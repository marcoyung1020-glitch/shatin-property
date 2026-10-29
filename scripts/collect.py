#!/usr/bin/env python3
"""沙田睇樓平台 — 數據收集程式
收集：中原 CCL、差估署指數、土地註冊處登記、HKMA HIBOR、
     美聯 / 中原 / 利嘉閣 放盤（API），輸出 site/data/*.json
28Hse / House730 由 parse_portals.py 另行處理。
"""
import json, re, subprocess, time, datetime as dt, csv, io, os, sys, urllib.parse as up
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site", "data")
os.makedirs(OUT, exist_ok=True)
CACHE = os.path.join(ROOT, "data")
os.makedirs(CACHE, exist_ok=True)
PUBF = os.path.join(CACHE, "midland_first_pub.json")
PUBCACHE = json.load(open(PUBF)) if os.path.exists(PUBF) else {}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

ESTATES = [
  # id, 名稱, 片區, 美聯 ID, 中原 code, 利嘉閣 alias, 28Hse c-id, House730 id
  dict(id="wai-king", name="蔚景園", area="沙田市中心", mid="E00490", cen="2-XSSZZHNRHT", ric="蔚景園-estate-沙田-hma-hk", h28=None, h730=25940),
  dict(id="shatin-centre", name="沙田中心", area="沙田市中心", mid="E00316", cen="2-XSDTIHLYHT", ric="沙田中心-estate-沙田-hma-hk", h28=4086, h730=26026),
  dict(id="riverside", name="河畔花園", area="沙田市中心", mid="E00422", cen="2-GYYYPPGOPS", ric="河畔花園-estate-沙田-hma-hk", h28=None, h730=25964),
  dict(id="lucky-plaza", name="好運中心", area="沙田市中心", mid="E00276", cen="2-XSHHIHLXHT", ric="好運中心-estate-沙田-hma-hk", h28=None, h730=26025),
  dict(id="wai-wah", name="偉華中心", area="沙田市中心", mid="E00489", cen="2-XSSZZHNSHT", ric="偉華中心-estate-沙田-hma-hk", h28=None, h730=25942),
  dict(id="garden-city", name="花園城", area="沙田市中心", mid="E00320", cen="3-XSIXZHNEHT", ric="花園城-bigest-沙田-hma-hk", h28=4118, h730=25949),
  dict(id="hilton", name="希爾頓中心", area="沙田市中心", mid="E00467", cen="2-XSSZZHNVHT", ric="希爾頓中心-estate-沙田-hma-hk", h28=None, h730=25941),
  dict(id="belair", name="富豪花園", area="沙田市中心", mid="E00001", cen="2-GYEWPPGXPS", ric="富豪花園-estate-沙田-hma-hk", h28=None, h730=25965),
  dict(id="shatin-plaza", name="沙田廣場", area="沙田市中心", mid="E00491", cen="2-XSSZZHNOHT", ric="沙田廣場-estate-沙田-hma-hk", h28=4099, h730=25943),
  dict(id="tsui-lai", name="翠麗花園", area="沙田市中心", mid="E00424", cen="2-GYEAWPWXPS", ric="翠麗花園-estate-沙田-hma-hk", h28=4125, h730=26029),
  dict(id="tin-yuen", name="田園閣", area="沙田市中心", mid="E00608", cen="2-XSDNZHNYHT", ric="田園閣-estate-沙田-hma-hk", h28=4115, h730=25947),
  dict(id="city-one", name="沙田第一城", area="第一城 / 石門", mid="E00012", cen="3-XSHNIHSXHT", ric="沙田第一城-bigest-沙田第一城-hma-hk", h28=4080, h730=None),
  dict(id="pictorial", name="碧濤花園", area="第一城 / 石門", mid="E00302", cen="3-XSLSTHZEHT", ric="碧濤花園-bigest-石門-hma-hk", h28=None, h730=25934),
  dict(id="garden-vista", name="翠湖花園", area="第一城 / 石門", mid="E00492", cen="3-XSISTHZYHT", ric="翠湖花園-bigest-石門-hma-hk", h28=None, h730=25931),
  dict(id="bayshore", name="濱景花園", area="第一城 / 石門", mid="E00014", cen="2-XSXSTHZJHT", ric="濱景花園-estate-石門-hma-hk", h28=None, h730=25930),
]


