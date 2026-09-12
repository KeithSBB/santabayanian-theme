#!/usr/bin/env python3
"""Homepage journal teaser, blog listing cards, videos, about from Nextcloud."""
from __future__ import annotations
import os, re, shutil, sys
from html import escape
from pathlib import Path

IMG_SRC_RE = re.compile(r'<img\b[^>]*?\bsrc=["\']([^"\']+)["\']', re.I)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TIME_RE = re.compile(r'<time[^>]*datetime=["\']([^"\']+)["\']', re.I)
YT_RE = re.compile(r"(?:youtu\.be/|v=|embed/|shorts/)([A-Za-z0-9_-]{11})")
JOURNAL_START = "<!-- journal:start -->"
JOURNAL_END = "<!-- journal:end -->"
HOME_VIDEO_START = "<!-- home-video:start -->"
HOME_VIDEO_END = "<!-- home-video:end -->"
VIDEOS_START = "<!-- videos:start -->"
VIDEOS_END = "<!-- videos:end -->"
ABOUT_START = "<!-- about:start -->"
ABOUT_END = "<!-- about:end -->"
VIDEOS_NC = Path(os.environ.get("VIDEOS_DIR", "/mnt/data/ncdata/musicuser/files/Website/videos"))
WEBSITE_NC = Path(os.environ.get("WEBSITE_DIR", "/mnt/data/ncdata/musicuser/files/Website"))
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
STOCK_COPY = [
    "Performance films and song videos. Pieces with a YouTube ID play here; the rest open a search until the official upload is wired in.",
    "Notes on music, physics, and the tools around the work. New categories appear when you add them to a post.",
]

def _title(html, fallback):
    m = H1_RE.search(html)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip() or fallback
    return fallback.replace("-", " ").title()

def _first_img(html):
    for m in IMG_SRC_RE.finditer(html):
        src = m.group(1).strip()
        if src.startswith("data:"):
            continue
        if "mascot" in src and "/images/site/" in src:
            continue
        return src
    return None

def _abs_img(src, slug, root):
    if not src:
        return None
    if src.startswith("http://") or src.startswith("https://") or src.startswith("/"):
        if src.startswith("/") and not (root / src.lstrip("/")).exists():
            name = Path(src).name
            for cand in (root / "images" / "blog" / name, root / "blog" / slug / name):
                if cand.exists():
                    return "/" + cand.relative_to(root).as_posix()
        return src
    for cand in (root / "images" / "blog" / Path(src).name, root / "blog" / slug / Path(src).name):
        if cand.exists():
            return "/" + cand.relative_to(root).as_posix()
    return "/blog/%s/%s" % (slug, src.lstrip("./"))

def write_html(path, html):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(html, encoding="utf-8")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)

def replace_markers(html, start, end, inner):
    block = start + "\n" + inner + end
    if start in html and end in html:
        return re.sub(re.escape(start) + r"[\s\S]*?" + re.escape(end), block, html, count=1)
    return html

def strip_stock_copy(html):
    html = html.replace("hello@santabayanian.com", "keith@santabayanian.com")
    for phrase in STOCK_COPY:
        html = html.replace(phrase, "")
    html = re.sub(r'<p class="lede">\s*</p>\s*', "", html)
    html = re.sub(r'<p>\s*</p>\s*', "", html)
    return html

def strip_file(path, log):
    if not path.is_file():
        return
    html = path.read_text(encoding="utf-8")
    new = strip_stock_copy(html)
    if new != html:
        write_html(path, new)
        log("stripped stock copy in %s" % path)

def iter_posts(root):
    blog = root / "blog"
    if not blog.is_dir():
        return []
    posts = []
    for d in blog.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        page = d / "index.html"
        if not page.is_file():
            continue
        html = page.read_text(encoding="utf-8", errors="ignore")
        tm = TIME_RE.search(html)
        posts.append({
            "slug": d.name,
            "title": _title(html, d.name),
            "img": _abs_img(_first_img(html), d.name, root),
            "href": "/blog/%s/" % d.name,
            "sort": (tm.group(1) if tm else "") + str(page.stat().st_mtime),
        })
    posts.sort(key=lambda p: p["sort"], reverse=True)
    return posts

