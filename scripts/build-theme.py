#!/usr/bin/env python3
"""Copy Nextcloud Website/theme media into the public site.

PNG/WebP/GIF keep their alpha. JPEG stills stay JPEG.
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(os.environ.get("BLOG_WEBROOT", os.environ.get("THEME_WEBROOT", "/var/www/santabayanian")))
NC_DEFAULT = Path("/mnt/data/ncdata/musicuser/files/Website/theme")
ORIGIN = os.environ.get("BLOG_ORIGIN", "https://santabayanian.com")
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic", ".gif"}
ALPHA_EXT = {".png", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}
SKIP_DIRS = {"masters", "master", "raw", "drafts", "export"}
RESERVED_STILL = {"mascot": "mascot", "hero": "mascot", "poster": "mascot", "r5": "mascot", "about": "about", "about-photo": "about", "og": "og"}
RESERVED_VIDEO = {"mascot-mist": "mascot-mist.mp4", "mist": "mascot-mist.mp4", "hero": "mascot-mist.mp4", "mascot-roots": "mascot-roots.mp4", "roots": "mascot-roots.mp4", "mascot-fire": "mascot-fire.mp4", "fire": "mascot-fire.mp4", "demon": "mascot-fire.mp4"}
GALLERY_HTML = "<!-- theme:mascot-start -->\n<section class=\"wrap section mascot-band\" data-mascot-reel>\n  <div class=\"section-head\"><div><p class=\"kicker\">The player</p><h2>Santa Bayanian</h2></div></div>\n  <div class=\"mascot-reel\" data-mascot-grid></div>\n</section>\n<!-- theme:mascot-end -->\n"

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
        if "about" in s:
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
    if not newer(src, dst) and dst.exists():
        return False
    ffmpeg = which("ffmpeg")
    if keep_alpha(src):
        if ffmpeg and run([ffmpeg, "-y", "-i", str(src), "-vf", "scale='min(%d,iw)':-2" % max_w, "-pix_fmt", "rgba", str(dst)]):
            os.chmod(dst, 0o644)
            return True
        shutil.copy2(src, dst)
        os.chmod(dst, 0o644)
        return True
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

def patch_index(index_path, theme):
    if not index_path.is_file():
        log("no index.html at %s — skip homepage patch" % index_path)
        return
    html = index_path.read_text(encoding="utf-8")
    original = html
    html = ensure_link(html, '<link rel="stylesheet" href="/css/theme.css">')
    html = ensure_link(html, '<script src="/js/theme.js" defer></script>')
    poster = theme.get("poster") or ""
    if poster:
        html = html.replace("/images/site/mascot.jpg", poster)
        html = html.replace("/images/site/mascot.png", poster)
    if "<!-- theme:mascot-start -->" not in html:
        if "<!-- rm:recent-start -->" in html:
            html = html.replace("<!-- rm:recent-start -->", GALLERY_HTML + "\n<!-- rm:recent-start -->", 1)
        elif '<section class="wrap section">' in html:
            html = html.replace('<section class="wrap section">', GALLERY_HTML + '\n<section class="wrap section">', 1)
    if html == original:
        log("homepage already current")
        return
    tmp = index_path.with_name("index.html.tmp")
    try:
        tmp.write_text(html, encoding="utf-8")
        os.chmod(tmp, 0o644)
        os.replace(tmp, index_path)
    except OSError:
        try:
            index_path.unlink()
        except OSError:
            pass
        index_path.write_text(html, encoding="utf-8")
        os.chmod(index_path, 0o644)
    log("patched %s" % index_path)

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
                log("still  %s -> /images/site/mascot/%s" % (src.name, gdest.name))
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
                log("clip   %s -> /images/site/mascot/%s" % (src.name, gdest.name))
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
    if "mascot-mist.mp4" not in assigned and first_video is not None:
        optimize_video(first_video, site / "mascot-mist.mp4")
        assigned["mascot-mist.mp4"] = "/images/site/mascot-mist.mp4"
        log("role   mascot-mist.mp4 (first clip)")
    poster = assigned.get("mascot.png") or assigned.get("mascot.webp") or assigned.get("mascot.jpg") or "/images/site/mascot.png"
    if poster.endswith(".png"):
        stale = site / "mascot.jpg"
        if stale.exists():
            stale.unlink()
            log("removed flattened mascot.jpg")
    theme = {
        "poster": poster,
        "heroVideo": assigned.get("mascot-mist.mp4", "/images/site/mascot-mist.mp4"),
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
    patch_index(ROOT / "index.html", theme)
    log("wrote theme.json, %d stills, %d clips, %d files processed" % (len(stills), len(clips), copied))
    return 0

if __name__ == "__main__":
    sys.exit(main())