def curl(url, headers=None, data=None, method=None, timeout=40, retries=3):
  cmd = ["curl", "-s", "-L", "-m", str(timeout), "-A", UA]
  for k, v in (headers or {}).items():
    cmd += ["-H", f"{k}: {v}"]
  if data is not None:
    cmd += ["-X", method or "POST", "-H", "Content-Type: application/json", "-d", json.dumps(data)]
  cmd.append(url)
  for i in range(retries):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode == 0 and r.stdout:
      return r.stdout.decode("utf-8", "ignore")
    time.sleep(2 + i * 3)
  return ""


def jget(url, **kw):
  t = curl(url, **kw)
  try:
    return json.loads(t)
  except Exception:
    return None


def load_old(name):
  try:
    return json.load(open(os.path.join(OUT, name), encoding="utf-8"))
  except Exception:
    return None


def save(name, obj):
  with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
    json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
  print("saved", name)


# ---------------- 市場指標 ----------------
def market():
  m = {"generated": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="minutes")}
  # CCL
  ccl = jget("https://hk.centanet.com/CCI/api/Index/CCL")
  chart = jget("https://hk.centanet.com/CCI/api/Index/CCLChart")
  if ccl:
    m["ccl_latest"] = {k: ccl[k] for k in ("ccl", "hk", "kln", "nte", "ntw", "big", "normal", "estate") if k in ccl}
    m["ccl_latest"]["dateRange"] = ccl.get("dateRange")
  if chart:
    rd = chart["rawData"]
    rows = []
    for i, t in enumerate(rd["times"]):
      if rd["ccl"][i] is None:
        continue
      if t < "2019-01-01":
        continue
      rows.append([t, rd["ccl"][i], rd["cclNTE"][i], rd["cclKLN"][i], rd["cclHK"][i], rd["cclNTW"][i]])
    m["ccl_weekly"] = rows
  # RVD
  def rvd(code):
    t = curl(f"https://www.rvd.gov.hk/datagovhk/{code}.csv")
    rd = list(csv.reader(io.StringIO(t.lstrip("\ufeff"))))
    hdr = rd[1]
    out = []
    for r in rd[2:]:
      if not r or not re.match(r"\d\d-\d{4}", r[0]):
        continue
      mm, yy = r[0].split("-")
      if int(yy) < 2015:
        continue
      out.append(dict(zip(hdr, r)) | {"ym": f"{yy}-{mm}"})
    return out
  pi = rvd("1.4M"); ri = rvd("1.3M"); ap = rvd("1.2M"); ar = rvd("1.1M")
  def num(x):
    try: return float(x)
    except: return None
  m["rvd_index"] = [[p["ym"], num(p["All Classes"]), num(r.get("All Classes")), num(p["Class A"]), num(r.get("Class A")), num(p["Class B"]), num(r.get("Class B")), p.get("All Classes - Remarks", "")]
                    for p, r in zip(pi, ri)]
  m["rvd_nt_avg"] = [[p["ym"], num(p["Class A New Territories"]), num(r["Class A New Territories"]), num(p["Class B New Territories"]), num(r["Class B New Territories"])] for p, r in zip(ap, ar)]
  # 土地註冊處
  lr = []
  for part in ("agt-6", "agt"):
    t1 = jget(f"https://www.landreg.gov.hk/json/monthly_agt/{part}/t1.json") or []
    t2 = jget(f"https://www.landreg.gov.hk/json/monthly_agt/{part}/t2.json") or []
    v = {x["Date"]: x for x in t2}
    for x in t1:
      d = x["Date"][:7]
      lr.append([d, x["Number of ASP for Residential Building Units"], x["Number of ASP for All Building Units"],
                 v.get(x["Date"], {}).get("Consideration of ASP for Residential Building Units")])
  seen = {}
  for r in lr:
    seen[r[0]] = r
  m["landreg"] = [seen[k] for k in sorted(seen) if k >= "2021-01"]
  # HIBOR
  base = "https://api.hkma.gov.hk/public/market-data-and-statistics"
  d = jget(f"{base}/daily-monetary-statistics/daily-figures-interbank-liquidity?pagesize=120&sortby=end_of_date&sortorder=desc")
  if d:
    m["hibor_daily"] = [[r["end_of_date"], r.get("hibor_overnight"), r.get("hibor_fixing_1m")] for r in reversed(d["result"]["records"])]
  d = jget(f"{base}/monthly-statistical-bulletin/er-ir/hk-interbank-ir-endperiod?segment=hibor.fixing&pagesize=96&sortby=end_of_month&sortorder=desc")
  if d:
    m["hibor_monthly"] = [[r["end_of_month"], r.get("ir_1m"), r.get("ir_3m"), r.get("ir_12m")] for r in reversed(d["result"]["records"])]
  old = load_old("market.json") or {}
  for k, v in old.items():
    if not m.get(k) and v:
      print("  沿用舊資料:", k); m[k] = v
  save("market.json", m)


