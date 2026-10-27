"""Rebuild dashboard.html from reports/*.json (data embedded, works offline)."""
import datetime, glob, json, os
BASE = os.path.dirname(os.path.abspath(__file__))
runs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(BASE, "reports", "findings_*.json")))]
triage = {}
tp = os.path.join(BASE, "reports", "triage.json")
if os.path.exists(tp): triage = json.load(open(tp))
data = {"latest": runs[-1] if runs else None,
        "trend": [{"date": r["date"], **r["counts"]} for r in runs[-30:]],
        "triage": triage, "built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
tpl = open(os.path.join(BASE, "dashboard_template.html"), encoding="utf-8").read()
open(os.path.join(BASE, "dashboard.html"), "w", encoding="utf-8").write(
    tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
print("Dashboard rebuilt:", len(runs), "runs")