def fix_blog_index_cards(root, log):
    index = root / "blog" / "index.html"
    if not index.is_file():
        return
    posts = {p["slug"]: p for p in iter_posts(root)}
    original = index.read_text(encoding="utf-8")
    html = strip_stock_copy(original)

    def fix_article(match):
        block = match.group(0)
        href = re.search(r'href=["\'](/blog/([^/"\']+)/?)["\']', block)
        if not href:
            return block
        slug = href.group(2)
        post = posts.get(slug)
        if not post or not post["img"]:
            return block
        img = post["img"]
        if re.search(r"<img\b", block, re.I):
            block = re.sub(
                r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'])',
                r"\1%s\3" % img,
                block,
                count=1,
                flags=re.I,
            )
        else:
            block = re.sub(
                r"(<a\b[^>]*>)",
                r'\1<img src="%s" alt="%s">' % (img, escape(post["title"])),
                block,
                count=1,
                flags=re.I,
            )
        return block

    html = re.sub(r"<article\b[\s\S]*?</article>", fix_article, html, flags=re.I)
    for slug, post in posts.items():
        if not post["img"]:
            continue
        html = re.sub(
            r'(href=["\']/blog/%s/?["\'][\s\S]{0,800}<img\b[^>]*\bsrc=["\'])([^"\']+)' % re.escape(slug),
            r"\1" + post["img"],
            html,
            count=1,
            flags=re.I,
        )
    if html != original:
        write_html(index, html)
        log("updated blog listing")

def parse_md(path):
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text.strip()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip().strip('"').strip("'")
            body = parts[2].strip()
    return meta, body

def inline_md(s):
    slots = []
    def save(html):
        slots.append(html)
        return "\x00%d\x00" % (len(slots) - 1)
    s = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: save('<img src="%s" alt="%s">' % (m.group(2).strip(), escape(m.group(1)))),
        s,
    )
    s = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: save('<a href="%s">%s</a>' % (m.group(2).strip(), escape(m.group(1)))),
        s,
    )
    s = escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    for i, html in enumerate(slots):
        s = s.replace("\x00%d\x00" % i, html)
    return s

def simple_md(text):
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return ""
    chunks = re.split(r"\n\s*\n", text)
    out = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.split("\n")
        if all(re.match(r"^[-*]\s+", ln) for ln in lines):
            items = "".join("<li>%s</li>" % inline_md(re.sub(r"^[-*]\s+", "", ln)) for ln in lines)
            out.append("<ul>%s</ul>" % items)
            continue
        if all(re.match(r"^\d+\.\s+", ln) for ln in lines):
            items = "".join("<li>%s</li>" % inline_md(re.sub(r"^\d+\.\s+", "", ln)) for ln in lines)
            out.append("<ol>%s</ol>" % items)
            continue
        hm = re.match(r"^(#{1,3})\s+(.*)$", chunk)
        if hm and "\n" not in chunk:
            n = len(hm.group(1))
            out.append("<h%d>%s</h%d>" % (n, inline_md(hm.group(2)), n))
            continue
        out.append("<p>%s</p>" % inline_md(" ".join(ln.strip() for ln in lines)))
    return "\n".join(out)

def md_to_html(text):
    try:
        import markdown as mdlib
        return mdlib.markdown(text, extensions=["extra", "sane_lists", "nl2br"])
    except Exception:
        return simple_md(text)

