#!/usr/bin/env python3
"""Copy Nextcloud Website/theme media into the public site."""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(os.environ.get("BLOG_WEBROOT", os.environ.get("THEME_WEBROOT", "/var/www/santabayanian")))
NC_DEFAULT = Path("/mnt/data/ncdata/musicuser/files/Website/theme")
BLOG_NC = Path(os.environ.get("BLOG_DIR", "/mnt/data/ncdata/musicuser/files/Website/blog"))
ORIGIN = os.environ.get("BLOG_ORIGIN", "https://santabayanian.com")
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic", ".gif"}
ALPHA_EXT = {".png", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}
SKIP_DIRS = {"masters", "master", "raw", "drafts", "export"}
RESERVED_STILL = {"mascot": "mascot", "hero": "mascot", "poster": "mascot", "r5": "mascot", "keith": "about", "about": "about", "about-photo": "about", "og": "og"}
RESERVED_VIDEO = {"mascot-mist": "mascot-mist.mp4", "mist": "mascot-mist.mp4", "hero": "mascot-mist.mp4", "mascot-roots": "mascot-roots.mp4", "roots": "mascot-roots.mp4", "mascot-fire": "mascot-fire.mp4", "fire": "mascot-fire.mp4", "demon": "mascot-fire.mp4"}
RECENT_START = "<!-- rm:recent-start -->"
RECENT_END = "<!-- rm:recent-end -->"
IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'])', re.I)

def log(msg):
    print(msg, flush=True)

def which(*names):
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None

def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "media"

def theme_dir():
    env = os.environ.get("THEME_DIR", "").strip()
    if env:
        return Path(env)
    return NC_DEFAULT if NC_DEFAULT.is_dir() else ROOT / "theme-src"

def dest_site():
    return ROOT / "images" / "site"

def dest_gallery():
    return dest_site() / "mascot"

def keep_alpha(src):
    return src.suffix.lower() in ALPHA_EXT

def out_ext(src):
    return ".png" if keep_alpha(src) else ".jpg"

def run(cmd):
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (OSError, subprocess.CalledProcessError) as exc:
        log("  cmd failed: %s: %s" % (cmd[0], exc))
        return False

def newer(src, dst):
    return (not dst.exists()) or src.stat().st_mtime > dst.stat().st_mtime + 0.5

def role_video(stem):
    s = slugify(stem)
    if s in RESERVED_VIDEO:
        return RESERVED_VIDEO[s]
    if any(k in s for k in ("mist", "water", "cape", "marsh")):
        return "mascot-mist.mp4"
    if any(k in s for k in ("root", "tentacle")):
        return "mascot-roots.mp4"
    if any(k in s for k in ("fire", "demon", "wing", "ember")):
        return "mascot-fire.mp4"
    return None

def role_still(stem, src):
    s = slugify(stem)
    base = RESERVED_STILL.get(s)
    if not base:
        if "about" in s or s in {"keith", "portrait"}:
            base = "about"
        elif s in {"og", "opengraph", "share"}:
            base = "og"
        elif s in {"mascot", "hero", "poster", "r5"}:
            base = "mascot"
    if not base:
        return None
    return base + out_ext(src)

def iter_media(folder):
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.startswith(".") or name.startswith("_") or name.endswith(".part"):
                continue
            path = Path(dirpath) / name
            if path.suffix.lower() in IMAGE_EXT or path.suffix.lower() in VIDEO_EXT:
                yield path

def optimize_image(src, dst, max_w=1800):
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst = dst.with_suffix(out_ext(src))
    if keep_alpha(src):
        if (not dst.exists()) or newer(src, dst):
            shutil.copy2(src, dst)
            os.chmod(dst, 0o644)
            log("png    %s -> %s (alpha preserved)" % (src.name, dst))
            return True
        return False
    if not newer(src, dst) and dst.exists():
        return False
    ffmpeg = which("ffmpeg")
    if ffmpeg and run([ffmpeg, "-y", "-i", str(src), "-vf", "scale='min(%d,iw)':-2" % max_w, "-q:v", "3", "-update", "1", "-frames:v", "1", str(dst)]):
        os.chmod(dst, 0o644)
        return True
    shutil.copy2(src, dst)
    os.chmod(dst, 0o644)
    return True

