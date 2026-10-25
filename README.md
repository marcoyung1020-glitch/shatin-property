# 沙田睇樓平台
- `scripts/update.sh`：一鍵更新所有資料（市場數據、HIBOR、三大代理放盤、整合、git commit）
- 28Hse / House730 會擋 curl，要喺 exec 環境執行 `scripts/fetch_portals.mjs`（用 fetch_url）讀入 `data/portal/`
- `data/midland_first_pub.json`：美聯首次刊登日期快取（只會讀新盤嘅詳情頁）
- `data/first_seen.json`：每條放盤首次被本平台收錄嘅時間；`_base` 係開始追蹤時間
- 「首次出現」＝各來源刊登時間同首次收錄時間取最早；合併單位取各網站最早
