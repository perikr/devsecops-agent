#!/usr/bin/env python3
"""Run the demo commands for real and record each output line with its timestamp to live_events.json.
Needs Docker (the demo app must be reachable as http://demo-app:5055 on network dast-net).
Usage: record_live.py PROJECT_DIR   (use a throwaway copy: it deletes reports/*.json first)"""
import glob, json, os, subprocess, sys, time

CMDS = ["ls -C",
        "python3 scan.py demo_target --dast-url http://demo-app:5055 --docker-network dast-net --fail-on critical",
        "python3 triage.py",
        "python3 build_dashboard.py"]


def main():
    cwd = os.path.abspath(sys.argv[1])
    for p in glob.glob(os.path.join(cwd, "reports", "*.json")): os.remove(p)
    events = []
    for cmd in CMDS:
        t0, lines = time.time(), []
        p = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             env={**os.environ, "PYTHONUNBUFFERED": "1"})
        for line in p.stdout:
            lines.append({"t": round(time.time() - t0, 2), "text": line.rstrip("\n").replace(cwd + "/", "").replace(cwd, ".")[:140]})
        p.wait()
        events.append({"cmd": cmd, "lines": lines, "end": round(time.time() - t0, 2), "exit": p.returncode})
        print(cmd[:50], "->", len(lines), "lines", events[-1]["end"], "s")
    json.dump(events, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_events.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