def optimize_video(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst = dst.with_suffix(".mp4")
    if not newer(src, dst) and dst.exists() and dst.stat().st_size > 1000:
        return False
    ffmpeg = which("ffmpeg")
    if ffmpeg and run([ffmpeg, "-y", "-i", str(src), "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "28", "-preset", "fast", "-an", "-movflags", "+faststart", str(dst)]):
        os.chmod(dst, 0o644)
        return True
    shutil.copy2(src, dst)
    os.chmod(dst, 0o644)
    return True

def write_json(path, data):
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)

def ensure_link(html, tag):
    if tag in html:
        return html
    if tag.startswith("<link") and "</head>" in html:
        return html.replace("</head>", "  %s\n</head>" % tag, 1)
    if tag.startswith("<script") and "</body>" in html:
        return html.replace("</body>", "%s\n</body>" % tag, 1)
    return html

def strip_player_copy(html):
    html = re.sub(r"<!-- theme:mascot-start -->[\s\S]*?<!-- theme:mascot-end -->\s*", "", html)
    html = re.sub(r"<section[^>]*mascot-band[^>]*>[\s\S]*?</section>\s*", "", html, flags=re.I)
    html = re.sub(
        r"<(section|article|div)(\s[^>]*)?>[\s\S]{0,3000}?<p class=\"kicker\">\s*The player\s*</p>[\s\S]*?</\1>\s*",
        "",
        html,
        flags=re.I,
    )
    html = re.sub(
        r"<(section|article|div)(\s[^>]*)?>[\s\S]{0,4000}?(?:A mascot from the same woods|same woods as the music|The story)[\s\S]*?</\1>\s*",
        "",
        html,
        flags=re.I,
    )
    html = html.replace("The player in the trees is the face of the work. ", "")
    html = html.replace("The player in the trees is the face of the work.", "")
    return html

def album_title(html, slug):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return slug.replace("-", " ").title()

def published_releases():
    albums = ROOT / "albums"
    items = []
    if not albums.is_dir():
        return items
    for d in albums.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        page = d / "index.html"
        if not page.is_file():
            continue
        cover = None
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            c = ROOT / "images" / "albums" / (d.name + ext)
            if c.exists():
                cover = "/images/albums/" + c.name
                break
        if not cover:
            continue
        html = page.read_text(encoding="utf-8", errors="ignore")
        items.append({"slug": d.name, "title": album_title(html, d.name), "cover": cover, "mtime": page.stat().st_mtime})
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items

def recent_block(items, limit=3):
    cards = []
    for it in items[:limit]:
        cards.append(
            '    <article class="release-card">\n'
            '      <a href="/albums/%s/">\n'
            '        <img src="%s" alt="%s">\n'
            '        <h3>%s</h3>\n'
            '      </a>\n'
            '    </article>\n' % (it["slug"], it["cover"], it["title"], it["title"])
        )
    inner = "".join(cards) if cards else "    <p class=\"lede\">New recordings will appear here when a release is published.</p>\n"
    return RECENT_START + "\n" + inner + RECENT_END

def sync_home_recent():
    home = ROOT / "index.html"
    if not home.is_file():
        return
    items = published_releases()
    log("published albums: %s" % (", ".join(i["slug"] for i in items) or "(none)"))
    block = recent_block(items)
    html = strip_player_copy(home.read_text(encoding="utf-8"))
    if RECENT_START in html and RECENT_END in html:
        html = re.sub(re.escape(RECENT_START) + r"[\s\S]*?" + re.escape(RECENT_END), block, html, count=1)
    else:
        section = (
            '<section class="wrap section" id="recent-releases">\n'
            '  <div class="section-head"><p class="kicker">Recordings</p><h2>Recent releases</h2></div>\n'
            '  <div class="release-grid">\n%s\n  </div>\n'
            '</section>\n' % block
        )
        html = re.sub(
            r'<section class="wrap section">[\s\S]*?Signatures[\s\S]*?</section>',
            section,
            html,
            count=1,
            flags=re.I,
        )
        if 'id="recent-releases"' not in html and "</main>" in html:
            html = html.replace("</main>", section + "</main>", 1)
    tmp = home.with_name("index.html.tmp")
    tmp.write_text(html, encoding="utf-8")
    os.chmod(tmp, 0o644)
    os.replace(tmp, home)
    log("synced home recent releases; stripped The Player copy")

def index_nc_blog_images():
    by_name, by_rel = {}, {}
    if not BLOG_NC.is_dir():
        log("blog nc dir missing: %s" % BLOG_NC)
        return by_name, by_rel
    for dirpath, dirnames, filenames in os.walk(BLOG_NC):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") or d.startswith(".attachments")]
        for name in filenames:
            if name.startswith(".") or name.endswith(".part") or name.endswith(".md"):
                continue
            path = Path(dirpath) / name
            if path.suffix.lower() not in IMAGE_EXT:
                continue
            by_name[name.lower()] = path
            try:
                rel = path.relative_to(BLOG_NC).as_posix().lower()
            except ValueError:
                rel = name.lower()
            by_rel[rel] = path
            by_rel[name.lower()] = path
            if ".attachments" in rel:
                by_rel["." + rel.split(".", 1)[-1] if False else rel] = path
                by_rel[rel.split("/")[-1]] = path
    return by_name, by_rel

def public_image_name(src):
    stem = slugify(src.stem)
    ext = src.suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    if src.suffix.lower() in ALPHA_EXT:
        ext = src.suffix.lower()
    return stem + ext

def copy_blog_image(src, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = public_image_name(src)
    dst = dest_dir / name
    if keep_alpha(src):
        if newer(src, dst) or not dst.exists():
            shutil.copy2(src, dst)
            os.chmod(dst, 0o644)
    else:
        if newer(src, dst) or not dst.exists():
            shutil.copy2(src, dst)
            os.chmod(dst, 0o644)
    return "/images/blog/" + name

def rewrite_blog_html(html, by_name, by_rel, dest_dir):
    def repl(match):
        src = match.group(2).strip()
        if src.startswith("data:") or src.startswith("http://") or src.startswith("https://"):
            return match.group(0)
        raw = src.split("?", 1)[0].lstrip("./")
        key = raw.lower()
        name = Path(raw).name.lower()
        found = by_rel.get(key) or by_name.get(name)
        if found is None and "attachments" in key:
            found = by_name.get(name)
        if found is None and src.startswith("/images/blog/"):
            disk = ROOT / src.lstrip("/")
            if disk.exists():
                return match.group(0)
            found = by_name.get(Path(src).name.lower())
        if found is None:
            log("blog img missing: %s" % src)
            return match.group(0)
        url = copy_blog_image(found, dest_dir)
        log("blog img %s -> %s" % (src, url))
        return match.group(1) + url + match.group(3)
    return IMG_SRC_RE.sub(repl, html)

def fix_blog_media():
    dest = ROOT / "images" / "blog"
    dest.mkdir(parents=True, exist_ok=True)
    by_name, by_rel = index_nc_blog_images()
    log("blog nc images: %d" % len(by_name))
    for src in by_name.values():
        copy_blog_image(src, dest)
    blog_root = ROOT / "blog"
    if not blog_root.is_dir():
        return
    for page in [blog_root / "index.html"] + list(blog_root.glob("*/index.html")):
        if not page.is_file():
            continue
        html = page.read_text(encoding="utf-8")
        new = rewrite_blog_html(html, by_name, by_rel, dest)
        if new != html:
            tmp = page.with_name(page.name + ".tmp")
            tmp.write_text(new, encoding="utf-8")
            os.chmod(tmp, 0o644)
            os.replace(tmp, page)
            log("rewrote images in %s" % page)

def patch_html(index_path, theme):
    if not index_path.is_file():
        return
    rel = index_path.relative_to(ROOT).as_posix()
    is_home = rel == "index.html"
    is_blog_post = rel.startswith("blog/") and rel != "blog/index.html"
    if is_blog_post:
        return
    html = index_path.read_text(encoding="utf-8")
    original = html
    html = ensure_link(html, '<link rel="stylesheet" href="/css/theme.css">')
    html = ensure_link(html, '<script src="/js/theme.js" defer></script>')
    if is_home:
        html = strip_player_copy(html)
        poster = theme.get("poster") or ""
        if poster:
            html = html.replace("/images/site/mascot.jpg", poster)
    if html == original:
        return
    tmp = index_path.with_name(index_path.name + ".tmp")
    try:
        tmp.write_text(html, encoding="utf-8")
        os.chmod(tmp, 0o644)
        os.replace(tmp, index_path)
    except OSError:
        index_path.write_text(html, encoding="utf-8")
        os.chmod(index_path, 0o644)
    log("patched %s" % index_path)

def patch_all_html(theme):
    skip_top = {"albums", "audio", "images"}
    for path in ROOT.rglob("index.html"):
        parts = path.relative_to(ROOT).parts
        if parts and parts[0] in skip_top:
            continue
        try:
            patch_html(path, theme)
        except OSError as exc:
            log("skip patch %s: %s" % (path, exc))

def main():
    debounce = float(os.environ.get("THEME_DEBOUNCE_SEC", os.environ.get("BLOG_DEBOUNCE_SEC", "0")) or 0)
    if debounce > 0:
        time.sleep(debounce)
    folder = theme_dir()
    site = dest_site()
    gallery = dest_gallery()
    log("theme   %s" % folder)
    log("webroot %s" % ROOT)
    if not folder.is_dir():
        log("ERROR theme dir missing: %s" % folder)
        return 1
    if not os.access(folder, os.R_OK):
        log("ERROR cannot read theme dir as this user: %s" % folder)
        return 1
    site.mkdir(parents=True, exist_ok=True)
    gallery.mkdir(parents=True, exist_ok=True)
    stills, clips, assigned = [], [], {}
    first_still = first_video = None
    copied = 0
    files = sorted(iter_media(folder), key=lambda p: p.name.lower())
    if not files:
        log("no image/video files in theme dir yet")
    for src in files:
        ext = src.suffix.lower()
        stem = src.stem
        name = slugify(stem)
        if ext in IMAGE_EXT:
            if first_still is None:
                first_still = src
            gdest = gallery / (name + out_ext(src))
            if optimize_image(src, gdest):
                copied += 1
            stills.append({"src": "/images/site/mascot/%s" % gdest.name, "name": stem})
            reserved = role_still(stem, src)
            if reserved and reserved not in assigned:
                if optimize_image(src, site / reserved, max_w=1200 if reserved.startswith("og.") else 1800):
                    copied += 1
                assigned[reserved] = "/images/site/%s" % reserved
                log("role   %s" % reserved)
        else:
            if first_video is None:
                first_video = src
            gdest = gallery / (name + ".mp4")
            if optimize_video(src, gdest):
                copied += 1
            clips.append({"src": "/images/site/mascot/%s" % gdest.name, "name": stem})
            reserved = role_video(stem)
            if reserved and reserved not in assigned:
                if optimize_video(src, site / reserved):
                    copied += 1
                assigned[reserved] = "/images/site/%s" % reserved
                log("role   %s" % reserved)
    if not any(k.startswith("mascot.") for k in assigned) and first_still is not None:
        dest = site / ("mascot" + out_ext(first_still))
        optimize_image(first_still, dest)
        assigned[dest.name] = "/images/site/%s" % dest.name
        log("role   %s (first still)" % dest.name)
    poster = assigned.get("mascot.png") or assigned.get("mascot.webp") or assigned.get("mascot.jpg")
    if poster and poster.endswith(".png"):
        stale = site / "mascot.jpg"
        if stale.exists():
            stale.unlink()
            log("removed flattened mascot.jpg")
    theme = {
        "poster": poster or "/images/site/mascot.png",
        "heroVideo": assigned.get("mascot-mist.mp4"),
        "rootsVideo": assigned.get("mascot-roots.mp4"),
        "fireVideo": assigned.get("mascot-fire.mp4"),
        "about": assigned.get("about.png") or assigned.get("about.jpg"),
        "og": assigned.get("og.png") or assigned.get("og.jpg"),
        "stills": stills,
        "clips": clips,
        "origin": ORIGIN,
    }
    write_json(site / "theme.json", theme)
    restorecon = which("restorecon")
    if restorecon:
        subprocess.run([restorecon, "-R", str(site)], check=False, capture_output=True)
        subprocess.run([restorecon, "-R", str(ROOT / "images" / "blog")], check=False, capture_output=True)
    patch_all_html(theme)
    try:
        sync_home_recent()
    except OSError as exc:
        log("home recent sync skipped: %s" % exc)
    try:
        fix_blog_media()
    except OSError as exc:
        log("blog media fix skipped: %s" % exc)
    log("wrote theme.json, %d stills, %d clips, %d files processed" % (len(stills), len(clips), copied))
    return 0

if __name__ == "__main__":
    sys.exit(main())
