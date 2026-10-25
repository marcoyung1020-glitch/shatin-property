#!/usr/bin/env python3
"""把 site/data/ 原始 JSON 整合成網站使用的 site/data/app.json。"""
import json, os, re, statistics as st
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site", "data")
J = lambda n: json.load(open(os.path.join(D, n), encoding="utf-8"))
m, E, LA = J("market.json"), J("estates.json"), J("listings_agency.json")

# CCL：用官方完整日期序列由尾對齊分區數值
cd = (m.get("ccl_latest", {}).get("ccl", {}) or {}).pop("chartData", None)
w = m.get("ccl_weekly", [])
if cd and w:
    dates = cd["date"][-len(w):]
    w = [[d] + r[1:] for d, r in zip(dates, w)]
m["ccl_weekly"] = w

name2id = {e["name"]: e["id"] for e in E}
import datetime as dt
HK = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(HK).strftime("%Y-%m-%dT%H:%M")
SEENF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "first_seen.json")
os.makedirs(os.path.dirname(SEENF), exist_ok=True)
SEEN = json.load(open(SEENF)) if os.path.exists(SEENF) else {}
BASE = SEEN.setdefault("_base", NOW)  # 開始追蹤時間：當日已存在嘅盤無法知道實際刊登日
def hk(ts):
    """各來源日期轉成香港時間 YYYY-MM-DDTHH:MM（只有日期就保留日期）"""
    if not ts: return None
    if len(ts) == 10: return ts
    try:
        d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if d.tzinfo is None: d = d.replace(tzinfo=HK)
        return d.astimezone(HK).strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return None
def stamp(key, pub, q):
    seen = SEEN.setdefault(key, NOW)
    pub = hk(pub)
    if pub and pub[:16] <= seen:
        return pub, q
    return seen, ("base" if seen == BASE else "seen")
L = []
for x in LA:
    if not x.get("price"): continue
    L.append(dict(s=x["src"], e=x["estate"], p=round(x["price"] / 1e4, 1), a=x.get("area"), f=x.get("psf"),
                  r=x.get("rooms"), b=x.get("bldg") or "", fl=x.get("floor") or "", d=x.get("updated") or "",
                  t=x.get("tags") or [], u=x.get("url") or "", ls=x.get("lease")))
    L[-1]["pd"], L[-1]["pq"] = stamp(f'{x["src"]}:{x.get("ref") or x.get("url")}', x.get("pub"), "exact")
# 剔除車位、舖位及資料不全
def ok(x):
    txt = " ".join([x["b"]] + list(x["t"]))
    if re.search(r"車位|車場|泊車|商舖|舖位", txt): return False
    if x["p"] < 150: return False
    if x["a"] is not None and x["a"] < 150: return False
    return True
before = len(L); L = [x for x in L if ok(x)]; print("removed", before - len(L))
# 估算 psf
for x in L:
    if not x["f"] and x["a"]: x["f"] = round(x["p"] * 1e4 / x["a"])

ES = []
for e in E:
    mine = [x for x in L if x["e"] == e["id"] and x["s"] in ("midland", "centanet", "ricacorp")]
    psf = [x["f"] for x in mine if x["f"]]
    price = [x["p"] for x in mine]
    rpsf = [r["rent"] / r["area"] for r in e["rents"] if r.get("area")]
    med_psf = st.median(psf) if psf else None
    med_rpsf = st.median(rpsf) if rpsf else None
    meta = e["meta"]
    op = meta.get("op_date") or ""
    yrs = sorted(set(re.findall(r"(\d{4})年", op)))
    ES.append(dict(id=e["id"], name=e["name"], area=e["area"],
        counts=e["counts"],
        med_psf=round(med_psf) if med_psf else None, min_price=min(price) if price else None,
        med_price=round(st.median(price), 1) if price else None,
        u500=sum(1 for x in mine if x["p"] <= 500),
        rent_psf=round(med_rpsf, 1) if med_rpsf else None, rent_n=len(rpsf),
        yield_=round(med_rpsf * 12 / med_psf * 100, 2) if med_psf and med_rpsf else None,
        op_year=(yrs[0] + ("–" + yrs[-1] if len(yrs) > 1 else "")) if yrs else "",
        flats=meta.get("total_flats"), blocks=meta.get("no_of_blocks"), address=meta.get("address"), developer=meta.get("developer"),
        mtr=([a for a in (meta.get("amenities") or []) if a.get("type") == "mtr"][:2] or [{"name": m_["name"]} for m_ in (meta.get("mtr") or [])][:2]),
        mall=[a for a in (meta.get("amenities") or []) if a.get("type") == "mall"][:1],
        school=((meta.get("school_net") or {}).get("primary") or {}).get("id") if isinstance(meta.get("school_net"), dict) else None,
        mid_avg=meta.get("avg_net_ft_price"), stat=meta.get("market_stat"), sold=(meta.get("recent_sold") or [])[:5],
        lat=meta.get("latitude"), lng=meta.get("longitude"),
        links=e["links"]))
json.dump(SEEN, open(SEENF, "w"), ensure_ascii=False)
STATUS = J("status.json") if os.path.exists(os.path.join(D, "status.json")) else {}
out = dict(status=STATUS, generated=m.get("generated"), listings_generated=m.get("generated"), market=m, estates=ES, listings=L)
json.dump(out, open(os.path.join(D, "app.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(L), os.path.getsize(os.path.join(D, "app.json")))
for e in ES: print(e["name"], e["med_psf"], e["rent_psf"], e["yield_"], e["u500"], e["op_year"], e["counts"])
