#!/usr/bin/env python3
"""將指定檔案 commit 並 push（Windows / Mac / Linux 通用）"""
import subprocess, sys
files = sys.argv[1:]
run = lambda *a: subprocess.run(["git", *a], check=False)
run("config", "user.name", "github-actions[bot]")
run("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("add", *files)
if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
    print("冇改變"); sys.exit(0)
run("commit", "-m", "美聯資料更新")
for _ in range(3):
    run("pull", "--rebase")
    if subprocess.run(["git", "push"]).returncode == 0:
        sys.exit(0)
sys.exit(1)
