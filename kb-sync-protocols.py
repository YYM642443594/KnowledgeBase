#!/usr/bin/env python3
"""Sync 志翔 protocol docs from WorkRecord (gitee, feature/zhixiang) into KnowledgeBase.

Source : /home/yym/sda1/KB_sync/WorkRecord  (clone of git@gitee.com:YYM642443594/WorkRecord.git, branch feature/zhixiang)
Dest   : ~/KnowledgeBase/Protocols/         (mirrors 03.志翔/00.协议文档/, incl. 00.Image/)

Usage: python3 kb-sync-protocols.py   # called by kb-sync.py; prints PROTOCOLS_UPDATED / PROTOCOLS_SAME / PROTOCOLS_FAIL
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLONE = "/home/yym/sda1/KB_sync/WorkRecord"
SRC = os.path.join(CLONE, "03.志翔", "00.协议文档")
DEST = os.path.join(HERE, "Protocols")
STATE = os.path.join(HERE, "kb-protocols.json")
BRANCH = "feature/zhixiang"

README = """# 志翔协议文档

> 自动同步自日常工作仓库 `WorkRecord@feature/zhixiang` 的 `03.志翔/00.协议文档/`（{date}，源 HEAD `{sha}`）。请勿在本目录手工编辑，修改请在 WorkRecord 仓库进行，同步后此处自动更新。

## 文档索引

{index}

## 图片资源

`00.Image/` 内为协议文档引用的坐标系/接线示意图（PNG），已随文档一并同步并在可视化浏览页面中内嵌显示。
"""

def sh(cmd, cwd=None, timeout=90):
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})

def fail(msg):
    print("PROTOCOLS_FAIL: " + msg); sys.exit(1)

def main():
    if not os.path.isdir(os.path.join(CLONE, ".git")):
        fail(f"WorkRecord clone missing at {CLONE}")
    r = sh(f"git fetch origin {BRANCH}", cwd=CLONE)
    if r.returncode != 0:
        fail("gitee fetch failed: " + (r.stderr or r.stdout)[:200])
    head = sh("git rev-parse origin/" + BRANCH, cwd=CLONE).stdout.strip()
    if not head:
        fail("cannot resolve origin/" + BRANCH)
    old = {}
    if os.path.exists(STATE):
        try: old = json.load(open(STATE, encoding="utf-8"))
        except Exception: pass
    if old.get("head") == head and os.path.isdir(DEST):
        print("PROTOCOLS_SAME")
        return

    # rsync reads from the working tree: fast-forward it to origin head first,
    # otherwise new protocol commits would copy stale files.
    st = sh("git status --porcelain", cwd=CLONE).stdout.strip()
    if st:
        fail("WorkRecord clone has local changes, refusing fast-forward: " + st[:200])
    ff = sh(f"git checkout {BRANCH} && git merge --ff-only origin/{BRANCH}", cwd=CLONE)
    if ff.returncode != 0:
        fail("fast-forward failed: " + (ff.stderr or ff.stdout)[:200])

    if not os.path.isdir(SRC):
        fail(f"source dir missing: {SRC}")
    r = sh(f'rsync -a --delete --exclude .git "{SRC}/" "{DEST}/"')
    if r.returncode != 0:
        fail("rsync failed: " + (r.stderr or "")[:200])

    docs = sorted(fn for fn in os.listdir(DEST) if fn.lower().endswith(".md"))
    index = "\n".join(f"- [{fn[:-3]}]({fn})" for fn in docs if fn != "Readme.md")
    date = sh('git log -1 --format=%as origin/' + BRANCH, cwd=CLONE).stdout.strip() or "?"
    with open(os.path.join(DEST, "Readme.md"), "w", encoding="utf-8") as f:
        f.write(README.format(date=date, sha=head[:8], index=index))

    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"head": head, "syncedAt": sh("date +%F' '%T").stdout.strip()}, f, ensure_ascii=False, indent=1)
    print("PROTOCOLS_UPDATED")

if __name__ == "__main__":
    main()
