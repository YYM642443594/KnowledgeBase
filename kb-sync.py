#!/usr/bin/env python3
"""KnowledgeBase viewer pipeline: sync check -> build -> commit & push.

Usage:
  python3 kb-sync.py           # incremental: fetch remote, compare content HEAD, build if changed
  python3 kb-sync.py --force   # force rebuild + commit/push even if content HEAD unchanged
  python3 kb-sync.py --build-only   # rebuild from local files, no fetch, no push

Exit codes: 0 = success (PUSHED or SKIP_PUSH), 1 = failure (prints FETCH_FAIL/PUSH_FAIL/COMMIT_FAIL/BUILD_FAIL).
"""
import json, os, subprocess, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "知识库-可视化浏览.html")
COMMITS_JSON = os.path.join(HERE, "kb-commits.json")
URL = "https://api.github.com/repos/YYM642443594/KnowledgeBase/commits/develop"
BRANCH = "develop"
MARKER = "自动: 知识库viewer"          # viewer-generated commits (not real content changes)
FALLBACK_CONTENT_SHA = "4b218314"       # last real content HEAD anchor

def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)

def fail(msg):
    print(msg); sys.exit(1)

def remote_head():
    r = sh(f'curl -s --max-time 30 "{URL}"')
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout).get("sha")
    except Exception:
        return None

def is_content_sha(sha):
    """True if this remote HEAD commit is a real content change (not viewer-generated).
    We can't always see the commit message from /commits/develop alone cheaply, so:
    a sha counts as content if it differs from our known viewer-generated shas.
    Loop protection: anchor content HEAD at FALLBACK_CONTENT_SHA when unknown."""
    if not sha:
        return False
    if sha.startswith(FALLBACK_CONTENT_SHA[:7]):
        return True
    # check commit message via API
    r = sh(f'curl -s --max-time 30 "https://api.github.com/repos/YYM642443594/KnowledgeBase/commits/{sha}"')
    if r.returncode == 0 and r.stdout.strip():
        try:
            msg = json.loads(r.stdout).get("commit", {}).get("message", "")
            return MARKER not in msg
        except Exception:
            return False
    return False

def fetch_commits():
    r = sh(f'curl -s --max-time 30 "https://api.github.com/repos/YYM642443594/KnowledgeBase/commits?sha={BRANCH}&per_page=25"')
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        commits = json.loads(r.stdout)
        if not isinstance(commits, list): return None
        return [{"sha": c["sha"][:8],
                 "date": c["commit"]["author"]["date"].replace("T", " ")[:16],
                 "msg": c["commit"]["message"].splitlines()[0][:60],
                 "author": c.get("author", {}).get("login") or c["commit"]["author"]["name"]}
                for c in commits]
    except Exception:
        return None

def main():
    force = "--force" in sys.argv
    build_only = "--build-only" in sys.argv

    old = {}
    if os.path.exists(COMMITS_JSON):
        try: old = json.load(open(COMMITS_JSON, encoding="utf-8"))
        except Exception: pass
    old_meta = old.get("_meta", {}) if isinstance(old, dict) else {}
    old_head = old_meta.get("content_head", "")
    old_head = old_head or (old[0]["sha"] if isinstance(old, list) and old else "")

    if build_only:
        raw = old if isinstance(old, list) and old else (old.get("commits", []) if isinstance(old, dict) else [])
        import kb_build_viewer
        kb_build_viewer.build(raw)
        print("BUILD_ONLY")
        return

    head = remote_head()
    if not head:
        fail("FETCH_FAIL: cannot reach GitHub API")

    # protocol docs: sync from WorkRecord (gitee feature/zhixiang) before any skip decision
    proto = sh(sys.executable + ' "' + os.path.join(HERE, "kb-sync-protocols.py") + '"')
    proto_status = proto.stdout.strip().splitlines()[-1] if proto.stdout.strip() else ""
    if proto_status not in ("PROTOCOLS_UPDATED", "PROTOCOLS_SAME"):
        fail("FETCH_FAIL: protocol sync: " + (proto_status or (proto.stderr or "no output")[:200]))
    print("PROTOCOLS: " + proto_status)

    if not force and proto_status == "PROTOCOLS_SAME" and old_head and head.startswith(old_head[:7]):
        print("SKIP_SYNC: remote HEAD matches last built content HEAD", old_head)
        print("SKIP_PUSH")
        return

    if not force and proto_status == "PROTOCOLS_SAME" and not is_content_sha(head):
        print("SKIP_SYNC: remote HEAD is viewer-generated (loop protection), content unchanged")
        print("SKIP_PUSH")
        return

    commits = fetch_commits()
    if commits is None:
        fail("FETCH_FAIL: cannot fetch commit list")
    assert isinstance(old, dict) or isinstance(old, list)

    # loop protection: drop viewer-generated commits from the embedded list and
    # anchor content_head at the newest real content commit
    content_head = FALLBACK_CONTENT_SHA
    for c in commits:
        if MARKER not in c["msg"]:
            content_head = c["sha"]
            break

    new_doc = {"_meta": {"content_head": content_head}, "commits": commits}
    with open(COMMITS_JSON, "w", encoding="utf-8") as f:
        json.dump(new_doc, f, ensure_ascii=False, indent=1)

    sys.path.insert(0, HERE)
    import kb_build_viewer
    try:
        kb_build_viewer.build(commits)
    except Exception as e:
        fail(f"BUILD_FAIL: {e}")

    # integrity check
    html = open(HTML, encoding="utf-8").read()
    if "__KB_DATA__" in html or "__MARKED_JS__" in html or len(html) < 100000:
        fail("BUILD_FAIL: placeholder left in output")

    if not force and proto_status == "PROTOCOLS_SAME" and old_head and content_head.startswith(old_head[:7]):
        print("SKIP_PUSH: content unchanged (only metadata refreshed)")
        return

    # commit & push via SSH
    os.chdir(HERE)
    if sh("git add -A && git commit -m '更新可视化浏览HTML+志翔协议文档同步 (自动: 知识库viewer)'").returncode != 0:
        out = sh("git status --porcelain").stdout.strip()
        if out:
            fail("COMMIT_FAIL: " + out)
        print("SKIP_PUSH: nothing to commit")
        return
    p = sh("git push origin " + BRANCH)
    if p.returncode != 0:
        fail("PUSH_FAIL: " + (p.stderr or p.stdout)[:300])
    print("PUSHED")

if __name__ == "__main__":
    main()