# ---------------- 美聯 ----------------
def midland_token():
  h = curl("https://www.midland.com.hk/zh-hk/list/buy/%E6%B2%B3%E7%95%94%E8%8A%B1%E5%9C%92-E-E00422")
  mm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
  return json.loads(mm.group(1))["runtimeConfig"]["BUILD_TOKEN"]


def midland(est, tok):
  H = {"Authorization": f"Bearer {tok}", "Origin": "https://www.midland.com.hk", "Referer": "https://www.midland.com.hk/"}
  out, rents = [], []
  for tx, bucket in (("S", out), ("R", rents)):
    page = 1
    while True:
      d = jget(f"https://data.midland.com.hk/search/v2/properties?est_ids={est['mid']}&tx_type={tx}&page={page}&limit=100&lang=zh-hk", headers=H)
      if not d or not d.get("result"):
        break
      bucket += d["result"]
      if len(bucket) >= d.get("count", 0) or page > 10:
        break
      page += 1
  L = []
  for r in out:
    L.append(dict(src="midland", ref=r.get("serial_no"), price=r.get("price"), area=r.get("net_area") or None,
                  psf=r.get("price_over_net_area") or None, rooms=r.get("bedroom"),
                  bldg=(r.get("building") or {}).get("name"), floor=(r.get("floor_level") or {}).get("name"),
                  facing=(r.get("orientation") or {}).get("name"), updated=(r.get("update_date") or "")[:10],
                  tags=[x["name"] for x in (r.get("misc") or {}).get("sell", [])][:4], url=r.get("url_desc"),
                  lease=bool(r.get("tenancy"))))
  # 首次刊登日期：列表 API 冇提供，要讀放盤頁（有快取，只會讀新盤）
  need = [x for x in L if x["ref"] and x["ref"] not in PUBCACHE and x.get("url")]
  def getpub(x):
    h = curl(x["url"], retries=2, timeout=30)
    mm = re.search(r'"serial_no":"%s".{0,4000}?"first_pub_date":"([^"]+)"' % x["ref"], h, re.S) or re.search(r'"first_pub_date":"([^"]+)"', h)
    return x["ref"], (mm.group(1) if mm else None)
  with ThreadPoolExecutor(8) as ex:
    for ref, d in ex.map(getpub, need):
      if d: PUBCACHE[ref] = d
  for x in L:
    x["pub"] = PUBCACHE.get(x["ref"])
  R = [dict(rent=r.get("rent"), area=r.get("net_area")) for r in rents if r.get("rent")]
  # 屋苑資料
  name = up.quote(est["name"])
  h = curl(f"https://www.midland.com.hk/zh-hk/list/buy/{name}-E-{est['mid']}")
  meta = {}
  mm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
  if mm:
    g = json.loads(mm.group(1))["props"]["pageProps"].get("geoData") or {}
    meta = {k: g.get(k) for k in ("avg_net_ft_price", "min_net_ft_price", "max_net_ft_price", "no_of_blocks", "total_flats", "no_of_storeys", "address", "op_date", "developer", "facilities", "merits", "management_co", "latitude", "longitude", "sell_count", "rent_count")}
    meta["school_net"] = (g.get("school_net") or [{}])[0].get("name") if isinstance(g.get("school_net"), list) else g.get("school_net")
    meta["mtr"] = g.get("mtr")
    meta["amenities"] = g.get("amenities")
    tx = (g.get("geo_transaction") or {})
    meta["recent_sold"] = [dict(price=x.get("price"), area=x.get("net_area"), rooms=x.get("bedroom"), bldg=x.get("building_name"), floor=x.get("floor"), gain=x.get("gain"), held=x.get("holding_period")) for x in tx.get("secondhand_sell", [])]
    meta["recent_rent"] = [dict(rent=x.get("price"), area=x.get("net_area"), rooms=x.get("bedroom"), bldg=x.get("building_name")) for x in tx.get("secondhand_rent", [])]
    meta["market_stat"] = g.get("market_stat")
    meta["market_stat_by_room"] = g.get("market_stat_by_room")
  return L, R, meta, len(out)


