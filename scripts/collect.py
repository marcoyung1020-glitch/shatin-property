#!/usr/bin/env python3
"""沙田睇樓平台 — 數據收集程式
收集：中原 CCL、差估署指數、土地註冊處登記、HKMA HIBOR、
     美聯 / 中原 / 利嘉閣 放盤（API），輸出 site/data/*.json
28Hse / House730 由 parse_portals.py 另行處理。
"""
import json, re, subprocess, time, datetime as dt, csv, io, os, sys, urllib.parse as up

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site", "data")
os.makedirs(OUT, exist_ok=True)
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
                  url=x.get("detailUrl"), lease=bool(x.get("withLease"))))
  return L, rents, total


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
    d = jget(f"https://www.ricacorp.com/zh-hk/property/api/post?locationId={loc}&offset={(p-1)*10}&page={p}&txType=1",
             headers={"x-custom-header": "www.ricacorp.com/zh-hk/property"})
    if d and d.get("results"):
      posts += d["results"]
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


def listings():
  tok = midland_token()
  estates_out = []
  allL = []
  for e in ESTATES:
    print("==", e["name"])
    mL, mR, meta, mN = midland(e, tok)
    cL, cR, cN = centanet(e)
    rL, rN = ricacorp(e)
    print(f"  midland {len(mL)}  centanet {len(cL)}/{cN}  ricacorp {len(rL)}/{rN}")
    for x in mL + cL + rL:
      x["estate"] = e["id"]
    allL += mL + cL + rL
    rents = [r for r in mR + cR if r.get("rent") and r.get("area")]
    estates_out.append(dict(id=e["id"], name=e["name"], area=e["area"], meta=meta, rents=rents,
                            counts=dict(midland=mN, centanet=cN, ricacorp=rN),
                            links=dict(
                              midland=f"https://www.midland.com.hk/zh-hk/list/buy/{up.quote(e['name'])}-E-{e['mid']}",
                              centanet=(f"https://hk.centanet.com/findproperty/list/buy/{up.quote(e['name'])}_{e['cen']}" if e.get("cen") else f"https://hk.centanet.com/findproperty/list/buy?q={up.quote(e['name'])}"),
                              ricacorp=f"https://www.ricacorp.com/zh-hk/property/list/buy/{up.quote(e['ric'])}",
                              h28=(f"https://www.28hse.com/buy/a3/dg44/c{e['h28']}" if e.get("h28") else None),
                              h730=(f"https://www.house730.com/buy/e{e['h730']}/" if e.get("h730") else None))))
  save("estates.json", estates_out)
  save("listings_agency.json", allL)


if __name__ == "__main__":
  what = sys.argv[1:] or ["market", "listings"]
  if "market" in what:
    market()
  if "listings" in what:
    listings()
