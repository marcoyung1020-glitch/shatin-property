#!/usr/bin/env python3
"""從香港銀行公會 (HKAB) 取每日 HIBOR 定價，寫入 site/data/market.json 的 hibor_daily。"""
import json, os, subprocess, datetime as dt
from concurrent.futures import ThreadPoolExecutor
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site", "data", "market.json")
def get(d):
    u = f"https://www.hkab.org.hk/api/hibor?year={d.year}&month={d.month}&day={d.day}"
    r = subprocess.run(["curl", "-s", "-m", "20", "-A", "Mozilla/5.0", u], capture_output=True)
    try:
        j = json.loads(r.stdout)
        if j.get("isHoliday") or j.get("1 Month") is None: return None
        return [d.isoformat(), j.get("Overnight"), j.get("1 Month"), j.get("3 Months"), j.get("6 Months"), j.get("12 Months")]
    except Exception: return None
today = dt.date.today()
days = [today - dt.timedelta(days=i) for i in range(0, 400) if (today - dt.timedelta(days=i)).weekday() < 5]
with ThreadPoolExecutor(6) as ex:
    rows = [r for r in ex.map(get, days) if r]
rows.sort()
m = json.load(open(P, encoding="utf-8"))
m["hibor_daily"] = rows
m["hibor_source"] = "https://www.hkab.org.hk/tc/rates/hibor"
json.dump(m, open(P, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(rows), rows[0] if rows else None, rows[-1] if rows else None)