# ---------------- 中原 ----------------
def centanet(est):
  if not est.get("cen"):
    return [], [], 0
  out = []; off = 0; total = 0
  while True:
    d = jget("https://hk.centanet.com/findproperty/api/Post/Search", headers={"Platform": "Web", "Lang": "tc"},
             data={"postType": "Sale", "offset": off, "size": 100, "bigestAndEstate": [est["cen"]]})
    if not d:
      break
    total = d.get("count", 0)
    out += d.get("data", [])
    off += 100
    if off >= total or off > 600:
      break
  rents = []
  d = jget("https://hk.centanet.com/findproperty/api/Post/Search", headers={"Platform": "Web", "Lang": "tc"},
           data={"postType": "Rent", "offset": 0, "size": 100, "bigestAndEstate": [est["cen"]]})
  if d:
    rents = [dict(rent=(x.get("priceInfo") or {}).get("rent"), area=(x.get("areaInfo") or {}).get("nSize")) for x in d.get("data", []) if (x.get("priceInfo") or {}).get("rent")]
  L = []
  for x in out:
    dt_ = (x.get("displayText") or {}).get("addr", {})
    L.append(dict(src="centanet", ref=x.get("refNo"), price=(x.get("priceInfo") or {}).get("price"),
                  area=(x.get("areaInfo") or {}).get("nSize") or None, psf=(x.get("unitPriceInfo") or {}).get("nUnitPrice") or None,
                  rooms=x.get("bedroomCount"), bldg=((x.get("estateName")+" ") if x.get("bigEstateName") else "")+(x.get("buildingName") or ""), floor=x.get("yAxis"), facing=x.get("direction"),
                  updated=(x.get("updateDate") or "")[:10], tags=[v.get("name") for k, v in (x.get("displayLabel") or {}).items() if isinstance(v, dict) and v.get("show") and v.get("name")][:4],
                  url=x.get("detailUrl"), lease=bool(x.get("withLease")), pub=(x.get("publishDate") or None) and x["publishDate"] + "+08:00"))
  return L, rents, total


def centanet_tx(est):
  """中原成交紀錄（近 90 日，包括土地註冊處及中原自己成交）"""
  if not est.get("cen"):
    return []
  out = []; off = 0
  while True:
    d = jget("https://hk.centanet.com/findproperty/api/Transaction/Search", headers={"Platform": "Web", "Lang": "tc"},
             data={"offset": off, "size": 100, "bigestAndEstate": [est["cen"]], "day": "Day90"})
    if not d or "data" not in d:
      raise RuntimeError("中原成交讀取失敗")
    out += d["data"]; off += 100
    if off >= d.get("count", 0) or off >= 600:
      break
  T = []
  for x in out:
    if x.get("firstOrSecondHand") not in (None, "SecondHand") or not x.get("transactionPrice"):
      continue
    T.append(dict(id=x.get("id"), price=x["transactionPrice"], area=x.get("nArea") or None, rooms=x.get("bedroomCount"),
                  est=x.get("estateName"), bldg=x.get("buildingName") or "", floor=x.get("yAxis") or "", flat=x.get("xAxis") or "",
                  date=(x.get("insDate") or "")[:10], reg=(x.get("regDate") or "")[:10] or None, src=x.get("dataSource"),
                  url=x.get("detailUrl")))
  return T


