#!/usr/bin/env python3
"""Build demo.mp4 from HTML slides + synthesized rock music (make_rock.py) + ffmpeg. Stdlib only.
Run: python3 demo_video/build_video.py   (needs ffmpeg, Google Chrome)
Numbers on the terminal slide come from reports/findings_*.json; the savings model uses the
ASSUMPTIONS below, which are examples to edit, not measurements."""
import collections, glob, html, json, os, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.join(HERE, "build")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
AUTHOR = "Krishna Peri"
GITHUB = "github.com/perikr/devsecops-agent"
STATIC_SCAN_SECONDS = 3  # measured: scan.py demo_target (Semgrep + Gitleaks + Trivy), warm cache

# Illustrative model: edit to match your team.
REPOS, MIN_MANUAL_PER_REPO, MIN_AGENT_REVIEW_PER_REPO, RUNS_PER_MONTH = 20, 45, 10, 4

f = json.load(open(sorted(glob.glob(os.path.join(ROOT, "reports", "findings_*.json")))[-1]))
C, total = f["counts"], len(f["findings"])
by_type = collections.Counter(x["type"] for x in f["findings"])
triaged = len(json.load(open(os.path.join(ROOT, "reports", "triage.json"))))
manual_h = REPOS * MIN_MANUAL_PER_REPO * RUNS_PER_MONTH / 60
agent_h = REPOS * MIN_AGENT_REVIEW_PER_REPO * RUNS_PER_MONTH / 60

CSS = """body{margin:0;width:1920px;height:1080px;background:#0f141b;color:#e8eaed;font:34px/1.45 -apple-system,Helvetica,sans-serif;
display:flex;flex-direction:column;justify-content:center;padding:0 140px;box-sizing:border-box}
h1{font-size:68px;margin:0 0 28px;color:#7fb0ff}ul{margin:0;padding-left:40px}li{margin:10px 0}
.sub{color:#99a1ad;font-size:28px;margin-top:30px}.foot{position:absolute;bottom:34px;left:140px;color:#99a1ad;font-size:24px}
pre{background:#000;border:1px solid #2f353e;border-radius:12px;padding:28px;font:28px/1.5 Menlo,monospace;color:#9be49b}
table{border-collapse:collapse;font-size:30px}td,th{border-bottom:1px solid #2f353e;padding:10px 26px;text-align:left}th{color:#99a1ad}
.big{font-size:84px;color:#7fb0ff;margin:0}.note{color:#ffb74d;font-size:25px;margin-top:22px}img{height:780px;border-radius:10px;border:1px solid #2f353e}"""

def slide(title, body, foot=f"{AUTHOR} | DevSecOps Agent"):
    return f"<!doctype html><meta charset=utf-8><style>{CSS}</style><h1>{title}</h1>{body}<div class=foot>{foot}</div>"

