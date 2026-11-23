#!/usr/bin/env python3
"""Found at Home site builder (Python 3.8+, standard library only).

What it does:
  1. Reads products.json and checks every product (Amazon site rules included).
  2. Pre-renders the product list into index.html, newest first, so the page
     works with JavaScript off and search engines can read it. Each card links
     to its own product page.
  3. Writes one page per product: p/<slug>/index.html (hero, three buy buttons,
     sticky mobile bar, FAQ; BreadcrumbList + FAQPage JSON-LD only, no Product schema).
  4. Writes sitemap.xml (home, about, every product page).

Usage (from this folder):   python build.py
Exit code 1 = a product has a problem; nothing is written in that case.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://foundathome.qimamai.tech/"
PAGES = ["", "about.html"]  # static pages in sitemap.xml ("" = home); product pages are added automatically
PAGES_DIR = "p"

CATEGORIES = {  # slug -> label (order = chip order)
    "kitchen": "Kitchen",
    "cleaning": "Cleaning",
    "organization": "Organization",
    "decor": "Decor",
    "gifts": "Gifts",
}

SOCIALS = [  # (label, url)
    ("TikTok", "https://www.tiktok.com/@found.athome"),
    ("Instagram", "https://www.instagram.com/found.athome/"),
    ("YouTube", "https://www.youtube.com/@foundathome"),
    ("Pinterest", "https://www.pinterest.com/foundathomefinds/"),
    ("Facebook", "https://www.facebook.com/profile.php?id=61596432606815"),  # PLACEHOLDER: replace with the real Page URL
]

ALLOWED_LINK_HOSTS = {"amzn.to", "www.amazon.com", "amazon.com"}
# Amazon Operating Agreement: no prices, ratings, reviews, sales counts or deal wording.
BANNED = re.compile(
    r"[$£€]|%\s?off\b|\bdeals?\b|\bsale\b|\bdiscount|\bcheap(?:est)?\b|\bpric(?:e|es|ed|ing)\b|"
    r"\bstars?\b|\brat(?:ing|ings|ed)\b|\breviews?(?:ed|ers?)?\b|\bbest[- ]?seller|\bbought\b|\bsold\b|"
    r"\bpast month\b|\bi tested\b|\bwe tested\b",
    re.I,
)
MAX_IMAGE_BYTES = 150 * 1024
MAX_VIDEO_BYTES = 8 * 1024 * 1024
START = "<!-- build:products"
END = "<!-- /build:products -->"
TEXT_FIELDS = ("name", "short_note", "headline", "intro", "who_its_for", "social_proof")
LIST_FIELDS = ("why_we_like", "good_to_know")

esc = html.escape


def load_products() -> list[dict]:
    data = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    items = data["products"] if isinstance(data, dict) else data
    if not isinstance(items, list):
        sys.exit("products.json: 'products' must be a list")
    for p in items:  # old files used "note"
        if "short_note" not in p and "note" in p:
            p["short_note"] = p["note"]
    return items


def fmt_num(m: re.Match) -> str:
    n = int(m.group(0).replace(",", ""))
    if n >= 1_000_000:
        v, u = n / 1_000_000, "M"
    elif n >= 1000:
        v, u = n / 1000, "K"
    else:
        return str(n)
    t = f"{v:.1f}" if v < 10 else f"{v:.0f}"
    return t.rstrip("0").rstrip(".") + u if "." in t else t + u


def proof_text(p: dict) -> str:
    """'3200000 views on TikTok' -> '3.2M views on TikTok' (already short numbers stay as written)."""
    return re.sub(r"\d[\d,]{3,}", fmt_num, str(p.get("social_proof") or "").strip())


def slug_of(p: dict) -> str:
    return str(p.get("slug") or p["id"])


def categories_of(p: dict) -> list[str]:
    c = p.get("category", [])
    return [c] if isinstance(c, str) else list(c)


def check(products: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    seen_slugs: set[str] = set()
    for i, p in enumerate(products):
        where = f"product #{i + 1} ({p.get('id', 'no id')})"
        for field in ("id", "name", "category", "short_note", "image", "link", "added",
                      "headline", "intro", "why_we_like", "good_to_know", "who_its_for", "faq"):
            if not p.get(field):
                errors.append(f"{where}: missing '{field}'")
        pid = str(p.get("id", ""))
        if pid and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", pid):
            errors.append(f"{where}: id must be lowercase letters, digits and dashes")
        if pid in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(pid)
        if pid:
            slug = slug_of(p)
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
                errors.append(f"{where}: slug must be lowercase letters, digits and dashes")
            if slug in seen_slugs:
                errors.append(f"{where}: duplicate slug '{slug}'")
            seen_slugs.add(slug)
        for c in categories_of(p):
            if c not in CATEGORIES:
                errors.append(f"{where}: unknown category '{c}' (use {', '.join(CATEGORIES)})")
        link = str(p.get("link", ""))
        u = urlparse(link)
        if link and (u.scheme != "https" or u.hostname not in ALLOWED_LINK_HOSTS):
            errors.append(f"{where}: link must be https://amzn.to/... or https://www.amazon.com/dp/...?tag=...")
        if u.hostname in {"www.amazon.com", "amazon.com"} and "tag=" not in (u.query or ""):
            errors.append(f"{where}: amazon.com link has no tag= tracking ID")

        # lists and FAQ shape
        for field in LIST_FIELDS:
            v = p.get(field)
            if v is not None and not (isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)):
                errors.append(f"{where}: '{field}' must be a list of text lines")
        wl, gk = p.get("why_we_like"), p.get("good_to_know")
        if isinstance(wl, list) and not 3 <= len(wl) <= 5:
            errors.append(f"{where}: why_we_like needs 3-5 bullets (has {len(wl)})")
        if isinstance(gk, list) and not 1 <= len(gk) <= 3:
            errors.append(f"{where}: good_to_know needs 1-3 items (has {len(gk)})")
        faq = p.get("faq")
        if faq is not None:
            if not (isinstance(faq, list) and all(isinstance(x, dict) and x.get("q") and x.get("a") for x in faq)):
                errors.append(f"{where}: faq must be a list of {{\"q\": ..., \"a\": ...}}")
            elif not 2 <= len(faq) <= 4:
                errors.append(f"{where}: faq needs 2-4 questions (has {len(faq)})")

        # banned wording in EVERY text field, including list items and FAQ
        texts: list[tuple[str, str]] = [(f, str(p.get(f, ""))) for f in TEXT_FIELDS]
        for f in LIST_FIELDS:
            if isinstance(p.get(f), list):
                texts += [(f, str(x)) for x in p[f]]
        if isinstance(faq, list):
            for x in faq:
                if isinstance(x, dict):
                    texts += [("faq", str(x.get("q", ""))), ("faq", str(x.get("a", "")))]
        for field, val in texts:
            m = BANNED.search(val)
            if m:
                errors.append(f"{where}: '{field}' contains '{m.group(0)}' (no prices, ratings, reviews, sales counts, deal or 'tested' wording)")
        sp = str(p.get("social_proof") or "")
        if sp and re.search(r"amazon", sp, re.I):
            errors.append(f"{where}: social_proof must be non-Amazon data only (e.g. TikTok views)")
        if sp and not re.search(r"tiktok|instagram", sp, re.I):
            errors.append(f"{where}: social_proof must say where the number is from, e.g. '3.2M views on TikTok' or '190M views on Instagram'")
        note = str(p.get("short_note", ""))
        if len(note) > 220:
            errors.append(f"{where}: short_note is {len(note)} characters; keep it to 1-2 short sentences (max 220)")

        img = str(p.get("image", ""))
        if img:
            if img.startswith(("http:", "https:", "//", "/")):
                errors.append(f"{where}: image must be our own file in img/products/, not a web link")
            else:
                f = ROOT / img
                if not f.is_file():
                    errors.append(f"{where}: image file not found: {img}")
                elif f.stat().st_size > MAX_IMAGE_BYTES:
                    errors.append(f"{where}: image is {f.stat().st_size // 1024} KB (max 150 KB)")
        vid = str(p.get("video") or "")
        if vid:
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
                pass  # YouTube Shorts ID
            elif vid.endswith(".mp4") and not vid.startswith(("http", "/")):
                f = ROOT / vid
                if not f.is_file():
                    errors.append(f"{where}: video file not found: {vid}")
                elif f.stat().st_size > MAX_VIDEO_BYTES:
                    errors.append(f"{where}: video is {f.stat().st_size // 1024} KB (max 8192 KB)")
            else:
                errors.append(f"{where}: video must be a local .mp4 path (our own short) or an 11-character YouTube ID")
        try:
            dt.date.fromisoformat(str(p.get("added", "")))
        except ValueError:
            errors.append(f"{where}: 'added' must be a date like 2026-11-20")
    return errors


def sort_newest(products: list[dict]) -> list[dict]:
    # newest first; for the same date, the one listed later in the file comes first
    # "featured": 1..4 = our most watched videos (set by hand from the daily report); they go first
    indexed = list(enumerate(products))
    indexed.sort(key=lambda t: (str(t[1]["added"]), t[0]), reverse=True)
    out = [p for _, p in indexed]
    top = sorted((p for p in out if p.get("featured")), key=lambda p: int(p["featured"]))
    return top + [p for p in out if not p.get("featured")]


# ---------------------------------------------------------------- hub (index.html)

def card(p: dict, eager: bool) -> str:
    cats = categories_of(p)
    label = " · ".join(CATEGORIES[c] for c in cats)
    if p.get("featured"):
        label = "Most watched · " + label
    loading = 'fetchpriority="high"' if eager else 'loading="lazy"'
    href = f"{PAGES_DIR}/{esc(slug_of(p))}/"
    sp = proof_text(p)
    badge = f'<span class="proof-badge">🔥 {esc(sp)}</span>' if sp else ""
    return (
        f'  <li class="card" id="{esc(p["id"])}" data-cat="{esc(" ".join(cats))}">\n'
        f'    <a class="card-imglink" href="{href}" tabindex="-1" aria-hidden="true">'
        f'<img class="card-img" src="{esc(p["image"])}" alt="" width="400" height="500" {loading} decoding="async">{badge}</a>\n'
        f'    <div class="card-body">\n'
        f'      <p class="card-cat">{esc(label)}</p>\n'
        f'      <h3 class="card-name"><a href="{href}">{esc(p["name"])}</a></h3>\n'
        f'      <p class="card-note">{esc(p["short_note"])}</p>\n'
        f'      <a class="btn" href="{href}">See the find<span class="sr-only"> : {esc(p["name"])}</span></a>\n'
        f'    </div>\n'
        f'  </li>'
    )


def block(products: list[dict]) -> str:
    has = bool(products)
    chips = "\n".join(
        f'  <li><button class="chip" type="button" data-filter="{slug}" aria-pressed="{"true" if slug == "all" else "false"}">{label}</button></li>'
        for slug, label in [("all", "All"), *CATEGORIES.items()]
    )
    cards = "\n".join(card(p, i < 2) for i, p in enumerate(products))
    socials = "\n".join(
        f'    <li><a class="social" href="{esc(url)}" rel="noopener me" target="_blank">{esc(label)}</a></li>'
        for label, url in SOCIALS
    )
    hide = lambda show: "" if show else " hidden"  # noqa: E731
    return f"""{START} (generated by build.py from products.json; edits here are overwritten) -->
