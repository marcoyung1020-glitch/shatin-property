#!/usr/bin/env python3
"""資料檔存喺 data 分支（每次只保留一個 commit，repository 唔會越嚟越大）。
用法：
  python scripts/push_data.py pull                 # 由 data 分支取回所有資料檔
  python scripts/push_data.py push FILE [FILE...]  # 上載自己負責嘅檔案，其餘沿用 data 分支現有版本
Windows / Mac / Linux 通用。"""
import os, subprocess, sys, tempfile

FILES = ["data/first_seen.json", "data/midland_first_pub.json",
         "site/data/app.json", "site/data/estates.json", "site/data/listings_agency.json",
         "site/data/market.json", "site/data/midland.json", "site/data/status.json"]

def git(*a, env=None, check=True):
    r = subprocess.run(["git", *a], capture_output=True, text=True, env=env)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(a)} 失敗：{r.stderr.strip()}")
    return r.stdout.strip()

def fetch():
    r = subprocess.run(["git", "fetch", "-q", "origin", "+refs/heads/data:refs/remotes/origin/data"], capture_output=True, text=True)
    return r.returncode == 0 and bool(git("rev-parse", "-q", "--verify", "refs/remotes/origin/data", check=False))

def take(paths):
    for p in paths:
        blob = subprocess.run(["git", "show", f"origin/data:{p}"], capture_output=True)
        if blob.returncode == 0:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(blob.stdout)

def pull():
    if fetch():
        take(FILES); print("已取回 data 分支資料")
    else:
        print("未有 data 分支")

def push(own):
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    for _ in range(4):
        have = fetch()
        old = git("rev-parse", "origin/data") if have else ""
        if have:
            take([f for f in FILES if f not in own])  # 唔係自己負責嘅檔案用最新版本
        idx = os.path.join(tempfile.mkdtemp(), "index")
        env = dict(os.environ, GIT_INDEX_FILE=idx)
        git("add", "-f", *[f for f in FILES if os.path.exists(f)], env=env)
        tree = git("write-tree", env=env)
        sha = git("commit-tree", tree, "-m", "資料更新", env=env)
        r = subprocess.run(["git", "push", "-q", f"--force-with-lease=refs/heads/data:{old}", "origin", f"{sha}:refs/heads/data"], capture_output=True, text=True)
        if r.returncode == 0:
            print("已上載", ", ".join(own)); return
        print("重試：", r.stderr.strip()[:200])
    raise SystemExit("上載失敗")

if __name__ == "__main__":
    if sys.argv[1] == "pull":
        pull()
    else:
        push(sys.argv[2:])
