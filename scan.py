#!/usr/bin/env python3
"""DevSecOps scan orchestrator. Free tools only: Semgrep (SAST), Gitleaks (secrets),
Trivy (SCA + IaC + container), OWASP ZAP (DAST, via Docker).
Usage: scan.py TARGET_DIR [--dast-url URL] [--fail-on high] [--image IMG]
Writes reports/findings_<date>.json and rebuilds dashboard.html. Only scan systems you own."""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys, tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
SEV = ["info", "low", "medium", "high", "critical"]
NORM = {"error": "high", "warning": "medium", "info": "low", "unknown": "low", "moderate": "medium",
        "informational": "info", "negligible": "low"}


def sev(s):
    s = str(s).lower()
    s = NORM.get(s, s)
    return s if s in SEV else "medium"


def run(cmd, ok=(0,)):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode not in ok:
        print(f"  ! {cmd[0]} exit {p.returncode}: {p.stderr.strip()[-300:]}", file=sys.stderr)
    return p


def finding(tool, kind, rule, sv, title, loc, line="", fix="", ref=""):
    fid = hashlib.sha1(f"{tool}|{rule}|{loc}|{line}".encode()).hexdigest()[:12]
    return {"id": fid, "tool": tool, "type": kind, "rule": rule, "severity": sev(sv), "title": title,
            "location": loc, "line": line, "fix": fix, "ref": ref}


def rel(target, path):
    return os.path.relpath(path, target) if os.path.isabs(path) else path


def semgrep(target, tmp):
    out = os.path.join(tmp, "semgrep.json")
    run(["semgrep", "scan", "--config", "p/default", "--config", "p/owasp-top-ten", "--metrics=off", "--json", "-o", out, "--quiet", target], ok=(0, 1))
    if not os.path.exists(out): return []
    return [finding("semgrep", "SAST", r["check_id"].split(".")[-1], r["extra"].get("severity", "medium"),
                    r["extra"]["message"].split("\n")[0][:200], rel(target, r["path"]), r["start"]["line"],
                    r["extra"].get("fix", ""), ",".join(r["extra"].get("metadata", {}).get("cwe", [])[:1]))
            for r in json.load(open(out)).get("results", [])]


def gitleaks(target, tmp):
    out = os.path.join(tmp, "gitleaks.json")
    run(["gitleaks", "dir", target, "--report-format", "json", "--report-path", out, "--no-banner", "--redact"], ok=(0, 1))
    if not os.path.exists(out): return []
    return [finding("gitleaks", "Secret", r["RuleID"], "high", r["Description"], rel(target, r["File"]),
                    r["StartLine"], "Rotate the credential and move it to a secret manager / CI variable")
            for r in json.load(open(out)) or []]


def trivy_fs(target, tmp):
    out = os.path.join(tmp, "trivy.json")
    run(["trivy", "fs", "--scanners", "vuln,misconfig", "--format", "json", "-o", out, "--quiet", target])
    if not os.path.exists(out): return []
    res = []
    for r in json.load(open(out)).get("Results", []):
        for v in r.get("Vulnerabilities") or []:
            res.append(finding("trivy", "SCA", v["VulnerabilityID"], v["Severity"],
                               f'{v["PkgName"]} {v["InstalledVersion"]}: {v.get("Title", "")}'[:200], r["Target"],
                               fix=("Upgrade to " + v["FixedVersion"]) if v.get("FixedVersion") else "",
                               ref=v.get("PrimaryURL", "")))
        for m in r.get("Misconfigurations") or []:
            res.append(finding("trivy", "IaC", m["ID"], m["Severity"], m["Title"], r["Target"],
                               (m.get("CauseMetadata") or {}).get("StartLine", ""), m.get("Resolution", ""),
                               m.get("PrimaryURL", "")))
    return res


def trivy_image(image, tmp):
    out = os.path.join(tmp, "trivy_img.json")
    run(["trivy", "image", "--format", "json", "-o", out, "--quiet", image])
    if not os.path.exists(out): return []
    return [finding("trivy", "Container", v["VulnerabilityID"], v["Severity"],
                    f'{v["PkgName"]} {v["InstalledVersion"]}: {v.get("Title", "")}'[:200], image,
                    fix=("Upgrade to " + v["FixedVersion"]) if v.get("FixedVersion") else "")
            for r in json.load(open(out)).get("Results", []) for v in r.get("Vulnerabilities") or []]


DOCKER_NET = None


def zap(url, tmp):
    if not shutil.which("docker"):
        print("  ! docker missing, skipping DAST", file=sys.stderr); return []
    os.chmod(tmp, 0o777)
    run(["docker", "run", "--rm", "-u", "root"] + (["--network", DOCKER_NET] if DOCKER_NET else []) + ["-v", f"{tmp}:/zap/wrk:rw", "ghcr.io/zaproxy/zaproxy:stable", "zap-baseline.py",
         "-t", url, "-J", "zap.json", "-I"], ok=(0, 1, 2))
    p = os.path.join(tmp, "zap.json")
    if not os.path.exists(p): return []
    risk = {"3": "high", "2": "medium", "1": "low", "0": "info"}
    return [finding("zap", "DAST", a["pluginid"], risk.get(a["riskcode"], "medium"), a["alert"], inst["uri"],
                    fix=a.get("solution", "").replace("<p>", "").replace("</p>", "")[:300],
                    ref="CWE-" + a.get("cweid", ""))
            for s in json.load(open(p)).get("site", []) for a in s.get("alerts", []) for inst in a.get("instances", [])[:3]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target"); ap.add_argument("--dast-url"); ap.add_argument("--image"); ap.add_argument("--docker-network", help="Docker network where ZAP can reach the target")
    ap.add_argument("--fail-on", default="high", choices=SEV)
    a = ap.parse_args()
    global DOCKER_NET
    DOCKER_NET = a.docker_network
    target = os.path.abspath(a.target)
    tmp = tempfile.mkdtemp()
    steps = [("SAST semgrep", semgrep, target), ("Secrets gitleaks", gitleaks, target), ("SCA/IaC trivy", trivy_fs, target)]
    if a.image: steps.append(("Container trivy", trivy_image, a.image))
    if a.dast_url: steps.append(("DAST zap", zap, a.dast_url))
    found = []
    for name, fn, arg in steps:
        print(f"[scan] {name} ...")
        r = fn(arg, tmp); print(f"       {len(r)} findings"); found += r
    uniq = {f["id"]: f for f in found}.values()
    found = sorted(uniq, key=lambda f: -SEV.index(f["severity"]))
    today = datetime.date.today().isoformat()
    counts = {s: sum(f["severity"] == s for f in found) for s in SEV}
    out = {"date": today, "target": target, "counts": counts, "findings": found}
    os.makedirs(os.path.join(BASE, "reports"), exist_ok=True)
    path = os.path.join(BASE, "reports", f"findings_{today}.json")
    json.dump(out, open(path, "w"), indent=1)
    subprocess.run([sys.executable, os.path.join(BASE, "build_dashboard.py")])
    print("[scan] counts:", counts, "->", path)
    gate = [f for f in found if SEV.index(f["severity"]) >= SEV.index(a.fail_on)]
    if gate:
        print(f"[gate] FAIL: {len(gate)} findings >= {a.fail_on}"); sys.exit(1)
    print("[gate] PASS")


if __name__ == "__main__":
    main()
