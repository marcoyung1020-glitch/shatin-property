# 沙田睇樓平台
香港時間 10:00 至 22:00 每 2 小時更新：提早 15 分鐘喺香港電腦（self-hosted runner）讀美聯（`.github/workflows/midland.yml`，因為 GitHub 伺服器被美聯擋）；整點由 GitHub Actions 更新其餘資料並發布到 GitHub Pages（`.github/workflows/update.yml`）。

資料檔唔存喺 main，而係存喺 `data` 分支，每次只保留一個 commit（`scripts/push_data.py pull / push`），repository 唔會越嚟越大。亦可喺 Actions 頁面撳「Run workflow」手動更新。

- `python scripts/collect.py midland`：只讀美聯，存入 `site/data/midland.json`
- `scripts/update.sh`：一鍵更新（市場數據、HIBOR、美聯／中原／利嘉閣放盤、整合）
- `scripts/collect.py`：CCL、差估署、土地註冊處、三大代理放盤
- `scripts/hibor.py`：銀行公會 HIBOR
- `scripts/build.py`：整合成 `site/data/app.json`
- `data/midland_first_pub.json`：美聯首次刊登日期快取（只讀新盤詳情頁）
- `data/first_seen.json`：每條放盤首次收錄時間；`_base` 係開始追蹤時間
- 「首次出現」＝刊登時間同首次收錄時間取最早；合併單位取各代理最早