<ul class="chips" aria-label="Filter by category"{hide(has)}>
{chips}
</ul>
<section class="finds" aria-labelledby="finds-title"{hide(has)}>
  <h2 class="sr-only" id="finds-title">Latest finds</h2>
  <ul class="grid" id="grid">
{cards}
  </ul>
  <p class="filter-empty" id="filter-empty" hidden>Nothing in this category yet. <a href="#main" data-show-all>See all finds</a></p>
</section>
<section class="soon" id="soon" aria-labelledby="soon-title"{hide(not has)}>
  <h2 id="soon-title">First finds drop this week ✨</h2>
  <p>Follow us so you see them first. We post short videos of kitchen, cleaning and home finds, and each one lands here with its own page and a link to check it on Amazon.</p>
  <ul class="socials">
{socials}
  </ul>
</section>
{END}"""


def write_index(products: list[dict]) -> None:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    a, b = text.find(START), text.find(END)
    if a < 0 or b < 0:
        sys.exit("index.html: build markers are missing")
    new = text[:a] + block(products) + text[b + len(END):]
    path.write_text(new, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- product pages

HEAD_COMMON = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="p:domain_verify" content="3775eae66bc25f1ad8ce753083a0d03d"/>
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https://static.cloudflareinsights.com; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://cloudflareinsights.com; frame-src https://www.youtube-nocookie.com; base-uri 'self'; form-action 'none'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="theme-color" content="#F6EFE6">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" href="/fonts/fraunces.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/dmsans.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/styles.css">"""


