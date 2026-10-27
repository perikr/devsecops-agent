# DevSecOps Agent (free tools + OpenClaw)

| Layer | Tool (free/OSS) | Runs in |
|---|---|---|
| SAST | Semgrep | scan.py / GitLab CI |
| Secrets | Gitleaks | scan.py / GitLab CI |
| SCA, IaC, container | Trivy | scan.py / GitLab CI |
| DAST | OWASP ZAP baseline (Docker) | scan.py `--dast-url` / GitLab CI (`DAST_URL`) |
| Triage, issues, report | OpenClaw agent (`TASK.md`) | `./run_agent.sh` |
| Dashboard | `dashboard.html` (same pattern as AI-Repo-Radar) | offline |

## Use
```
python3 scan.py demo_target                       # SAST + secrets + SCA/IaC
python3 scan.py demo_target --image myapp:latest  # + container scan
python3 scan.py ./myrepo --dast-url http://localhost:5000   # + DAST (pulls ZAP image, ~1 GB)
python3 triage.py                                 # agent first-pass triage: top 10, verdict + fix
./run_agent.sh                                    # optional: OpenClaw LLM agent for deeper review
openclaw cron add --help                          # schedule run_agent.sh daily
```
`scan.py` exits 1 when a finding meets `--fail-on` (default high), so it works as a CI gate.
Copy `.gitlab-ci.yml` into a GitLab repo for the pipeline version. DAST only against systems you own.
`demo_target/` is intentionally vulnerable; never deploy it.

## Ideas to extend (from your catalog)
checkov (more IaC), nuclei (authorized DAST templates), OPA (policy gates), semgrep/mcp or secops-mcp (expose scans as MCP tools), ollama (free local LLM for triage), The-PR-Agent (MR review).

## Demo
Video walkthrough (about 3 min, including a live run of the real commands): [`demo_video/demo.mp4`](demo_video/demo.mp4). Rebuild with `python3 demo_video/build_video.py` (needs ffmpeg, Google Chrome).
Soundtrack: an original corporate-style loop synthesized by `demo_video/make_music.py` (no copyrighted music, no voice-over). Set `LINKEDIN` in `demo_video/build_video.py` to show your profile on the end card.
Created by Krishna Peri (github.com/perikr/devsecops-agent).

## Advantages and savings
- **No licence cost**: Semgrep, Gitleaks, Trivy and OWASP ZAP are open source; GitLab CI runs on the free tier.
- **One workflow** covers code (SAST), secrets, dependencies, IaC, containers and the running app (DAST).
- **Less manual reading**: the OpenClaw agent triages the top findings, people review the shortlist.
- **Low token cost**: scanning and the first-pass triage (`triage.py`) are plain code with zero tokens; an LLM agent (OpenClaw, optional, see `TASK.md`) is only needed for deeper review of what is left.
- **Auditable**: each run saves a dated JSON report.

Measured on the demo app: static scan (Semgrep + Gitleaks + Trivy) took 3 s on a warm cache; DAST adds the ZAP baseline run time.
Illustrative model, not a measurement: 20 repos x 4 scans/month, 45 min manual vs 10 min with the agent is about 60 h vs 13 h per month. Change the assumptions at the top of `demo_video/build_video.py` to match your team.
