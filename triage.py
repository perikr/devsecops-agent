#!/usr/bin/env python3
"""First-pass triage: rank the latest findings, shortlist the top N, give each a verdict and a fix.
Plain rules, no LLM and no tokens. Writes reports/triage.json (merged) and prints the shortlist.
Usage: triage.py [N=10]"""
import glob, json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
SEV = ["info", "low", "medium", "high", "critical"]
PRIO = {"Secret": 0, "SAST": 1, "SCA": 2, "DAST": 3, "IaC": 4, "Container": 5}
HINTS = [("sql", "Use parameterized queries"), ("subprocess", "Avoid shell=True; pass an argument list and validate input"),
         ("shell", "Avoid shell=True; pass an argument list and validate input"), ("debug", "Disable debug mode outside development"),
         ("html", "Escape output or render with a template engine"), ("host", "Bind to 127.0.0.1 unless public access is needed"),
         ("root", "Run the container as a non-root user")]
NOISE = ("Non-Storable", "Storable and Cacheable", "Cross-Origin-Embedder", "Cross-Origin-Resource")


def judge(f):
    t, s = f["type"], SEV.index(f["severity"])
    if t == "Secret": return "true-positive", "Rotate the credential and load it from a secret manager"
    if t == "DAST":
        if any(n in f["title"] for n in NOISE): return "likely-false-positive", "Informational header or cache note, no direct risk"
        return ("true-positive" if s >= 2 else "needs-review"), (f["fix"] or "Add the missing security control")[:90]
    fix = f["fix"] or next((h for k, h in HINTS if k in f["rule"].lower() or k in f["title"].lower()), "Review and remediate")
    if t == "SAST" and "test" in f["location"].lower(): return "needs-review", fix[:90]
    return "true-positive", fix[:90]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    f = json.load(open(sorted(glob.glob(os.path.join(BASE, "reports", "findings_*.json")))[-1]))["findings"]
    f.sort(key=lambda x: (-SEV.index(x["severity"]), PRIO.get(x["type"], 9)))
    seen, top = set(), []
    for x in f:
        if (x["rule"], x["location"]) in seen: continue
        seen.add((x["rule"], x["location"])); top.append(x)
        if len(top) == n: break
    path = os.path.join(BASE, "reports", "triage.json")
    tri = json.load(open(path)) if os.path.exists(path) else {}
    print(f"Triaging top {len(top)} of {len(f)} findings")
    for x in top:
        v, note = judge(x)
        tri[x["id"]] = {"verdict": v, "note": note}
        print(f'{x["severity"]:<8}| {x["type"]:<6}| {x["rule"][:26]:<26}| {v}')
    json.dump(tri, open(path, "w"), indent=1)


if __name__ == "__main__":
    main()
