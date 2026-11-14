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
CARDS_JSON = os.path.join(HERE, "00-索引", "项目卡片.json")
OUT = os.path.join(HERE, "知识库.html")

# When set (by kb-sync.py) the viewer header shows this content HEAD instead of
# commits[0], keeping rebuilds stable across viewer/script-only commits.
HEAD_OVERRIDE = None

# section metadata: id, dir, icon, color, description[, display label]
# dir: single directory name (str), or a tuple of names for a multi-root section.
SECTIONS = [
    ("esp",    "ESP",           "📡", "#4f8cff", "ESP32 / ESP32-CAM / ESP8266 三个芯片平台的固件工程知识：透传、网页终端、视频监控、五云协议、踩坑记录"),
    ("imu",    "IMU",           "🧭", "#3fb27f", "GD32F103 / GD32F303 两个 MCU 平台的 IMU 固件知识：串口丢字节、参数页迁移、指令集、PPS 功能"),
    ("stm32",  "STM32",         "🔧", "#5a9bd4", "STM32_F10x 工程知识：MAX7219 点阵显示、四层改三层架构重构、跨仓库工程架构规范"),
    ("qt",     "QT-Tools",      "🖥", "#e2a03f", "志翔 IMU 上位机（Qt 6 / QML）：Hex 指令、蓝牙、波形与页面性能优化、协议开发规范"),
    ("linux",  "Linux-Scripts", "🐧", "#e05c5c", "常用机环境脚本：Claude Code / OpenClaw 安装配置、FTP 服务、硬盘挂载、依赖清理"),
    ("proto",  "Protocols",     "📜", "#9b6ce0", "志翔协议文档（同步自 WorkRecord@feature/zhixiang）：IMU 通讯协议与指令、坐标系示意、自动售水机通信协议（二进制帧 / MQTT JSON）"),
    ("kb",     ("00-索引", "01-技术笔记", "02-项目文档", "03-问题排查", "04-工具使用",
                "05-读书笔记", "06-参考资料", "07-日常记录"),
                               "📚", "#7a8b99", "规范沉淀区：按主题分类的跨平台知识文档（技术笔记、项目文档、问题排查、工具使用等）",
               "00~07 目录"),
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

# T2 (KNOWLEDGE-12): 00-索引/项目卡片.json → 查看器「项目总览」视图。
# 只做解析 + 相对链接校验 + 内嵌，不改写清单内容；链接失效/清单缺失一律打印
# WARNING（不静默跳过），构建继续进行，由人工按警告决定是否返工数据。
DIM_KEYS = ("features", "chips", "commands", "issues")

def _norm_rel(p):
    return str(p).replace("\\", "/").strip()

def _resolve_card_link(rel, by_path):
    """校验卡片内相对链接。返回 (embed_extra, status):
    - ("", "embedded") 指向查看器已收录文档 → 模板运行时经 KB.byPath 解析为站内路由；
    - (rel, "external") 文件在仓库存在但未被查看器收录（如 .json 等）→ 下发 link 字段，
      模板以相对路径直链（file:// 下有效，查看器位于仓库根目录）；
    - ("", "missing") 文件不存在 → 下发 bad 标记，模板按失效条目渲染并注明。"""
    rel = _norm_rel(rel)
    if not rel:
        return "", "missing"
    if rel in by_path:
        return "", "embedded"
    if os.path.isfile(os.path.join(HERE, rel)):
        return rel, "external"
    return "", "missing"

def load_project_cards(by_path):
    """解析项目卡片清单，返回 (projects, meta) 供内嵌；所有异常路径都以 WARNING 呈现。"""
    rel = os.path.relpath(CARDS_JSON, HERE)
    if not os.path.isfile(CARDS_JSON):
        print(f"WARNING: 项目卡片清单缺失: {rel}")
        print("WARNING: 「项目总览」将渲染为空（模板回退为原首页），请检查 00-索引/项目卡片.json 是否存在")
        return [], {}
    try:
        with open(CARDS_JSON, encoding="utf-8") as f:
            raw = json.load(f)
    except ValueError as e:
        print(f"WARNING: 项目卡片清单解析失败（非合法 JSON）: {e}")
        print("WARNING: 「项目总览」将渲染为空，请修复清单后重建")
        return [], {}
    projects_in = raw.get("projects")
    meta_in = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
    if not isinstance(projects_in, list) or not projects_in:
        print("WARNING: 项目卡片清单缺少 projects 列表或为空，「项目总览」将渲染为空")
        return [], {}
    warnings = []
    projects, n_entries, n_docs = [], 0, 0
    for i, p in enumerate(projects_in, 1):
        if not isinstance(p, dict) or not p.get("id") or not p.get("name"):
            warnings.append(f"projects[{i}] 缺少 id/name 字段，该卡片无法渲染，已跳过")
            continue
        card = {k: p.get(k, "") for k in ("id", "name", "dir", "summary", "note", "updated")}
        if p.get("dir") and not os.path.isdir(os.path.join(HERE, _norm_rel(p["dir"]))):
            warnings.append(f"{p['id']}: dir 指向不存在的目录 {p['dir']}")
        for key in DIM_KEYS:
            entries = []
            for e in (p.get(key) or []):
                if not isinstance(e, dict) or not e.get("item"):
                    warnings.append(f"{p['id']}.{key}: 存在缺少 item 的条目，已跳过")
                    continue
                ent = {"item": e["item"]}
                if e.get("source"):
                    ent["source"] = _norm_rel(e["source"])   # 运行时经 KB.byPath 解析为站内路由
                    n_entries += 1
                    extra, status = _resolve_card_link(e["source"], by_path)
                    if status == "missing":
                        ent["bad"] = 1
                        warnings.append(f"{p['id']}.{key}: 「{str(e['item'])[:30]}…」出处链接失效: {e['source']}")
                    elif status == "external":
                        ent["link"] = extra
                        warnings.append(f"{p['id']}.{key}: 出处未被查看器收录（已按相对路径直链）: {e['source']}")
                else:
                    ent["bad"] = 1
                    warnings.append(f"{p['id']}.{key}: 「{str(e['item'])[:30]}…」未注明出处 source")
                entries.append(ent)
            card[key] = entries
        docs = []
        for d in (p.get("docs") or []):
            path = d.get("p") if isinstance(d, dict) else d
            if not path:
                warnings.append(f"{p['id']}.docs: 存在空链接条目，已跳过")
                continue
            n_docs += 1
            extra, status = _resolve_card_link(path, by_path)
            if status == "embedded":
                docs.append(path)                      # 运行时经 KB.byPath 解析
            elif status == "external":
                docs.append({"p": path, "link": extra})
                warnings.append(f"{p['id']}.docs: 文档未被查看器收录（已按相对路径直链）: {path}")
            else:
                docs.append({"p": path, "bad": 1})
                warnings.append(f"{p['id']}.docs: 链接失效: {path}")
        card["docs"] = docs
        projects.append(card)
    meta = {
        "updated": meta_in.get("updated", ""),
        "source": rel.replace(os.sep, "/"),
        "nonProject": [
            {"dir": x.get("dir", ""), "reason": x.get("reason", "")}
            for x in (meta_in.get("non_project_dirs") or []) if isinstance(x, dict)
        ],
    }
    for w in warnings:
        print("WARNING: 项目卡片 " + w)
    tail = f"，{len(warnings)} 条警告（见上）" if warnings else "，无警告"
    print(f"项目卡片: {len(projects)} 个项目 / {n_entries} 条四维度条目 / {n_docs} 条文档链接已校验{tail}")
    return projects, meta

def build(commits):
    """Render viewer HTML for the given commits list. Returns the html string."""
    data = []
    for section in SECTIONS:
        sid, d, icon, color, desc = section[:5]
        label = section[5] if len(section) > 5 else (d if isinstance(d, str) else "/".join(d))
        roots = d if isinstance(d, tuple) else (d,)
        docs = []
        for root_dir in roots:
            base = os.path.join(HERE, root_dir)
            for root, dirs, files in os.walk(base):
                dirs.sort()
                for fn in sorted(files):
                    if not fn.lower().endswith((".md", ".markdown")): continue
                    if sid == "kb" and fn == "README.md":
                        continue  # 01~07 目录的占位 README（工程区为 Readme.md，不受影响）
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
        data.append({"id": sid, "name": label, "dir": label + "/", "icon": icon, "color": color,
                     "desc": desc, "docs": docs, "bytes": sum(x["sizeKB"] * 1024 for x in docs)})

    by_path = {}
    for s in data:
        for x in s["docs"]:
            by_path[x["relPath"]] = x["hash"]

    # embed referenced images as data URIs (viewer must be self-contained, opened via file://)
    images = {}
    for section in SECTIONS:
        d = section[1]
        for root_dir in (d if isinstance(d, tuple) else (d,)):
            imgdir = os.path.join(HERE, root_dir, "00.Image")
            if not os.path.isdir(imgdir): continue
            for fn in os.listdir(imgdir):
                if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".gif")): continue
                ext = fn.rsplit(".", 1)[1].lower()
                mime = "image/png" if ext == "png" else ("image/gif" if ext == "gif" else "image/jpeg")
                with open(os.path.join(imgdir, fn), "rb") as f:
                    images[root_dir + "/00.Image/" + fn] = f"data:{mime};base64," + base64.b64encode(f.read()).decode()

    # HEAD_OVERRIDE: content head pinned by kb-sync.py (newest real commit),
    # so a rebuild right after a script-only push renders identically.
    head = HEAD_OVERRIDE or (commits[0]["sha"] if commits else "unknown")

    tpl = read(TEMPLATE)
    marked = read(MARKED)
    assert "</script" not in marked.lower(), "marked contains </script>!"

    # T2: 项目卡片清单解析与链接校验（缺失/失效打 WARNING，不中断构建）
    projects, projects_meta = load_project_cards(by_path)
    kb_data = {"sections": data, "byPath": by_path, "images": images,
               "projects": projects, "projectsMeta": projects_meta}
    cards_dump = json.dumps({"projects": projects, "projectsMeta": projects_meta},
                            ensure_ascii=False, separators=(",", ":"))
    assert "</script" not in cards_dump.lower(), "project cards contain </script>!"

    html = tpl.replace("__MARKED_JS__", marked)
    html = html.replace("__KB_DATA__", json.dumps(kb_data, ensure_ascii=False, separators=(",", ":")))
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
    doc = json.load(open(COMMITS_JSON, encoding="utf-8"))
    commits = doc.get("commits") if isinstance(doc, dict) else doc
    build(commits)