def ul(*items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

term = (f"$ python3 scan.py demo_target --dast-url http://demo-app:5055 --fail-on critical\n"
        f"[scan] SAST semgrep      {by_type['SAST']} findings\n[scan] Secrets gitleaks  {by_type['Secret']} findings\n"
        f"[scan] SCA/IaC trivy     {by_type['SCA'] + by_type['IaC']} findings\n[scan] DAST zap          {by_type['DAST']} findings\n"
        f"[scan] counts: critical {C['critical']}, high {C['high']}, medium {C['medium']}, low {C['low']}\n[gate] FAIL: {C['critical']} findings >= critical")

# (title, html body, spoken-style script; only its length is used to set how long each slide stays up, no voice is rendered)
SLIDES = [
 ("DevSecOps Agent", f"<p class=sub style='font-size:42px;color:#e8eaed'>Automated security checks with free tools and OpenClaw</p><p class=sub>Created by {AUTHOR}</p>",
  f"Hello, I am {AUTHOR}. This is the DevSecOps Agent: automated security checks built from free, open source tools and driven by an OpenClaw agent."),
 ("The problem for corporate teams", ul("Security scans are spread across separate tools and pipelines", "Raw results are noisy, and every finding needs a human to read it", "Paid scanners add licence cost for every team", "Reviews happen late, so fixes cost more"),
  "Corporate teams usually run several scanners in separate places. The results are noisy, someone has to triage every finding by hand, and paid licences add cost for each team."),
 ("What is inside", ul("<b>SAST</b>: Semgrep", "<b>Secrets</b>: Gitleaks", "<b>SCA, IaC, containers</b>: Trivy", "<b>DAST</b>: OWASP ZAP", "<b>Pipeline</b>: GitLab CI, free tier", "<b>Triage and reporting</b>: OpenClaw agent and an offline dashboard"),
  "The agent combines Semgrep for static analysis, Gitleaks for secrets, Trivy for dependencies, infrastructure code and containers, and OWASP ZAP for dynamic testing. A GitLab pipeline runs them, and an OpenClaw agent triages the results."),
 ("One command", f"<pre>{html.escape(term)}</pre><p class=sub>Real output from the bundled, intentionally vulnerable demo app. The gate fails the build, so it works as a CI check.</p>",
  f"One command runs every layer. On the demo app it found {total} issues: {C['critical']} critical, {C['high']} high, {C['medium']} medium and {C['low']} low. The gate then fails the build, so it can block risky changes."),
 ("The dashboard", "<img src='dashboard.png'>",
  "Results land in one offline dashboard with severity counts, a trend, filters and search, and the agent's verdict next to each finding."),
 ("What the OpenClaw agent does", ul("Reads the code behind the top findings", "Marks each one true positive, likely false positive, or needs review", "Suggests a concrete fix", "Opens GitLab issues for confirmed critical and high findings", "Runs on a schedule with openclaw cron"),
  f"The OpenClaw agent reads the code behind the most severe findings. In this run it triaged {triaged} findings, giving a verdict and a fix for each. It can open GitLab issues for confirmed problems and run on a schedule."),
 ("GitLab pipeline", ul("<code>.gitlab-ci.yml</code> uses only open source images", "Runs on every merge request or on a nightly schedule", "DAST runs when you set DAST_URL, on staging only", "<code>--fail-on high</code> blocks the merge"),
  "The included GitLab pipeline uses only open source tools. It can gate every merge request, or run nightly. Dynamic testing runs only when you point it at a staging address you own."),
 ("Advantages", ul("<b>Free</b>: no licence fees for any scanner", "<b>One workflow</b> for code, secrets, dependencies, infrastructure and running apps", "<b>Less reading</b>: the agent triages, people review the shortlist", "<b>Fast feedback</b>: the static scan of the demo took " + f"{STATIC_SCAN_SECONDS} seconds", "<b>Low LLM cost</b>: scanners are plain tools, the model only sees the top findings", "<b>Auditable</b>: every run saves a dated JSON report"),
  f"The advantages: no licence fees, one workflow for every layer, and fast feedback. The static scan of the demo took about {STATIC_SCAN_SECONDS} seconds. Because the scanners are ordinary tools, the language model only reads the top findings, which keeps token use low."),
 ("Time and resources saved", f"<table><tr><th>Measured on this demo</th><th></th></tr><tr><td>Static scan time</td><td>{STATIC_SCAN_SECONDS} s</td></tr><tr><td>Findings produced</td><td>{total}</td></tr><tr><td>Findings the LLM read</td><td>{triaged} ({round(100 * triaged / total)}%)</td></tr><tr><td>Scanner licence cost</td><td>0</td></tr></table>"
  f"<p class=sub style='margin-top:20px'>Example model: {REPOS} repos, scanned {RUNS_PER_MONTH} times a month, {MIN_MANUAL_PER_REPO} min manual vs {MIN_AGENT_REVIEW_PER_REPO} min with the agent: about {manual_h:.0f} h vs {agent_h:.0f} h, saving roughly {manual_h - agent_h:.0f} hours a month.</p>"
  "<p class=note>The model uses assumed minutes, not measurements. Replace them with your team's numbers in build_video.py.</p>",
  f"On the demo we measured a {STATIC_SCAN_SECONDS} second static scan, {total} findings, and the model reading only {triaged} of them, with zero scanner licence cost. As an example only: for {REPOS} repositories scanned four times a month, assuming forty five minutes of manual work per repository versus ten with the agent, the saving is about {manual_h - agent_h:.0f} hours a month. Those minutes are assumptions, so replace them with your own."),
 ("Get started", ul("<code>python3 scan.py demo_target</code>", "<code>./run_agent.sh</code> for agent triage", "Copy <code>.gitlab-ci.yml</code> into your repo", "Scan only systems you own or are authorised to test", f"GitHub: <b>{GITHUB}</b>"),
  f"To start, run scan dot py, then the agent script, and copy the GitLab file into your repository. Scan only systems you own or are authorised to test. Thank you for watching. This project was created by {AUTHOR}."),
]

def sh(*a, **k):
    return subprocess.run(a, check=True, capture_output=True, text=True, **k)

def main():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    def shot(src, out, size="1920,1080"):
        sh(CHROME, "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=1", "--screenshot=" + out, "--window-size=" + size, "file://" + src)
    dash = os.path.join(WORK, "dash.html")  # copy with the local path replaced so it is not shown in the video
    open(dash, "w").write(open(os.path.join(ROOT, "dashboard.html"), encoding="utf-8").read().replace(f["target"], "demo_target"))
    shot(dash, os.path.join(WORK, "dashboard.png"), "1280,720")
    clips, total = [], 0.0
    for i, (title, body, narr) in enumerate(SLIDES):
        foot = f"{AUTHOR} | DevSecOps Agent" + (f" | {GITHUB}" if i == len(SLIDES) - 1 else "")
        page, png, mp4 = (os.path.join(WORK, f"s{i}.{e}") for e in ("html", "png", "mp4"))
        open(page, "w").write(slide(title, body, foot))
        shot(page, png)
        dur = max(8.0, len(narr.split()) / 2.4 + 1.5)  # reading time
        total += dur
        sh("ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", png, "-t", f"{dur:.2f}",
           "-vf", f"fade=in:d=0.4,fade=out:st={dur - 0.4:.2f}:d=0.4,format=yuv420p", "-c:v", "libx264", "-an", mp4)
        clips.append(mp4)
        print("slide", i + 1, f"{dur:.1f}s")
    lst = os.path.join(WORK, "list.txt")
    open(lst, "w").write("".join(f"file '{c}'\n" for c in clips))
    silent = os.path.join(WORK, "silent.mp4")
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent)
    wav = os.path.join(WORK, "rock.wav")
    sh("python3", os.path.join(HERE, "make_rock.py"), wav)
    out = os.path.join(HERE, "demo.mp4")
    sh("ffmpeg", "-y", "-i", silent, "-stream_loop", "-1", "-i", wav, "-t", f"{total:.2f}", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
       "-af", f"volume=0.9,afade=t=in:d=1,afade=t=out:st={total - 3:.2f}:d=3", "-c:a", "aac", "-ar", "44100", "-ac", "2", out)
    print("built", out)

if __name__ == "__main__":
    main()
