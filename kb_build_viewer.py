#!/usr/bin/env python3
"""Build the self-contained HTML viewer for the KnowledgeBase repo (develop branch).

All inputs/outputs live inside this repo (~/KnowledgeBase). Run kb-sync.py instead
of calling this directly — it handles incremental checks and git push.
"""
import json, re, os, base64

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "kb-viewer-template.html")
MARKED = os.path.join(HERE, "marked.min.js")
COMMITS_JSON = os.path.join(HERE, "kb-commits.json")
OUT = os.path.join(HERE, "知识库.html")

# section metadata: id, dir, icon, color, description
SECTIONS = [
    ("esp",    "ESP",           "📡", "#4f8cff", "ESP32 / ESP32-CAM / ESP8266 三个芯片平台的固件工程知识：透传、网页终端、视频监控、五云协议、踩坑记录"),
    ("imu",    "IMU",           "🧭", "#3fb27f", "GD32F103 / GD32F303 两个 MCU 平台的 IMU 固件知识：串口丢字节、参数页迁移、指令集、PPS 功能"),
    ("qt",     "QT-Tools",      "🖥", "#e2a03f", "志翔 IMU 上位机（Qt 6 / QML）：Hex 指令、蓝牙、波形与页面性能优化、协议开发规范"),
    ("linux",  "Linux-Scripts", "🐧", "#e05c5c", "常用机环境脚本：Claude Code / OpenClaw 安装配置、FTP 服务、硬盘挂载、依赖清理"),
    ("proto",  "Protocols",     "📜", "#9b6ce0", "志翔协议文档（同步自 WorkRecord@feature/zhixiang）：IMU 通讯协议与指令、坐标系示意、自动售水机通信协议（二进制帧 / MQTT JSON）"),
]

def read(p):
    with open(p, encoding="utf-8") as f: return f.read()

def front_meta(md):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", md, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            kv = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
            if not kv: continue
            v = kv.group(2).strip()
            if v.startswith("[") and v.endswith("]"):
                v = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
            meta[kv.group(1)] = v
    return meta

def plain_text(md):
    b = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", md, flags=re.S)
    b = re.sub(r"```.*?```", " ", b, flags=re.S)
    b = re.sub(r"`[^`]*`", " ", b)
    b = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", b)
    b = re.sub(r"^#{1,6}\s*", "", b, flags=re.M)
    b = re.sub(r"[*_>|#\[\]]", "", b)
    b = re.sub(r"\s+", " ", b)
    return b.strip()

def desc_of(meta, text):
    d = meta.get("desc") or meta.get("summary")
    if d: return d
    for line in text.split("。"):
        line = line.strip()
        if 20 < len(line) < 160: return line + "。"
    return text[:120] + "…"

def build(commits):
    """Render viewer HTML for the given commits list. Returns the html string."""
    data = []
    for sid, d, icon, color, desc in SECTIONS:
        base = os.path.join(HERE, d)
        docs = []
        for root, dirs, files in os.walk(base):
            dirs.sort()
            for fn in sorted(files):
                if not fn.lower().endswith((".md", ".markdown")): continue
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, HERE)
                md = read(p)
                meta = front_meta(md)
                title = meta.get("title") or fn.rsplit(".", 1)[0]
                docs.append({
                    "hash": rel.replace(os.sep, "/"),
                    "title": title,
                    "relPath": rel.replace(os.sep, "/"),
                    "desc": desc_of(meta, plain_text(md))[:150],
                    "created": meta.get("created", ""),
                    "updated": meta.get("updated", ""),
                    "tags": meta.get("tags", []) if isinstance(meta.get("tags"), list) else ([meta.get("tags")] if meta.get("tags") else []),
                    "sizeKB": round(os.path.getsize(p) / 1024, 1),
                    "_text": plain_text(md)[:6000],
                    "content": md,
                })
        data.append({"id": sid, "name": d, "dir": d + "/", "icon": icon, "color": color,
                     "desc": desc, "docs": docs, "bytes": sum(x["sizeKB"] * 1024 for x in docs)})

    by_path = {}
    for s in data:
        for x in s["docs"]:
            by_path[x["relPath"]] = x["hash"]

    # embed referenced images as data URIs (viewer must be self-contained, opened via file://)
    images = {}
    for sid, d, *_ in SECTIONS:
        imgdir = os.path.join(HERE, d, "00.Image")
        if not os.path.isdir(imgdir): continue
        for fn in os.listdir(imgdir):
            if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".gif")): continue
            ext = fn.rsplit(".", 1)[1].lower()
            mime = "image/png" if ext == "png" else ("image/gif" if ext == "gif" else "image/jpeg")
            with open(os.path.join(imgdir, fn), "rb") as f:
                images[d + "/00.Image/" + fn] = f"data:{mime};base64," + base64.b64encode(f.read()).decode()

    head = commits[0]["sha"] if commits else "unknown"

    tpl = read(TEMPLATE)
    marked = read(MARKED)
    assert "</script" not in marked.lower(), "marked contains </script>!"

    html = tpl.replace("__MARKED_JS__", marked)
    html = html.replace("__KB_DATA__", json.dumps(
        {"sections": data, "byPath": by_path, "images": images}, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("__COMMITS__", json.dumps(commits, ensure_ascii=False))
    html = html.replace("__SYNC_DATE__", commits[0]["date"][:10] if commits else "?")
    html = html.replace("__HEAD_SHA__", head)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK -> {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB, head={head})")
    for s in data:
        print(f"  {s['name']}: {len(s['docs'])} docs")
    return html

if __name__ == "__main__":
    commits = json.load(open(COMMITS_JSON, encoding="utf-8"))
    build(commits)
