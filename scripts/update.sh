#!/usr/bin/env bash
# 一鍵更新（28Hse / House730 頁面要先由 fetch_portals.mjs 讀入 data/portal/）
set -e
cd "$(dirname "$0")/.."
python3 -u scripts/collect.py market listings
python3 -u scripts/hibor.py
python3 -u scripts/parse_portals.py
python3 -u scripts/build.py
git add -A && git commit -qm "自動更新 $(TZ=Asia/Hong_Kong date '+%Y-%m-%d %H:%M')" || true
