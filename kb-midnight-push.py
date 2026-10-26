#!/usr/bin/env python3
"""Midnight push job (automation 66c4388b): incremental sync -> build -> push if content changed.

All state lives inside the repo at ~/KnowledgeBase (no separate viewer folder).
Run:  python3 ~/KnowledgeBase/kb-midnight-push.py
Output status lines: PUSHED / SKIP_PUSH = success; *_FAIL = failure.
"""
import sys, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
r = subprocess.run([sys.executable, os.path.join(HERE, "kb-sync.py"), "--force"] + sys.argv[1:])
sys.exit(r.returncode)
