#!/usr/bin/env bash
# 一鍵更新：市場數據、HIBOR、美聯／中原／利嘉閣放盤，整合成 site/data/app.json
set -e
cd "$(dirname "$0")/.."
python3 -u scripts/collect.py market listings
python3 -u scripts/hibor.py
python3 -u scripts/build.py
