# 沙田睇樓平台
每晚 10:00（香港時間）由 GitHub Actions 自動更新（`.github/workflows/update.yml`），並發布到 GitHub Pages。亦可喺 Actions 頁面撳「Run workflow」手動更新。

- `scripts/update.sh`：一鍵更新（市場數據、HIBOR、美聯／中原／利嘉閣放盤、整合）
- `scripts/collect.py`：CCL、差估署、土地註冊處、三大代理放盤
- `scripts/hibor.py`：銀行公會 HIBOR
- `scripts/build.py`：整合成 `site/data/app.json`
- `data/midland_first_pub.json`：美聯首次刊登日期快取（只讀新盤詳情頁）
- `data/first_seen.json`：每條放盤首次收錄時間；`_base` 係開始追蹤時間
- 「首次出現」＝刊登時間同首次收錄時間取最早；合併單位取各代理最早
