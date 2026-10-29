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

# ---------- 已下架／已售出追蹤 ----------
TRF = os.path.join(os.path.dirname(SEENF), "tracked.json")
TR = json.load(open(TRF)) if os.path.exists(TRF) else {}
TXF = os.path.join(D, "transactions.json")
TX = json.load(open(TXF, encoding="utf-8")) if os.path.exists(TXF) else {}
key_ = lambda x: f'{x["s"]}:{x["u"]}'
cur = {key_(x) for x in L}
prev_n, cur_n = {}, {}
for k, v in TR.items():
    if v.get("gone") is None: prev_n[v["x"]["s"]] = prev_n.get(v["x"]["s"], 0) + 1
for x in L: cur_n[x["s"]] = cur_n.get(x["s"], 0) + 1
# 某來源今次數量跌超過 15%，多數係讀取唔齊，唔當作下架
healthy = {s_: cur_n.get(s_, 0) >= 0.85 * n for s_, n in prev_n.items()}
for x in L:
    k = key_(x); v = TR.get(k)
    TR[k] = dict(x=x, seen=NOW, gone=None, sold=None, since=(v or {}).get("since") or NOW)
# 個別屋苑讀唔齊（例如利嘉閣某幾版讀唔到）都唔當作下架
got = {}
for x in L: got[(x["s"], x["e"])] = got.get((x["s"], x["e"]), 0) + 1
rep = {(s_, e["id"]): n for e in E for s_, n in (e.get("counts") or {}).items() if n}
complete = lambda s_, e_: got.get((s_, e_), 0) >= 0.95 * rep.get((s_, e_), 0)
for k, v in TR.items():
    if k not in cur and v.get("gone") is None and healthy.get(v["x"]["s"], False) and complete(v["x"]["s"], v["x"]["e"]):
        v["gone"] = NOW
# 保留下架後 60 日
cut = (dt.datetime.now(HK) - dt.timedelta(days=60)).strftime("%Y-%m-%dT%H:%M")
TR = {k: v for k, v in TR.items() if v.get("gone") is None or v["gone"] >= cut}

CN = dict(zip("零一二三四五六七八九", range(10)))
def floor_no(t):
    t = (t or "").replace("樓", "").strip()
    if t.isdigit(): return int(t)
    if t and all(c in "零一二三四五六七八九十" for c in t):
        if "十" in t:
            a, _, b = t.partition("十")
            return (CN.get(a, 1) if a else 1) * 10 + (CN.get(b, 0) if b else 0)
        return CN.get(t)
    return None
def zone_of(t, top):
    if re.search("高", t or ""): return 2
    if re.search("中", t or ""): return 1
    if re.search("低|地", t or ""): return 0
    n = floor_no(t)
    if n is None or not top: return None
    return 0 if n <= top / 3 else (1 if n <= top * 2 / 3 else 2)
def bkeys(b):
    b = b or ""
    names = set(re.findall(r"([\u4e00-\u9fff]{2}(?:苑|閣|大廈))", b))
    codes = set(re.findall(r"([A-Z]?\d*[A-Z]?)\s*座", b)) - {""}
    return names, codes
def same_bldg(a, b):
    (na, ca), (nb, cb) = bkeys(a), bkeys(b)
    if na and nb: return bool(na & nb)
    return bool(ca and cb and ca & cb)
TOP = {}
def bid(b):
    na, ca = bkeys(b)
    return min(na) if na else (min(ca) if ca else "")
for eid, ts in TX.items():
    for t in ts:
        n = floor_no(t["floor"])
        if n:
            TOP[eid] = max(TOP.get(eid, 0), n)
            kb = (eid, bid(t["bldg"])); TOP[kb] = max(TOP.get(kb, 0), n)
def cands(v):
    x = v["x"]
    if not x.get("a") or not x.get("b"): return None
    lz = zone_of(x["fl"], None)
    start = min(x.get("pd") or v["since"], v["since"])[:10]
    if x.get("pq") == "base":  # 開始追蹤前已放盤：實際刊登日不詳，放寬 30 日
        start = (dt.date.fromisoformat(start) - dt.timedelta(days=30)).isoformat()
    end = (dt.datetime.fromisoformat(v["gone"]) + dt.timedelta(days=21)).strftime("%Y-%m-%d")
    for t in TX.get(x["e"], []):
        if not t.get("area") or abs(t["area"] - x["a"]) > 2: continue
        if not same_bldg(x["b"], t["bldg"]): continue
        if not (start <= (t["date"] or "") <= end): continue
        tz = zone_of(t["floor"], TOP.get((x["e"], bid(t["bldg"]))) or TOP.get(x["e"]))
        if lz is not None and tz is not None and lz != tz: continue
        p = t["price"] / 1e4
        if not (0.85 * x["p"] <= p <= 1.02 * x["p"]): continue
        yield abs(x["p"] - p) / x["p"] + (0 if lz is not None and tz is not None else 0.03), t
def sale_of(t):
    return dict(p=round(t["price"] / 1e4, 1), d=t["date"], fl=t["floor"], flat=t["flat"], u=t.get("url"), reg=t.get("reg"))
# 每宗成交（同一來源）只配對一個最似嘅盤
C = sorted(((sc, k, t) for k, v in TR.items() if v.get("gone") for sc, t in cands(v)), key=lambda z: z[0])
used, SOLD = set(), {}
for sc, k, t in C:
    if k in SOLD or (TR[k]["x"]["s"], t["id"]) in used: continue
    SOLD[k] = sale_of(t); used.add((TR[k]["x"]["s"], t["id"]))
GONE = []
for k, v in TR.items():
    if v.get("gone") is None: continue
    v["sold"] = SOLD.get(k)
    y = dict(v["x"]); y["gd"] = v["gone"]
    if v["sold"]:
        y["st"] = "sold"; y["sp"] = v["sold"]["p"]; y["sd"] = v["sold"]["d"]; y["sfl"] = (v["sold"]["fl"] or "") + (v["sold"]["flat"] or ""); y["su"] = v["sold"]["u"]
    else:
        y["st"] = "gone"
    GONE.append(y)
json.dump(TR, open(TRF, "w"), ensure_ascii=False)
print("已下架", sum(1 for y in GONE if y["st"] == "gone"), "已售出", sum(1 for y in GONE if y["st"] == "sold"))

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
out = dict(status=STATUS, generated=m.get("generated"), listings_generated=m.get("generated"), market=m, estates=ES, listings=L + GONE)
json.dump(out, open(os.path.join(D, "app.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(L), os.path.getsize(os.path.join(D, "app.json")))
for e in ES: print(e["name"], e["med_psf"], e["rent_psf"], e["yield_"], e["u500"], e["op_year"], e["counts"])
