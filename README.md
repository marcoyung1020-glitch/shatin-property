# 沙田睇樓平台
- `python3 scripts/collect.py market listings`：收集 CCL、差估署、土地註冊處、美聯／中原／利嘉閣放盤
- `python3 scripts/hibor.py`：銀行公會 HIBOR
- 28Hse / House730 頁面另存於 /tmp/portal 後執行 `python3 scripts/parse_portals.py`
- `python3 scripts/build.py`：整合成 site/data/app.json
