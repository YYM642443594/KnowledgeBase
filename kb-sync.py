#!/usr/bin/env python3
"""KnowledgeBase viewer pipeline: fetch -> protocol sync -> build -> commit & push.

Single source of truth: origin/develop on GitHub. This clone is a build worker:
it fast-forwards to origin/develop, syncs 志翔 protocol docs from WorkRecord,
rebuilds 知识库.html in place (repo root, no separate folder), and pushes one
viewer commit if anything changed. A push race is retried by re-aligning to
the new remote head and rebuilding. Local divergence is auto-reset ONLY when
every unpushed local commit is viewer-generated; anything else aborts loudly
(so manual/script edits are never silently discarded — push them first).

Usage:
  python3 kb-sync.py           # normal run
  python3 kb-sync.py --force   # commit+push even if the rebuild produced no diff
  python3 kb-sync.py --build-only   # rebuild from local files, no network, no push

Exit codes: 0 = success (PUSHED or SKIP_PUSH), 1 = failure (prints FETCH_FAIL/PUSH_FAIL/COMMIT_FAIL/BUILD_FAIL).
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "知识库.html")
COMMITS_JSON = os.path.join(HERE, "kb-commits.json")
STATE = os.path.join(HERE, "kb-protocols.json")
BRANCH = "develop"
MARKER = "自动: 知识库viewer"          # viewer-generated commits (never treated as content)
COMMIT_MSG = "更新可视化浏览HTML+志翔协议文档同步 (自动: 知识库viewer)"

def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=HERE,
                          env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, **kw)

def fail(msg):
    print(msg); sys.exit(1)

def git_out(cmd):
    r = sh(cmd)
    return r.stdout.strip() if r.returncode == 0 else ""

def sync_to_remote():
    """Align local develop with origin/develop. Returns remote head sha.
    Dirty working tree aborts (protects manual edits). Divergence auto-resets
    only if all unpushed local commits are viewer-generated (rebuild reproduces
    them); any real local commit aborts instead of being discarded."""
    if sh("git status --porcelain").stdout.strip():
        fail("FETCH_FAIL: working tree dirty, refusing to sync (commit or clean first)")
    r = sh(f"git fetch origin {BRANCH}")
    if r.returncode != 0:
        fail("FETCH_FAIL: " + (r.stderr or r.stdout)[:300])
    head = git_out(f"git rev-parse origin/{BRANCH}")
    if not head:
        fail("FETCH_FAIL: cannot resolve origin/" + BRANCH)
    if sh(f"git merge --ff-only origin/{BRANCH}").returncode != 0:
        subjects = sh(f"git log --format=%s origin/{BRANCH}..{BRANCH}").stdout.strip().splitlines()
        real = [s for s in subjects if MARKER not in s]
        if real:
            fail("FETCH_FAIL: local has unpushed real commits (push them first): " +
                 " | ".join(s[:60] for s in real[:3]))
        rst = sh(f"git reset --hard origin/{BRANCH}")
        if rst.returncode != 0:
            fail("FETCH_FAIL: cannot align with remote: " + (rst.stderr or "")[:200])
    return head

def fetch_commits():
    """Recent commits for the viewer panel — real content changes only.
    Walks history until LIMIT real commits are collected (viewer-generated
    ones never count), so pushing a viewer commit does not slide the window
    and re-embed a different history — otherwise every push would churn out
    another diff forever."""
    LIMIT = 30
    out = git_out(
        f'git log origin/{BRANCH} -200 --format=%H%x09%ad%x09%s --date=format:"%Y-%m-%d %H:%M"')
    if not out:
        return None
    commits = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        sha, date, msg = parts
        if MARKER in msg:
            continue
        commits.append({"sha": sha[:8], "date": date, "msg": msg[:60]})
        if len(commits) >= LIMIT:
            break
    return commits or None

def sync_protocols(force=False):
    """Sync 志翔 protocol docs from WorkRecord@feature/zhixiang. Fails hard on error."""
    if force and os.path.exists(STATE):
        os.remove(STATE)
    r = subprocess.run([sys.executable, os.path.join(HERE, "kb-sync-protocols.py")],
                       capture_output=True, text=True)
    status = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if status not in ("PROTOCOLS_UPDATED", "PROTOCOLS_SAME"):
        fail("FETCH_FAIL: protocol sync: " + (status or (r.stderr or "no output")[:200]))
    print("PROTOCOLS: " + status)

def build_once():
    """Rebuild 知识库.html from the current working tree and commit history."""
    commits = fetch_commits()
    if not commits:
        fail("FETCH_FAIL: cannot read commit history")
    with open(COMMITS_JSON, "w", encoding="utf-8") as f:
        json.dump({"_meta": {"content_head": commits[0]["sha"]}, "commits": commits},
                  f, ensure_ascii=False, indent=1)
    sys.path.insert(0, HERE)
    import kb_build_viewer
    kb_build_viewer.build(commits)
    html = open(HTML, encoding="utf-8").read()
    if "__KB_DATA__" in html or "__MARKED_JS__" in html or len(html) < 100000:
        fail("BUILD_FAIL: placeholder left in output")

def commit_and_push(force=False):
    """Commit staged changes (if any) and push. True on success."""
    sh("git add -A")
    staged = sh("git status --porcelain").stdout.strip()
    if not staged and not force:
        print("SKIP_PUSH: nothing changed")
        return True
    msg = COMMIT_MSG + (" (force)" if not staged else "")
    if sh(f'git commit --allow-empty -m "{msg}"').returncode != 0:
        fail("COMMIT_FAIL: " + (sh("git status --porcelain").stdout or "commit error")[:300])
    ok = sh(f"git push origin {BRANCH}").returncode == 0
    print("PUSHED " + git_out("git rev-parse --short HEAD") if ok else "PUSH_REJECTED")
    return ok

def main():
    force = "--force" in sys.argv

    if "--build-only" in sys.argv:
        doc = json.load(open(COMMITS_JSON, encoding="utf-8"))
        commits = doc.get("commits") if isinstance(doc, dict) else doc
        sys.path.insert(0, HERE)
        import kb_build_viewer
        kb_build_viewer.build(commits)
        print("BUILD_ONLY")
        return

    sync_to_remote()
    for attempt in (1, 2, 3):
        sync_protocols(force=(attempt > 1))
        build_once()
        if commit_and_push(force=force and attempt == 1):
            return
        print(f"PUSH_RETRY: push rejected, re-aligning with origin (attempt {attempt}/3)")
        sync_to_remote()
    fail("PUSH_FAIL: push rejected after 3 realign attempts")

if __name__ == "__main__":
    main()
