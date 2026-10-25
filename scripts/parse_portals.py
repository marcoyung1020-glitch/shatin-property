#!/usr/bin/env python3
"""Parse fetched House730 / 28Hse markdown pages (/tmp/portal/*.md) into site/data/listings_portal.json."""
import json, re, glob, os, datetime

SRC = os.environ.get("PORTAL_DIR", "/tmp/portal")
OUT = os.path.join(os.path.dirname(__file__), "..", "site", "data", "listings_portal.json")

H28 = {"蔚景園":4109,"沙田中心":4086,"河畔花園":4107,"好運中心":4082,"偉華中心":4089,"花園城":4118,
       "希爾頓中心":4095,"富豪花園":4088,"沙田廣場":4099,"翠麗花園":4125,"田園閣":4115,"沙田第一城":4080,
       "碧濤花園":4085,"翠湖花園":4087,"濱景花園":4090}
H730 = {"蔚景園":25940,"沙田中心":26026,"河畔花園":25964,"好運中心":26025,"偉華中心":25942,"花園城":25949,
        "希爾頓中心":25941,"富豪花園":25965,"沙田廣場":25943,"翠麗花園":26029,"田園閣":25947,"沙田第一城":25999,
        "碧濤花園":25934,"翠湖花園":25931,"濱景花園":25930}

def num(s):
    return float(s.replace(",", "")) if s else None

def lines_of(path):
    return [l.strip() for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]

def parse_h730(est, L):
    out = []
    try:
        cut = next(i for i, l in enumerate(L) if l.startswith("已瀏覽所有符合"))
        L = L[:cut]
    except StopIteration:
        pass
    starts = [i for i, l in enumerate(L) if re.match(r"^(沙田|沙田第一城 / 石門|石門|沙田第一城) \S", l) and est in l and "|" not in l and len(l) < 30]
    for k, i in enumerate(starts):
        blk = L[i:(starts[k+1] if k+1 < len(starts) else len(L))]
        t = "\n".join(blk)
        price = re.search(r"售\$([\d,\.]+)\s*萬", t)
        if not price:
            continue
        area = re.search(r"實([\d,]+)呎", t)
        rooms = re.search(r"(\d)房", t)
        floor = re.search(r"(高層|中層|低層|地下)", t)
        psf = re.search(r"\$([\d,]+)/呎", t)
        title = L[i-1] if i > 0 and not re.match(r"^(售|\$|\d)", L[i-1]) and "位於" not in L[i-1] and len(L[i-1]) < 50 else ""
        out.append(dict(source="house730", estate=est, building=re.sub(r"^.*?"+est, est, blk[0]),
            price=num(price.group(1)), area=num(area.group(1)) if area else None,
            rooms=int(rooms.group(1)) if rooms else (0 if "開放式" in t else None),
            floor=floor.group(1) if floor else "", psf=num(psf.group(1)) if psf else None,
            owner="業主" in t and "業主盤" in t, title=title[:60], agency="",
            url=f"https://www.house730.com/buy/e{H730[est]}/"))
    m = re.search(r"共找到 ([\d,]+) 個樓盤", "\n".join(L))
    return out, int(m.group(1).replace(",", "")) if m else None

def parse_h28(est, L):
    out = []
    starts = [i for i, l in enumerate(L) if re.match(r"^沙田 \S+ \|", l) and est in l]
    for k, i in enumerate(starts):
        blk = L[i:(starts[k+1] if k+1 < len(starts) else len(L))]
        t = "\n".join(blk)
        price = re.search(r"售 \$([\d,\.]+) 萬", t)
        if not price:
            continue
        area = re.search(r"實用面積: ([\d,]+) 呎(?: @([\d,]+))?", t)
        rooms = re.search(r"(\d) 房", t)
        floor = re.search(r"(高層|中層|低層|地下)", blk[0])
        ag = next((b[3:] for b in blk if b.startswith("** ") and "刊登" not in b), "")
        bld = blk[0].split("|", 1)[1].strip() if "|" in blk[0] else ""
        out.append(dict(source="28hse", estate=est, building=bld,
            price=num(price.group(1)), area=num(area.group(1)) if area else None,
            rooms=int(rooms.group(1)) if rooms else None, floor=floor.group(1) if floor else "",
            psf=num(area.group(2)) if area and area.group(2) else None,
            owner=("業主" in ag), title="", agency=ag,
            url=f"https://www.28hse.com/buy/a3/dg44/c{H28[est]}"))
    m = re.search(r"共有 ([\d,]+) 個放售樓盤", "\n".join(L))
    return out, int(m.group(1).replace(",", "")) if m else None

def main():
    res = {"generated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="minutes"),
           "listings": [], "totals": {}}
    for est in H28:
        res["totals"][est] = {}
        for prefix, fn, key in (("h730", parse_h730, "house730"), ("h28", parse_h28, "28hse")):
            p = os.path.join(SRC, f"{prefix}_{est}.md")
            if not os.path.exists(p):
                continue
            items, total = fn(est, lines_of(p))
            res["listings"] += items
            res["totals"][est][key] = {"total": total, "parsed": len(items),
                "url": items[0]["url"] if items else (f"https://www.house730.com/buy/e{H730[est]}/" if key == "house730" else f"https://www.28hse.com/buy/a3/dg44/c{H28[est]}")}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    for e, v in res["totals"].items():
        print(e, v.get("house730", {}).get("parsed"), v.get("house730", {}).get("total"), v.get("28hse", {}).get("parsed"), v.get("28hse", {}).get("total"))

if __name__ == "__main__":
    main()