# ---------------- 利嘉閣 ----------------
def ric_state(alias, tx="buy"):
  h = curl(f"https://www.ricacorp.com/zh-hk/property/list/{tx}/{up.quote(alias)}")
  mm = re.search(r'<script id="serverApp-state" type="application/json">(.*?)</script>', h, re.S)
  if not mm:
    return None
  s = mm.group(1).replace("&q;", '"').replace("&a;", "&").replace("&s;", "'").replace("&l;", "<").replace("&g;", ">")
  return json.loads(s)


def ricacorp(est):
  st = None
  for i in range(4):
    st = ric_state(est["ric"])
    if st and st.get("SEARCHFILTER"):
      break
    time.sleep(4)
  if not st or not st.get("SEARCHFILTER"):
    print("  ricacorp: no state", est["name"])
    return [], 0
  loc = st["SEARCHFILTER"].get("locationId")
  posts = list(st.get("POSTS") or [])
  total = st.get("POSTSTOTAL") or len(posts)
  pages = st.get("POSTSNUMPAGES") or 1
  for p in range(2, min(pages, 20) + 1):
    for k in range(4):  # 個別版面間中讀唔到，重試幾次
      d = jget(f"https://www.ricacorp.com/zh-hk/property/api/post?locationId={loc}&offset={(p-1)*10}&page={p}&txType=1",
               headers={"x-custom-header": "www.ricacorp.com/zh-hk/property"})
      if d and d.get("results"):
        posts += d["results"]; break
      time.sleep(2 + 3 * k)
    time.sleep(0.6)
  L = []
  seen = set()
  for x in posts:
    if x.get("postNo") in seen:
      continue
    seen.add(x.get("postNo"))
    L.append(dict(src="ricacorp", ref=x.get("postNo"), price=x.get("marketPrice"), area=x.get("saleableArea") or None,
                  psf=round(x["unitPrice"]) if x.get("unitPrice") else None, rooms=x.get("room"),
                  bldg=(x.get("displayText") or "").replace(est["name"], "").strip(), floor=x.get("floorZoneText"), facing=x.get("directionText"),
                  updated=dt.datetime.fromtimestamp(x["overallDateModified"] / 1000).strftime("%Y-%m-%d") if x.get("overallDateModified") else "",
                  tags=(x.get("policyTags") or [])[:4], url="https://www.ricacorp.com/zh-hk/property/detail/" + (x.get("aliasV4") or x.get("alias") or ""), lease=False))
  return L, total


def midland_all():
  """只讀美聯（喺香港電腦嘅 self-hosted runner 執行），結果存入 site/data/midland.json"""
  tok = midland_token()
  now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M")
  out = {"generated": now, "estates": {}}
  for e in ESTATES:
    L, R, meta, N = midland(e, tok)
    for x in L:
      x["estate"] = e["id"]
    print(e["name"], len(L))
    out["estates"][e["id"]] = dict(L=L, R=R, meta=meta, N=N)
  if sum(len(v["L"]) for v in out["estates"].values()) < 100:
    raise SystemExit("美聯放盤太少，唔覆蓋舊資料")
  json.dump(PUBCACHE, open(PUBF, "w"))
  save("midland.json", out)