def buy_button(p: dict, where: str) -> str:
    return (
        f'<a class="btn btn-buy" href="{esc(p["link"])}" rel="sponsored nofollow noopener" target="_blank" '
        f'data-pos="{where}">Buy on Amazon<span class="sr-only"> (opens Amazon in a new tab)</span></a>'
    )


def media(p: dict) -> str:
    alt = esc(p.get("image_alt") or p["name"])
    img = f'/{esc(p["image"])}'
    vid = str(p.get("video") or "")
    if not vid:
        return f'<img class="hero-img" src="{img}" alt="{alt}" width="720" height="900" fetchpriority="high" decoding="async">'
    if vid.endswith(".mp4"):
        # 9:16 cover frame from our reel (img/products/<name>-poster.webp) if present, else the 4:5 image
        pst = vid[:-4] + "-poster.webp"
        poster = f'/{esc(pst)}' if (ROOT / pst).is_file() else img
        return (
            f'<video class="hero-img hero-vid" controls playsinline preload="none" poster="{poster}" width="720" height="1280">'
            f'<source src="/{esc(vid)}" type="video/mp4">'
            f'<img src="{img}" alt="{alt}"></video>'
        )
    # YouTube Shorts: no third-party request until the visitor presses play (app.js swaps in the player)
    return (
        f'<div class="hero-video" data-yt="{esc(vid)}">'
        f'<img class="hero-img" src="{img}" alt="{alt}" width="720" height="900" fetchpriority="high" decoding="async">'
        f'<a class="yt-play" href="https://www.youtube.com/shorts/{esc(vid)}" rel="noopener" target="_blank">'
        f'<span aria-hidden="true">&#9654;</span> Watch the short video</a></div>'
    )


