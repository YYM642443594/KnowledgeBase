#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""share-hub — 为不同朋友提供相互隔离的只读下载页（单文件、零第三方依赖）"""
import hashlib, html, json, mimetypes, os, posixpath, re, secrets, shutil, sys, time, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlparse, parse_qsl

HOST, PORT = "127.0.0.1", 8080
CONFIG_DIR = os.path.expanduser("~/.config/share-hub")
CONFIG_FILE = os.path.join(CONFIG_DIR, "links.json")
TMP_DIR = "/mnt/sda1/share-hub-tmp"
SCAN_ROOT = "/mnt/sda1/00.FTP"

import threading
_lock = threading.Lock()

# ---------------- 配置 ----------------
def cfg_load():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)

def cfg_save(cfg):
    with _lock:
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_FILE)

def ensure_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        cfg_save({
            "admin_password": secrets.token_urlsafe(9),
            "public_base_url": "",
            "sessions": [],
            "links": {}
        })

# ---------------- 工具 ----------------
def esc(s): return html.escape(str(s), quote=True)

def fmt_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024

def fmt_time(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))

SVG_ICONS = {
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "text": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/>',
    "image": '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="10" r="1.5"/><path d="M21 16l-5-5-9 8"/>',
    "video": '<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3z"/>',
    "audio": '<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
    "archive": '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
    "code": '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4"/><path d="M13 5l-2 14"/>',
    "package": '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5"/><path d="M12 22v-9"/>',
    "download": '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 21h16"/>',
}
_EXT_ICON = {
    "folder": ("pdf", "text", "image", "video", "audio", "archive", "code", "package")
}
def icon_key(name, is_dir):
    if is_dir: return "folder"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext == "pdf": return "text"
    if ext in ("png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "ico", "heic"): return "image"
    if ext in ("mp4", "mkv", "avi", "mov", "flv", "wmv", "webm", "ts"): return "video"
    if ext in ("mp3", "wav", "flac", "aac", "ogg", "m4a"): return "audio"
    if ext in ("zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso"): return "archive"
    if ext in ("py", "c", "h", "cpp", "hpp", "js", "ts", "sh", "json", "yml", "yaml", "toml", "xml", "html", "css", "lua", "rs", "go", "java", "ini", "conf", "s", "ld"): return "code"
    if ext in ("deb", "exe", "msi", "apk", "appimage", "rpm", "dmg"): return "package"
    if ext in ("txt", "md", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "csv", "log", "nfo"): return "text"
    return "file"

def icon_svg(name, is_dir):
    key = icon_key(name, is_dir)
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round">' + SVG_ICONS[key] + "</svg>")

def guess_mime(name):
    m, _ = mimetypes.guess_type(name)
    return m or "application/octet-stream"

# ---------------- 路径安全 ----------------
def resolve_link_path(link, segments):
    """把 URL 相对路径解析为绝对路径；越界返回 None。
    允许目标位于：分享根目录内，或 SCAN_ROOT 内（方便用户用软链把别处的资料挂进分享目录）。"""
    base_r = os.path.realpath(link["path"])
    if not segments:
        return base_r
    target = base_r
    for seg in segments:
        if seg in ("", "."): continue
        target = os.path.join(target, seg)
    rp = os.path.realpath(target)
    prefixes = [base_r, os.path.realpath(SCAN_ROOT)]
    for p in prefixes:
        if rp == p or rp.startswith(p.rstrip(os.sep) + os.sep):
            return rp
    return None

def list_entries(rp):
    try:
        names = os.listdir(rp)
    except PermissionError:
        names = []
    dirs, files = [], []
    for n in names:
        if n.startswith("."): continue
        full = os.path.join(rp, n)
        if os.path.isdir(full): dirs.append(n)
        else: files.append(n)
    key = lambda s: s.lower()
    return sorted(dirs, key=key), sorted(files, key=key)

# ---------------- 打包 zip ----------------
def purge_tmp(max_age=7200):
    now = time.time()
    try:
        for f in os.listdir(TMP_DIR):
            p = os.path.join(TMP_DIR, f)
            try:
                if os.path.isfile(p) and now - os.path.getmtime(p) > max_age:
                    os.unlink(p)
            except OSError:
                pass
    except FileNotFoundError:
        pass

def build_zip(rp, label):
    purge_tmp()
    base_arc = re.sub(r'[\\/:*?"<>|]', "_", label).strip() or "files"
    out = os.path.join(TMP_DIR, f"hub-{int(time.time())}-{secrets.token_hex(4)}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        if os.path.isfile(rp):
            z.write(rp, os.path.basename(rp))
        else:
            count = 0
            for root, dirs, files in os.walk(rp):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in sorted(files):
                    if f.startswith("."): continue
                    full = os.path.join(root, f)
                    arc = os.path.join(base_arc, os.path.relpath(full, rp))
                    z.write(full, arc)
                    count += 1
            if count == 0:
                z.writestr(os.path.join(base_arc, "(空目录).txt"), "此文件夹为空")
    return out

# ---------------- 页面模板 ----------------
CSS = """
:root{--bg:#f4f5f7;--card:#ffffff;--text:#191c24;--muted:#6b7280;--line:#e5e7eb;--accent:#4f6bed;--accent-soft:rgba(79,107,237,.10);--danger:#dc2626}
@media(prefers-color-scheme:dark){:root{--bg:#0e1014;--card:#171a21;--text:#e6e8ee;--muted:#8b92a1;--line:#272c37;--accent:#7b93ff;--accent-soft:rgba(123,147,255,.14);--danger:#f87171}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.65 system-ui,-apple-system,"Segoe UI","Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif}
a{color:var(--accent)}
.wrap{max-width:880px;margin:0 auto;padding:20px 16px 70px}
.top{position:sticky;top:0;z-index:9;background:var(--bg);border-bottom:1px solid var(--line)}
.top::before{content:"";display:block;height:3px;background:linear-gradient(90deg,var(--accent),#9f7bff)}
.top .wrap{padding:12px 16px 10px}
.brand{display:flex;align-items:center;justify-content:space-between;gap:10px}
h1{font-size:17px;margin:0;font-weight:700;display:flex;align-items:center;gap:8px;min-width:0}
h1 .dot{width:9px;height:9px;border-radius:50%;background:var(--accent);flex:none;box-shadow:0 0 0 4px var(--accent-soft)}
.note{color:var(--muted);font-size:13px;margin-top:2px}
.bar{display:flex;align-items:center;gap:10px;margin-top:14px;flex-wrap:wrap}
.crumb{display:flex;flex-wrap:wrap;align-items:center;gap:4px;font-size:13.5px;color:var(--muted);min-width:0}
.crumb a{color:var(--muted);text-decoration:none;padding:3px 8px;border-radius:7px}
.crumb a:hover{background:var(--accent-soft);color:var(--accent)}
.crumb .cur{padding:3px 8px;border-radius:7px;background:var(--accent-soft);color:var(--accent);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:220px}
.crumb .sep{opacity:.5}
.spacer{flex:1}
.search{border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:9px;padding:6px 12px;font-size:13.5px;width:150px;outline:none}
.search:focus{border-color:var(--accent)}
.btn{display:inline-flex;align-items:center;gap:6px;background:var(--accent);color:#fff;border:none;border-radius:9px;padding:7px 14px;font-size:13.5px;font-weight:600;text-decoration:none;cursor:pointer}
.btn:hover{filter:brightness(1.08)}
.btn svg{width:15px;height:15px}
.btn.ghost{background:var(--card);color:var(--text);border:1px solid var(--line)}
.btn.ghost:hover{border-color:var(--accent);color:var(--accent);filter:none}
.btn.danger{background:transparent;color:var(--danger);border:1px solid var(--line);padding:4px 10px;font-weight:500}
.btn.danger:hover{border-color:var(--danger)}
.list{display:flex;flex-direction:column;gap:8px;margin-top:16px}
.row{display:flex;align-items:center;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:13px;padding:11px 14px;color:inherit;text-decoration:none;transition:.15s}
a.row:hover,.row:hover{border-color:var(--accent);box-shadow:0 5px 16px rgba(0,0,0,.07);transform:translateY(-1px)}
a.fill{display:flex;align-items:center;gap:12px;flex:1;min-width:0;color:inherit;text-decoration:none}
a.fill:hover b{color:var(--accent)}
.ic{width:36px;height:36px;border-radius:10px;background:var(--accent-soft);color:var(--accent);display:flex;align-items:center;justify-content:center;flex:none}
.ic svg{width:20px;height:20px}
.nm{flex:1;min-width:0}
.nm b{display:block;font-weight:600;font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.meta{color:var(--muted);font-size:12.5px;display:flex;gap:14px;margin-top:1px}
.dl{flex:none}
.empty{text-align:center;color:var(--muted);padding:60px 0}
.empty .ic{margin:0 auto 12px;width:52px;height:52px}
.empty .ic svg{width:26px;height:26px}
.foot{text-align:center;color:var(--muted);font-size:12.5px;margin-top:34px}
.foot a{color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:26px;margin-top:20px;text-align:center}
.card .ic{width:64px;height:64px;margin:0 auto 14px;border-radius:18px}
.card .ic svg{width:30px;height:30px}
.card h2{font-size:18px;margin:0 0 6px;word-break:break-all}
.card .meta{justify-content:center}
.card .btn{margin-top:18px;font-size:14.5px;padding:10px 22px}
@media(max-width:640px){.meta .dt{display:none}.search{width:110px}}
/* admin */
table{width:100%;border-collapse:collapse;margin-top:12px;font-size:13.5px}
th{color:var(--muted);text-align:left;font-weight:600;padding:8px 10px;border-bottom:1px solid var(--line)}
td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top}
td.code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;word-break:break-all}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin-top:16px}
.panel h3{margin:0 0 12px;font-size:15px}
.frow{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.frow label{display:flex;flex-direction:column;gap:4px;font-size:12.5px;color:var(--muted);flex:1;min-width:170px}
input[type=text],input[type=password]{border:1px solid var(--line);background:var(--bg);color:var(--text);border-radius:9px;padding:8px 12px;font-size:14px;outline:none;width:100%}
input:focus{border-color:var(--accent)}
.msg{background:var(--accent-soft);color:var(--accent);border-radius:10px;padding:10px 14px;margin-top:12px;font-size:13.5px}
.login{max-width:360px;margin:12vh auto 0}
"""

def page(title, body, extra_head=""):
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{esc(title)}</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%93%A6%3C/text%3E%3C/svg%3E">
<style>{CSS}</style>{extra_head}</head>
<body>{body}<div class="foot">share-hub · 只读下载页</div></body></html>"""

def crumb_html(tok, link_name, rel_parts):
    parts = [f'<a href="/s/{tok}/b/">🏠 {esc(link_name)}</a>']
    acc = ""
    for i, p in enumerate(rel_parts):
        acc = acc + "/" + p if acc else p
        href = f'/s/{tok}/b/{quote(acc, safe="")}'
        if i == len(rel_parts) - 1:
            parts.append(f'<span class="sep">›</span><span class="cur">{esc(p)}</span>')
        else:
            parts.append(f'<span class="sep">›</span><a href="{href}">{esc(p)}</a>')
    return "".join(parts)

def render_browse(tok, link, rel_parts, rp):
    base = f"/s/{tok}"
    is_file = os.path.isfile(rp)
    if is_file:
        st = os.stat(rp)
        name = os.path.basename(rp)
        row = f'''<div class="row" style="cursor:default"><div class="ic">{icon_svg(name, False)}</div>
        <div class="nm"><b>{esc(name)}</b><div class="meta"><span>{fmt_size(st.st_size)}</span><span class="dt">{fmt_time(st.st_mtime)}</span></div></div>
        <a class="btn dl" href="{base}/f/"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{SVG_ICONS["download"]}</svg>下载</a></div>'''
        body = f'''<div class="wrap"><div class="top"><div class="wrap"><div class="brand"><h1><span class="dot"></span>{esc(link["name"])}</h1></div>
        {("<div class='note'>" + esc(link.get("note", "")) + "</div>") if link.get("note") else ""}
        <div class="bar"><div class="crumb">{crumb_html(tok, link["name"], rel_parts[:-1])}</div></div></div></div>
        <div class="list">{row}</div></div>'''
        return page(link["name"], body)

    dirs, files = list_entries(rp)
    rel_acc = ""
    rows = []
    for d in dirs:
        acc2 = (rel_acc + "/" + d) if rel_acc else d
        href = f"{base}/b/{quote(acc2, safe='')}"
        zip_href = f"{base}/z/{quote(acc2, safe='')}"
        rows.append(f'''<div class="row"><a class="fill" href="{href}"><div class="ic">{icon_svg(d, True)}</div>
        <div class="nm"><b>{esc(d)}</b><div class="meta"><span>文件夹</span></div></div></a>
        <a class="btn ghost dl" href="{zip_href}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{SVG_ICONS["archive"]}</svg>打包</a></div>''')
    for f in files:
        acc2 = (rel_acc + "/" + f) if rel_acc else f
        try: st = os.stat(os.path.join(rp, f))
        except OSError: continue
        href = f"{base}/f/{quote(acc2, safe='')}"
        rows.append(f'''<a class="row" data-name="{esc(f.lower())}" href="{href}"><div class="ic">{icon_svg(f, False)}</div>
        <div class="nm"><b>{esc(f)}</b><div class="meta"><span>{fmt_size(st.st_size)}</span><span class="dt">{fmt_time(st.st_mtime)}</span></div></div>
        <span class="btn ghost dl"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{SVG_ICONS["download"]}</svg>下载</span></a>''')
    if not rows:
        rows.append('<div class="empty"><div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">' + SVG_ICONS["folder"] + '</svg></div>这个文件夹是空的</div>')

    cur = rel_parts[-1] if rel_parts else link["name"]
    crumb = crumb_html(tok, link["name"], rel_parts)
    zip_href = f"{base}/z/{quote('/'.join(rel_parts), safe='')}"
    search = '<input class="search" id="q" type="text" placeholder="筛选文件…" onkeyup="flt()">'
    js = '<script>function flt(){var v=document.getElementById("q").value.toLowerCase();document.querySelectorAll("[data-name]").forEach(function(r){r.style.display=r.dataset.name.indexOf(v)>=0?"":"none"})}</script>'
    head = extra_head = ""
    body = f'''<div class="wrap"><div class="top"><div class="wrap">
    <div class="brand"><h1><span class="dot"></span>{esc(link["name"])}</h1></div>
    {("<div class='note'>" + esc(link.get("note", "")) + "</div>") if link.get("note") else ""}
    <div class="bar"><div class="crumb">{crumb}</div><div class="spacer"></div>{search}
    <a class="btn" href="{zip_href}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{SVG_ICONS["archive"]}</svg>打包下载</a></div>
    </div></div><div class="list">{''.join(rows)}</div></div>'''
    return page(cur, body, js)

def neutral_page(msg):
    body = f'''<div class="wrap" style="max-width:420px;margin-top:14vh">
    <div class="card"><div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{SVG_ICONS["package"]}</svg></div>
    <h2>share-hub</h2><div class="meta"><span>{esc(msg)}</span></div></div></div>'''
    return page("share-hub", body)

def render_pw_form(tok, link, err=""):
    body = f'''<div class="wrap" style="max-width:360px;margin-top:13vh"><div class="card">
    <h2>🔒 {esc(link["name"])}</h2><div class="meta"><span>此分享受密码保护，请输入访问密码</span></div>
    {('<div class="msg">' + esc(err) + '</div>') if err else ''}
    <form method="post" action="/s/{tok}" style="margin-top:6px">
    <input type="password" name="pw" placeholder="访问密码" style="width:100%;margin-top:14px" autofocus>
    <button class="btn" style="width:100%;justify-content:center;margin-top:12px">进入</button></form></div></div>'''
    return page(link["name"], body)

# ---------------- 管理后台 ----------------
def scan_dirs():
    out = []
    try:
        for n in sorted(os.listdir(SCAN_ROOT)):
            p = os.path.join(SCAN_ROOT, n)
            if os.path.isdir(p) and not n.startswith("."):
                out.append(p)
                try:
                    for m in sorted(os.listdir(p)):
                        q = os.path.join(p, m)
                        if os.path.isdir(q) and not m.startswith("."):
                            out.append(q)
                except PermissionError:
                    pass
    except FileNotFoundError:
        pass
    return out

def render_admin(cfg, base_url, msg="", err=""):
    pw_ok = cfg.get("_authed", False)
    if not pw_ok:
        body = f'''<div class="wrap"><div class="login card">
        <h2>⚙️ 管理登录</h2><div class="meta"><span>share-hub 分享管理后台</span></div>
        {('<div class="msg">' + esc(err) + '</div>') if err else ''}
        <form method="post" action="/admin" style="margin-top:8px">
        <input type="password" name="pw" placeholder="管理密码" style="width:100%;margin-top:14px" autofocus>
        <button class="btn" style="width:100%;justify-content:center;margin-top:12px">登录</button></form></div></div>'''
        return page("share-hub 管理", body)

    base_url = base_url or f"http://127.0.0.1:{PORT}"
    rows = []
    for tok, lk in cfg.get("links", {}).items():
        url = f"{base_url}/s/{tok}"
        pw = "🔒 有" if lk.get("pw_hash") else "—"
        rows.append(f'''<tr><td><b>{esc(lk["name"])}</b>{('<div class="meta"><span>' + esc(lk.get("note", "")) + '</span></div>') if lk.get("note") else ''}</td>
        <td class="code">{esc(lk["path"])}</td>
        <td class="code"><a href="{esc(url)}" target="_blank">{esc(url)}</a>
        <button class="btn ghost" style="padding:3px 8px;font-size:12px;margin-top:4px" onclick="cp(this)" data-u="{esc(url)}">复制</button></td>
        <td>{pw}</td>
        <td><form method="post" action="/admin" onsubmit="return confirm('确定删除分享「{esc(lk["name"])}」？链接将立即失效。')">
        <input type="hidden" name="action" value="delete"><input type="hidden" name="tok" value="{esc(tok)}">
        <button class="btn danger">删除</button></form></td></tr>''')
    table = ('<table><tr><th>名称</th><th>目录</th><th>访问链接</th><th>密码</th><th></th></tr>' + ''.join(rows) + '</table>') if rows else \
        '<div class="empty">还没有创建任何分享链接</div>'

    options = "".join(f'<option value="{esc(p)}">{esc(p)}</option>' for p in scan_dirs())
    msg_html = f'<div class="msg">{esc(msg)}</div>' if msg else ""
    body = f'''<div class="wrap">
    <div class="top"><div class="wrap"><div class="brand"><h1><span class="dot"></span>⚙️ share-hub 管理后台</h1>
    <form method="post" action="/admin"><input type="hidden" name="action" value="logout"><button class="btn ghost" style="padding:5px 12px">退出</button></form></div></div></div>
    {msg_html}{('<div class="msg">' + esc(err) + '</div>') if err else ''}
    <div class="panel"><h3>我的分享链接</h3>{table}</div>
    <div class="panel"><h3>➕ 新建分享</h3>
    <form method="post" action="/admin">
    <input type="hidden" name="action" value="create">
    <div class="frow">
    <label>名称（朋友看到的名字）<input type="text" name="name" required placeholder="例如：张三-PX4资料"></label>
    <label>目录（要分享的文件夹或单个文件）<input type="text" name="path" list="dirs" required placeholder="选择或输入完整路径"></label>
    </div>
    <datalist id="dirs">{options}</datalist>
    <div class="frow">
    <label>访问密码（可选，留空=仅凭链接访问）<input type="text" name="password" placeholder="留空则不需要密码"></label>
    <label>备注（可选，仅显示给朋友）<input type="text" name="note" placeholder="例如：PX4 教程+固件，有问题联系我"></label>
    </div>
    <button class="btn">创建分享链接</button></form></div>
    <div class="panel"><h3>🔧 设置</h3>
    <form method="post" action="/admin"><input type="hidden" name="action" value="settings">
    <div class="frow">
    <label>公网地址（⚠️ 仅显示前缀，勿改——真实公网入口由 Tailscale Funnel 决定，改错只会让复制的链接打不开）<input type="text" name="baseurl" value="{esc(cfg.get("public_base_url", ""))}" placeholder="https://….ts.net"></label>
    <label>修改管理密码（留空=不变）<input type="text" name="newpw" placeholder="新管理密码"></label>
    </div>
    <button class="btn ghost">保存设置</button></form></div>
    <script>function cp(b){{navigator.clipboard.writeText(b.dataset.u).then(function(){{b.textContent="已复制 ✓"}})}}</script>
    </div>'''
    return page("share-hub 管理", body)

# ---------------- HTTP 处理 ----------------
class Handler(BaseHTTPRequestHandler):
    server_version = "ShareHub/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print(f"[{time.strftime('%m-%d %H:%M:%S')}] {self.address_string()} {fmt % args}", flush=True)

    # ---- 基础发送 ----
    def send_html(self, body, status=200, headers=None):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or []):
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def redirect(self, loc, headers=None):
        self.send_response(303)
        self.send_header("Location", loc)
        for k, v in (headers or []):
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def read_post(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            n = 0
        if n <= 0 or n > 1_000_000:
            return {}
        body = self.rfile.read(n).decode("utf-8", "replace")
        return dict(parse_qsl(body, keep_blank_values=True))

    def cookies(self):
        out = {}
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                out[k] = v
        return out

    # ---- 路由 ----
    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_HEAD(self): self.route("GET")

    def route(self, method):
        try:
            u = urlparse(self.path)
            path = u.path
            if path == "/":
                self.send_html(neutral_page("请通过分享链接访问资料下载页"))
            elif path == "/admin":
                self.handle_admin(method)
            elif path.startswith("/s/"):
                self.handle_share(path, method)
            elif path == "/healthz":
                self.send_html("ok")
            else:
                self.send_html(neutral_page("404 页面不存在"), 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self.send_html(neutral_page(f"服务器内部错误: {esc(e)}"), 500)
            except Exception:
                pass
            import traceback; traceback.print_exc()

    # ---- 分享页 ----
    def handle_share(self, path, method):
        cfg = cfg_load()
        parts = [unquote(p) for p in path.split("/")]  # ['', 's', tok, kind, ...]
        tok = parts[2]
        links = cfg.get("links", {})
        match = None
        for k in links:
            if hashlib.sha256(k.encode()).digest() == hashlib.sha256(tok.encode()).digest() and k == tok:
                match = k
        if match is None:
            self.send_html(neutral_page("链接无效或已被删除"), 404)
            return
        link = links[match]

        # 密码保护
        if link.get("pw_hash"):
            ck = self.cookies().get(f"acc_{match}", "")
            if ck != link["pw_hash"]:
                if method == "POST" and len(parts) == 3:
                    form = self.read_post()
                    h = hashlib.sha256(form.get("pw", "").strip().encode()).hexdigest()
                    if h == link["pw_hash"]:
                        self.redirect(f"/s/{match}/b/", [("Set-Cookie", f"acc_{match}={h}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400")])
                        return
                    self.send_html(render_pw_form(match, link, "密码不正确，请重试"), 401)
                    return
                self.send_html(render_pw_form(match, link))
                return

        kind = parts[3] if len(parts) > 3 else "b"
        segs = parts[4:]
        if any(s in ("..", "\\") for s in segs):
            self.send_html(neutral_page("非法路径"), 400)
            return
        rp = resolve_link_path(link, segs)
        if rp is None or not os.path.exists(rp):
            self.send_html(neutral_page("文件不存在"), 404)
            return

        if kind == "b":
            self.send_html(render_browse(match, link, [s for s in segs if s], rp))
        elif kind == "f":
            if os.path.isdir(rp):
                self.send_html(neutral_page("这是文件夹，请使用打包下载"), 400)
                return
            self.send_file(rp, method)
        elif kind == "z":
            if os.path.isfile(rp):
                self.send_html(neutral_page("单个文件请直接点击下载"), 400)
                return
            label = segs[-1] if (segs and segs[-1]) else link["name"]
            zpath = build_zip(rp, label)
            try:
                self.send_file(zpath, method, download_name=f"{label}.zip", delete_after=True)
            finally:
                pass
        else:
            self.send_html(neutral_page("404 页面不存在"), 404)

    def send_file(self, rp, method, download_name=None, delete_after=False):
        size = os.path.getsize(rp)
        name = download_name or os.path.basename(rp)
        ctype = guess_mime(name)
        start, end = 0, size - 1
        status = 200
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip())
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else size - 1
                else:
                    start = max(0, size - int(m.group(2)))
                    end = size - 1
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                end = min(end, size - 1)
                status = 206
        length = end - start + 1
        self.send_response(status)
        ctype_disp = "application/zip" if download_name else ctype
        self.send_header("Content-Type", ctype_disp)
        self.send_header("Content-Length", str(length))
        quoted = quote(name, safe="")
        self.send_header("Content-Disposition",
                         f"attachment; filename*=UTF-8''{quoted}")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        if method == "GET" and self.command != "HEAD":
            with open(rp, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(262144, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        if delete_after:
            try:
                os.unlink(rp)
            except OSError:
                pass

    # ---- 管理 ----
    def handle_admin(self, method):
        cfg = cfg_load()
        ck = self.cookies()
        authed = ck.get("admin_sess") in cfg.get("sessions", [])

        if method == "POST":
            form = self.read_post()
            action = form.get("action", "login")
            if action == "login":
                pw = form.get("pw", "").strip()
                if pw and pw == cfg.get("admin_password"):
                    sess = secrets.token_urlsafe(16)
                    cfg.setdefault("sessions", []).append(sess)
                    cfg["sessions"] = cfg["sessions"][-10:]
                    cfg["_authed"] = True
                    cfg_save(cfg)
                    cfg.pop("_authed")
                    self.redirect("/admin", [("Set-Cookie", f"admin_sess={sess}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800")])
                else:
                    cfg["_authed"] = False
                    html_out = render_admin(cfg, cfg.get("public_base_url", ""), err="密码不正确")
                    self.send_html(html_out, 401)
                return
            if not authed:
                self.redirect("/admin")
                return
            if action == "logout":
                s = ck.get("admin_sess")
                cfg["sessions"] = [x for x in cfg.get("sessions", []) if x != s]
                cfg_save(cfg)
                self.redirect("/admin", [("Set-Cookie", "admin_sess=; Path=/; Max-Age=0")])
                return
            if action == "create":
                name = form.get("name", "").strip()[:60]
                path = form.get("path", "").strip()
                password = form.get("password", "").strip()
                note = form.get("note", "").strip()[:120]
                rp = os.path.realpath(path) if path else ""
                if not name or not rp or not os.path.exists(rp):
                    cfg["_authed"] = True
                    self.send_html(render_admin(cfg, cfg.get("public_base_url", ""), err="名称或路径无效（路径必须真实存在）"))
                    return
                tok = secrets.token_urlsafe(9)
                while tok in cfg.get("links", {}):
                    tok = secrets.token_urlsafe(9)
                cfg.setdefault("links", {})[tok] = {
                    "name": name, "path": rp, "note": note,
                    "pw_hash": hashlib.sha256(password.encode()).hexdigest() if password else "",
                    "created": time.strftime("%Y-%m-%d"),
                }
                cfg_save(cfg)
                new_url = f"{cfg.get('public_base_url') or f'http://127.0.0.1:{PORT}'}/s/{tok}"
                cfg["_authed"] = True
                self.send_html(render_admin(cfg, cfg.get("public_base_url", ""), msg=f"✅ 已创建「{name}」，链接：{new_url}"))
                return
            if action == "delete":
                tok = form.get("tok", "")
                if tok in cfg.get("links", {}):
                    del cfg["links"][tok]
                    cfg_save(cfg)
                self.redirect("/admin")
                return
            if action == "settings":
                if form.get("baseurl", "").strip():
                    cfg["public_base_url"] = form["baseurl"].strip().rstrip("/")
                if form.get("newpw", "").strip():
                    cfg["admin_password"] = form["newpw"].strip()
                    cfg["sessions"] = []
                    cfg_save(cfg)
                    self.redirect("/admin", [("Set-Cookie", "admin_sess=; Path=/; Max-Age=0")])
                    return
                cfg_save(cfg)
                self.redirect("/admin")
                return

        # GET
        cfg["_authed"] = authed
        self.send_html(render_admin(cfg, cfg.get("public_base_url", "")))

def main():
    ensure_config()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.daemon_threads = True
    print(f"share-hub listening on http://{HOST}:{PORT}, serving links from {CONFIG_FILE}", flush=True)
    srv.serve_forever()

if __name__ == "__main__":
    main()