def listings():
  """每個來源獨立處理：讀唔到（例如美聯擋海外 IP）就沿用上次資料，並記錄喺 status.json"""
  oldL = load_old("listings_agency.json") or []
  oldE = {e["id"]: e for e in (load_old("estates.json") or [])}
  status = load_old("status.json") or {}
  now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M")
  ok = {"midland": True, "centanet": True, "ricacorp": True}
  MF = load_old("midland.json") if os.environ.get("MIDLAND_FROM_FILE") else None
  if os.environ.get("MIDLAND_FROM_FILE"):
    tok = None  # GitHub 伺服器被美聯擋，改用 self-hosted runner 存低嘅 midland.json
    gen = (MF or {}).get("generated")
    fresh = bool(gen) and (dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).replace(tzinfo=None) - dt.datetime.fromisoformat(gen)).total_seconds() < 5 * 3600
    ok["midland"] = fresh
    if gen:
      status.setdefault("midland", {})["last_ok"] = gen
  else:
    try:
      tok = midland_token()
    except Exception as ex:
      print("  美聯 token 失敗:", str(ex)[:80]); tok = None; ok["midland"] = False
  estates_out = []
  allL = []
  for e in ESTATES:
    print("==", e["name"])
    prev = oldE.get(e["id"], {})
    keep = lambda src: [x for x in oldL if x["src"] == src and x.get("estate") == e["id"]]
    pc = prev.get("counts", {})
    mL = mR = None; meta = prev.get("meta", {}); mN = pc.get("midland")
    if MF and e["id"] in MF.get("estates", {}):
      d_ = MF["estates"][e["id"]]
      mL, mR, meta, mN = d_["L"], d_["R"], d_["meta"], d_["N"]
    elif tok:
      try:
        mL, mR, meta, mN = midland(e, tok)
      except Exception as ex:
        print("  美聯失敗:", str(ex)[:80]); ok["midland"] = False
    try:
      cL, cR, cN = centanet(e)
    except Exception as ex:
      print("  中原失敗:", str(ex)[:80]); ok["centanet"] = False; cL, cR, cN = None, None, pc.get("centanet")
    try:
      rL, rN = ricacorp(e)
    except Exception as ex:
      print("  利嘉閣失敗:", str(ex)[:80]); ok["ricacorp"] = False; rL, rN = None, pc.get("ricacorp")
    for x in (mL or []) + (cL or []) + (rL or []):
      x["estate"] = e["id"]
    mL = keep("midland") if mL is None else mL
    cL = keep("centanet") if cL is None else cL
    rL = keep("ricacorp") if rL is None else rL
    print(f"  midland {len(mL)}  centanet {len(cL)}/{cN}  ricacorp {len(rL)}/{rN}")
    allL += mL + cL + rL
    if mR is None or cR is None:
      rents = prev.get("rents", [])
    else:
      rents = [r for r in mR + cR if r.get("rent") and r.get("area")]
    estates_out.append(dict(id=e["id"], name=e["name"], area=e["area"], meta=meta, rents=rents,
                            counts=dict(midland=mN, centanet=cN, ricacorp=rN),
                            links=dict(
                              midland=f"https://www.midland.com.hk/zh-hk/list/buy/{up.quote(e['name'])}-E-{e['mid']}",
                              centanet=(f"https://hk.centanet.com/findproperty/list/buy/{up.quote(e['name'])}_{e['cen']}" if e.get("cen") else f"https://hk.centanet.com/findproperty/list/buy?q={up.quote(e['name'])}"),
                              ricacorp=f"https://www.ricacorp.com/zh-hk/property/list/buy/{up.quote(e['ric'])}")))
  # 中原成交紀錄：用嚟判斷已下架放盤係咪已售出
  oldT = load_old("transactions.json") or {}
  T = {}
  for e in ESTATES:
    try:
      T[e["id"]] = centanet_tx(e)
    except Exception as ex:
      print("  成交失敗:", e["name"], str(ex)[:80]); T[e["id"]] = oldT.get(e["id"], [])
  save("transactions.json", T)
  print("成交紀錄", sum(len(v) for v in T.values()))
  for k, v in ok.items():
    st_ = status.setdefault(k, {})
    st_["ok"] = v; st_["checked"] = now
    if v and not (k == "midland" and MF): st_["last_ok"] = now
  json.dump(PUBCACHE, open(PUBF, "w"))
  save("status.json", status)
  save("estates.json", estates_out)
  save("listings_agency.json", allL)


if __name__ == "__main__":
  what = sys.argv[1:] or ["market", "listings"]
  if "market" in what:
    market()
  if "midland" in what:
    midland_all()
  if "listings" in what:
    listings()