def find_about_md():
    env = os.environ.get("ABOUT_MD", "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p
    for cand in (
        WEBSITE_NC / "about.md",
        WEBSITE_NC / "about" / "about.md",
        WEBSITE_NC / "about" / "index.md",
    ):
        if cand.is_file():
            return cand
    return None

def public_image_name(src):
    stem = re.sub(r"[^a-z0-9]+", "-", src.stem.lower()).strip("-") or "image"
    ext = src.suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    return stem + ext

def index_about_images(md_path):
    by_name = {}
    roots = {md_path.parent}
    about_dir = WEBSITE_NC / "about"
    if about_dir.is_dir():
        roots.add(about_dir)
    for folder in roots:
        for dirpath, dirnames, filenames in os.walk(folder):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") or d.startswith(".attachments")]
            for name in filenames:
                path = Path(dirpath) / name
                if path.suffix.lower() in IMAGE_EXT:
                    by_name[name.lower()] = path
                    try:
                        rel = path.relative_to(folder).as_posix().lower()
                        by_name[rel] = path
                    except ValueError:
                        pass
    return by_name

def copy_about_image(src, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = public_image_name(src)
    dst = dest_dir / name
    if (not dst.exists()) or src.stat().st_mtime > dst.stat().st_mtime + 0.5:
        shutil.copy2(src, dst)
        os.chmod(dst, 0o644)
    return "/images/about/" + name

def rewrite_about_images(html, by_name, dest_dir, log):
    def repl(match):
        src = match.group(1).strip()
        if src.startswith("data:") or src.startswith("http://") or src.startswith("https://"):
            return match.group(0)
        raw = src.split("?", 1)[0].lstrip("./")
        found = by_name.get(raw.lower()) or by_name.get(Path(raw).name.lower())
        if found is None:
            log("about img missing: %s" % src)
            return match.group(0)
        url = copy_about_image(found, dest_dir)
        log("about img %s -> %s" % (src, url))
        return match.group(0).replace(src, url, 1)
    return IMG_SRC_RE.sub(repl, html)

def sync_about(root, log):
    md_path = find_about_md()
    dest = root / "about" / "index.html"
    if not dest.is_file():
        log("about page missing: %s" % dest)
        return
    if md_path is None:
        log("about.md not found under %s — leave existing About copy" % WEBSITE_NC)
        return
    log("about md %s" % md_path)
    meta, body = parse_md(md_path)
    dest_dir = root / "images" / "about"
    dest_dir.mkdir(parents=True, exist_ok=True)
    by_name = index_about_images(md_path)
    for src in list(by_name.values()):
        copy_about_image(src, dest_dir)
    html_body = md_to_html(body)
    html_body = rewrite_about_images(html_body, by_name, dest_dir, log)
    portrait = meta.get("portrait") or meta.get("image") or meta.get("cover") or ""
    if portrait:
        key = Path(portrait).name.lower()
        found = by_name.get(portrait.lower().lstrip("./")) or by_name.get(key)
        if found:
            url = copy_about_image(found, dest_dir)
            html_body = '<p class="about-photo"><img src="%s" alt=""></p>\n' % url + html_body
            log("about portrait %s" % url)
    page = dest.read_text(encoding="utf-8")
    if ABOUT_START not in page or ABOUT_END not in page:
        inner = (
            '<section class="wrap section about-page">\n'
            "  <h1>%s</h1>\n"
            '  <div class="about-body">\n%s\n%s\n%s\n  </div>\n'
            "</section>\n" % (escape(meta.get("title") or "About"), ABOUT_START, html_body, ABOUT_END)
        )
        if "</main>" in page:
            page = re.sub(r"<main\b[^>]*>[\s\S]*?</main>", "<main id=\"content\">\n" + inner + "</main>", page, count=1, flags=re.I)
        else:
            page += inner
    else:
        page = replace_markers(page, ABOUT_START, ABOUT_END, html_body + "\n")
        if meta.get("title") and "<title>" in page:
            page = re.sub(r"<title>[^<]*</title>", "<title>%s \u2014 Santa Bayanian</title>" % escape(meta["title"]), page, count=1)
    write_html(dest, page)
    log("wrote about from markdown")

def youtube_id(value):
    if not value:
        return None
    value = value.strip()
    m = YT_RE.search(value)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    return None

def load_videos():
    items = []
    if not VIDEOS_NC.is_dir():
        return items
    for path in sorted(VIDEOS_NC.rglob("*.md")):
        if path.name.startswith("_") or path.name.startswith("."):
            continue
        meta, body = parse_md(path)
        if str(meta.get("draft", "")).lower() in {"1", "true", "yes"}:
            continue
        first = body.splitlines()[0] if body else ""
        yid = youtube_id(meta.get("youtube") or meta.get("url") or meta.get("id") or first)
        if not yid:
            continue
        title = meta.get("title") or path.stem.replace("-", " ").title()
        rest = body
        if body and youtube_id(first):
            rest = "\n".join(body.splitlines()[1:]).strip()
        items.append({"id": yid, "title": title, "body": rest, "date": meta.get("date") or "", "mtime": path.stat().st_mtime})
    items.sort(key=lambda v: (v["date"], v["mtime"]), reverse=True)
    return items

def videos_inner(items):
    if not items:
        return VIDEOS_START + "\n" + VIDEOS_END
    cards = []
    for it in items:
        desc = ("<p>%s</p>\n" % escape(it["body"])) if it["body"] else ""
        cards.append(
            '<article class="video-card">\n'
            '  <div class="video-embed">\n'
            '    <iframe src="https://www.youtube-nocookie.com/embed/%s" title="%s" allow="encrypted-media; picture-in-picture" allowfullscreen loading="lazy"></iframe>\n'
            '  </div>\n'
            '  <h2>%s</h2>\n%s'
            '</article>\n' % (it["id"], escape(it["title"]), escape(it["title"]), desc)
        )
    return VIDEOS_START + "\n<div class=\"video-grid\">\n" + "".join(cards) + "</div>\n" + VIDEOS_END

def replace_main(html, main_html):
    if re.search(r"<main\b", html, re.I) and "</main>" in html.lower():
        return re.sub(r"<main\b[^>]*>[\s\S]*?</main>", main_html, html, count=1, flags=re.I)
    return html

def chrome_from(root):
    for rel in ("about/index.html", "contact/index.html", "blog/index.html", "index.html"):
        path = root / rel
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore")
    return ""

def sync_home(root, log):
    home = root / "index.html"
    if not home.is_file():
        return
    html = home.read_text(encoding="utf-8")
    videos = load_videos()
    if videos:
        it = videos[0]
        video_inner = (
            '<article class="video-card">\n'
            '  <div class="video-embed">\n'
            '    <iframe src="https://www.youtube-nocookie.com/embed/%s" title="%s" allow="encrypted-media; picture-in-picture" allowfullscreen loading="lazy"></iframe>\n'
            '  </div>\n'
            '  <h3>%s</h3>\n'
            '</article>\n' % (it["id"], escape(it["title"]), escape(it["title"]))
        )
        log("homepage latest video: %s" % it["title"])
    else:
        video_inner = ""
        log("homepage latest video: none in Nextcloud")
    html = replace_markers(html, HOME_VIDEO_START, HOME_VIDEO_END, video_inner)

    posts = iter_posts(root)
    if posts:
        p = posts[0]
        img = ('      <img src="%s" alt="%s">\n' % (p["img"], escape(p["title"]))) if p["img"] else ""
        journal_inner = (
            '  <article class="journal-teaser">\n'
            '    <a href="%s">\n%s'
            '      <h3>%s</h3>\n'
            '    </a>\n'
            '  </article>\n' % (p["href"], img, escape(p["title"]))
        )
        log("homepage journal teaser: %s" % p["slug"])
    else:
        journal_inner = ""
    html = replace_markers(html, JOURNAL_START, JOURNAL_END, journal_inner)
    write_html(home, html)

def sync_videos(root, log):
    items = load_videos()
    log("videos from Nextcloud: %d (%s)" % (len(items), VIDEOS_NC))
    dest = root / "videos" / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    inner = videos_inner(items)
    main = (
        '<main id="content">\n'
        '  <section class="wrap section">\n'
        '    <h1>Videos</h1>\n'
        + inner +
        '  </section>\n'
        '</main>'
    )
    html = dest.read_text(encoding="utf-8") if dest.is_file() else chrome_from(root)
    if not html:
        html = (
            "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>Videos \u2014 Santa Bayanian</title>"
            "<link rel=\"stylesheet\" href=\"/css/site.css\">"
            "<link rel=\"stylesheet\" href=\"/css/theme.css\"></head>"
            "<body><main id=\"content\"></main>"
            "<script src=\"/js/site.js\" defer></script>"
            "<script src=\"/js/theme.js\" defer></script></body></html>"
        )
    html = replace_main(html, main)
    html = strip_stock_copy(html)
    if "<title>" in html:
        html = re.sub(r"<title>[^<]*</title>", "<title>Videos \u2014 Santa Bayanian</title>", html, count=1)
    write_html(dest, html)
    log("rewrote videos page with Nextcloud-only embeds")

def run(root, blog_nc, log):
    fix_blog_index_cards(root, log)
    sync_home(root, log)
    sync_videos(root, log)
    sync_about(root, log)
    for rel in ("contact/index.html", "blog/index.html"):
        strip_file(root / rel, log)

if __name__ == "__main__":
    root = Path(os.environ.get("BLOG_WEBROOT", os.environ.get("THEME_WEBROOT", "/var/www/santabayanian")))
    def log(msg):
        print(msg, flush=True)
    run(root, Path(os.environ.get("BLOG_DIR", "/mnt/data/ncdata/musicuser/files/Website/blog")), log)
    sys.exit(0)