def li_list(items: list[str]) -> str:
    return "\n".join(f"          <li>{esc(x)}</li>" for x in items)


def product_page(p: dict) -> str:
    slug = slug_of(p)
    url = f"{SITE_URL}{PAGES_DIR}/{slug}/"
    cats = categories_of(p)
    first_cat = cats[0]
    title = f"{p['name']} | Found at Home"
    desc = p["short_note"]
    og_img = f"{SITE_URL}{p['image']}"
    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Found at Home", "item": SITE_URL},
                    {"@type": "ListItem", "position": 2, "name": CATEGORIES[first_cat], "item": f"{SITE_URL}#filter-{first_cat}"},
                    {"@type": "ListItem", "position": 3, "name": p["name"], "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": x["q"], "acceptedAnswer": {"@type": "Answer", "text": x["a"]}}
                    for x in p["faq"]
                ],
            },
        ],
    }
    faq = "\n".join(
        f'        <details class="faq-item"><summary>{esc(x["q"])}</summary><p>{esc(x["a"])}</p></details>' for x in p["faq"]
    )
    proof = f'<p class="proof">🔥 {esc(proof_text(p))}</p>\n      ' if p.get("social_proof") else ""
    label = " · ".join(CATEGORIES[c] for c in cats)
    socials = "\n".join(
        f'      <li><a href="{esc(u)}" rel="noopener me" target="_blank">{esc(l)}</a></li>' for l, u in SOCIALS
    )
    jsonld_text = json.dumps(jsonld, indent=2, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
{HEAD_COMMON}
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Found at Home">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{esc(og_img)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{jsonld_text}
</script>
<script src="/app.js" defer></script>
<!-- Cloudflare Web Analytics (cookieless) -->
<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "04fcfedd50024aaa947650f196691369"}}'></script>
</head>
<body class="product-page">
<header class="masthead small wrap">
  <a class="home" href="/" aria-label="Found at Home, back to all finds">
    <svg class="mark" viewBox="160 150 680 690" aria-hidden="true" focusable="false">
      <path class="house" d="M240 800V460L500 200L760 460V800Z"/>
      <path class="spark" d="M500 510L524 596L610 620L524 644L500 730L476 644L390 620L476 596Z"/>
    </svg>
    <span class="brand">Found at Home</span>
  </a>
