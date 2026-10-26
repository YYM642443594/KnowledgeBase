#!/usr/bin/env python3
"""Midnight push job (automation 66c4388b): incremental sync -> build -> push only if content changed.

All state lives inside the repo at ~/KnowledgeBase (no separate viewer folder).
Run:  python3 ~/KnowledgeBase/kb-midnight-push.py
Output status lines: PUSHED / SKIP_PUSH = success; *_FAIL = failure.
Loop protection lives in kb-sync.py (viewer-generated commits never anchor content HEAD).
"""
import sys, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
# incremental (no --force): SKIP_SYNC/SKIP_PUSH when remote HEAD is unchanged or viewer-generated
r = subprocess.run([sys.executable, os.path.join(HERE, "kb-sync.py")])
sys.exit(r.returncode)
