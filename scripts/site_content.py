#!/usr/bin/env python3
"""Homepage journal teaser, blog listing cards, videos from Nextcloud."""
from __future__ import annotations
import os, re, sys
from html import escape
from pathlib import Path

IMG_SRC_RE = re.compile(r'<img\b[^>]*?\bsrc=["\']([^"\']+)["\']', re.I)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TIME_RE = re.compile(r'<time[^>]*datetime=["\']([^"\']+)["\']', re.I)
YT_RE = re.compile(r"(?:youtu\.be/|v=|embed/|shorts/)([A-Za-z0-9_-]{11})")
JOURNAL_START = "<!-- journal:start -->"
JOURNAL_END = "<!-- journal:end -->"
VIDEOS_START = "<!-- videos:start -->"
VIDEOS_END = "<!-- videos:end -->"
VIDEOS_NC = Path(os.environ.get("VIDEOS_DIR", "/mnt/data/ncdata/musicuser/files/Website/videos"))
STOCK_COPY = [
    "Performance films and song videos. Pieces with a YouTube ID play here; the rest open a search until the official upload is wired in.",
    "Notes on music, physics, and the tools around the work. New categories appear when you add them to a post.",
    "Add a markdown file to Nextcloud Website/videos with a YouTube URL.",
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

def strip_stock_copy(html):
    html = html.replace("hello@santabayanian.com", "keith@santabayanian.com")
    for phrase in STOCK_COPY:
        html = html.replace(phrase, "")
    html = re.sub(r'<p class="lede">\s*</p>\s*', "", html)
    html = re.sub(r'<p>\s*</p>\s*', "", html)
    return html

def strip_home_placeholder_videos(html):
    """Remove stock film/video cards from the homepage. Keep the mascot hero loop."""
    patterns = [
        r'<section\b[^>]*\bid=["\']videos["\'][^>]*>[\s\S]*?</section>\s*',
        r'<section\b[^>]*class=["\'][^"\']*\bvideos\b[^"\']*["\'][^>]*>[\s\S]*?</section>\s*',
        r'<section\b[^>]*>[\s\S]{0,2500}?<p class=["\']kicker["\']>\s*(?:On film|Videos|Watch|Film|Performance)\s*</p>[\s\S]*?</section>\s*',
        r'<section\b[^>]*>[\s\S]{0,8000}?(?:video-grid|video-card|/images/videos/|youtube-nocookie|youtube\.com/embed|youtu\.be)[\s\S]*?</section>\s*',
        r'<article\b[^>]*class=["\'][^"\']*video-card[^"\']*["\'][^>]*>[\s\S]*?</article>\s*',
        r'<iframe\b[^>]*(?:youtube|youtu\.be)[^>]*>[\s\S]*?</iframe>\s*',
    ]
    for pat in patterns:
        html = re.sub(pat, "", html, flags=re.I)
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

def sync_home_journal(root, log):
    home = root / "index.html"
    if not home.is_file():
        return
    posts = iter_posts(root)
    html = home.read_text(encoding="utf-8")
    before = html
    html = strip_stock_copy(html)
    html = strip_home_placeholder_videos(html)
    if posts:
        p = posts[0]
        img = ('        <img src="%s" alt="%s">\n' % (p["img"], escape(p["title"]))) if p["img"] else ""
        inner = (
            JOURNAL_START + "\n"
            '<section class="wrap section" id="from-the-journal">\n'
            '  <div class="section-head"><p class="kicker">Journal</p><h2>Latest from the blog</h2></div>\n'
            '  <article class="journal-teaser">\n'
            '    <a href="%s">\n%s'
            '      <h3>%s</h3>\n'
            '    </a>\n'
            '  </article>\n'
            '</section>\n' % (p["href"], img, escape(p["title"]))
            + JOURNAL_END
        )
        if JOURNAL_START in html and JOURNAL_END in html:
            html = re.sub(re.escape(JOURNAL_START) + r"[\s\S]*?" + re.escape(JOURNAL_END), inner, html, count=1)
        elif 'id="recent-releases"' in html:
            html = re.sub(r'(id="recent-releases"[\s\S]*?</section>)', r"\1\n" + inner, html, count=1)
        elif "</main>" in html:
            html = html.replace("</main>", inner + "\n</main>", 1)
        log("homepage journal teaser: %s" % p["slug"])
    if html != before:
        write_html(home, html)
        log("stripped leftover homepage videos; kept mascot hero")

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
        body = ""
    else:
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
        body = '<div class="video-grid">\n' + "".join(cards) + '</div>\n'
    return VIDEOS_START + "\n" + body + VIDEOS_END

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
    if dest.is_file():
        html = dest.read_text(encoding="utf-8")
    else:
        html = chrome_from(root)
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
    sync_home_journal(root, log)
    sync_videos(root, log)
    for rel in ("contact/index.html", "about/index.html", "blog/index.html"):
        strip_file(root / rel, log)

if __name__ == "__main__":
    root = Path(os.environ.get("BLOG_WEBROOT", os.environ.get("THEME_WEBROOT", "/var/www/santabayanian")))
    def log(msg):
        print(msg, flush=True)
    run(root, Path(os.environ.get("BLOG_DIR", "/mnt/data/ncdata/musicuser/files/Website/blog")), log)
    sys.exit(0)