</header>

<main class="wrap pp" id="main">
  <nav class="crumbs" aria-label="Breadcrumb">
    <ol>
      <li><a href="/">All finds</a></li>
      <li><a href="/#filter-{esc(first_cat)}">{esc(CATEGORIES[first_cat])}</a></li>
      <li aria-current="page">{esc(p["name"])}</li>
    </ol>
  </nav>

  <article class="pp-grid">
    <div class="pp-media">
      {media(p)}
    </div>

    <div class="pp-main">
      <p class="card-cat">{esc(label)}</p>
      <h1 class="pp-title">{esc(p["headline"])}</h1>
      {proof}<p class="pp-name">{esc(p["name"])}</p>
      <div class="buy-block">
        {buy_button(p, "top")}
        <p class="disclosure-top">As an Amazon Associate I earn from qualifying purchases.</p>
      </div>

      <p class="pp-intro">{esc(p["intro"])}</p>

      <section aria-labelledby="why">
        <h2 id="why">Why we like it</h2>
        <ul class="ticks">
{li_list(p["why_we_like"])}
        </ul>
      </section>

      <div class="buy-block">
        {buy_button(p, "middle")}
        <p class="card-ad">Affiliate link</p>
      </div>

      <section aria-labelledby="know">
        <h2 id="know">Good to know</h2>
        <ul class="notes">
{li_list(p["good_to_know"])}
        </ul>
      </section>

      <section aria-labelledby="who">
        <h2 id="who">Who it's for</h2>
        <p>{esc(p["who_its_for"])}</p>
      </section>

      <section aria-labelledby="faq">
        <h2 id="faq">Quick questions</h2>
{faq}
      </section>

      <div class="buy-block buy-last">
        {buy_button(p, "bottom")}
        <p class="card-ad">Affiliate link. As an Amazon Associate I earn from qualifying purchases.</p>
      </div>

      <p class="back"><a href="/">&larr; Back to all finds</a></p>
    </div>
  </article>
</main>

<div class="sticky-buy">
  <a class="btn btn-buy" href="{esc(p["link"])}" rel="sponsored nofollow noopener" target="_blank" data-pos="sticky">Buy on Amazon<span class="sr-only"> (opens Amazon in a new tab)</span></a>
  <p>Affiliate link</p>
</div>

<footer class="site-footer">
  <div class="wrap">
    <ul class="footer-links" aria-label="Found at Home on social media">
{socials}
    </ul>
    <p class="disclosure-full">Found at Home is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com. As an Amazon Associate I earn from qualifying purchases. If you buy through a link on this site, we may earn a commission at no extra cost to you.</p>
    <p class="footer-meta">© 2026 Found at Home · a QIMAM project · <a href="/about.html">About us</a></p>
  </div>
</footer>
</body>
</html>
"""


def write_product_pages(products: list[dict]) -> int:
    out = ROOT / PAGES_DIR
    if out.exists():
        shutil.rmtree(out)  # pages of removed products disappear
    for p in products:
        d = out / slug_of(p)
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(product_page(p), encoding="utf-8", newline="\n")
    return len(products)


def write_sitemap(products: list[dict]) -> None:
    today = dt.date.today().isoformat()
    home_mod = max([str(p["added"]) for p in products] + [today if not products else ""])
    rows = []
    for page in PAGES:
        f = ROOT / (page or "index.html")
        lastmod = home_mod if page == "" else dt.date.fromtimestamp(f.stat().st_mtime).isoformat()
        rows.append(f"  <url>\n    <loc>{SITE_URL}{page}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>")
    for p in products:
        rows.append(f"  <url>\n    <loc>{SITE_URL}{PAGES_DIR}/{slug_of(p)}/</loc>\n    <lastmod>{p['added']}</lastmod>\n  </url>")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8", newline="\n")


def main() -> None:
    products = load_products()
    errors = check(products)
    if errors:
        print("Not built. Fix these in products.json:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    products = sort_newest(products)
    write_index(products)
    n = write_product_pages(products)
    write_sitemap(products)
    print(f"Built index.html, {n} product page(s) and sitemap.xml.")


if __name__ == "__main__":
    main()
