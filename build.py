#!/usr/bin/env python3
"""Found at Home site builder (Python 3.8+, standard library only).

What it does:
  1. Reads products.json and checks every product (Amazon site rules included).
  2. Pre-renders the product list into index.html, newest first, so the page
     works with JavaScript off and search engines can read it.
  3. Writes sitemap.xml.

Usage (from this folder):   python build.py
Exit code 1 = a product has a problem; nothing is written in that case.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://foundathome.qimamai.tech/"
PAGES = ["", "about.html"]  # pages listed in sitemap.xml ("" = home)

CATEGORIES = {  # slug -> label (order = chip order)
    "kitchen": "Kitchen",
    "cleaning": "Cleaning",
    "organization": "Organization",
    "decor": "Decor",
    "gifts": "Gifts",
}

SOCIALS = [  # (label, url) - FB is a placeholder until the Page URL is confirmed
    ("TikTok", "https://www.tiktok.com/@found.athome"),
    ("Instagram", "https://www.instagram.com/found.athome/"),
    ("YouTube", "https://www.youtube.com/@foundathome"),
    ("Pinterest", "https://www.pinterest.com/foundathomefinds/"),
    ("Facebook", "https://www.facebook.com/profile.php?id=61596432606815"),  # PLACEHOLDER: replace with the real Page URL
]

ALLOWED_LINK_HOSTS = {"amzn.to", "www.amazon.com", "amazon.com"}
# Amazon Operating Agreement: no prices, ratings or deal wording outside the PA-API.
BANNED = re.compile(
    r"[$£€]\s?\d|\b\d+\s?%\s?off\b|\bdeals?\b|\bsale\b|\bdiscount|\bcheapest\b|"
    r"\bstars?\b|\brating|\breviews?\b|\bbest[- ]?seller|\bi tested\b|\bwe tested\b",
    re.I,
)
MAX_IMAGE_BYTES = 150 * 1024
START = "<!-- build:products"
END = "<!-- /build:products -->"

esc = html.escape


def load_products() -> list[dict]:
    data = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    items = data["products"] if isinstance(data, dict) else data
    if not isinstance(items, list):
        sys.exit("products.json: 'products' must be a list")
    return items


def categories_of(p: dict) -> list[str]:
    c = p.get("category", [])
    return [c] if isinstance(c, str) else list(c)


def check(products: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for i, p in enumerate(products):
        where = f"product #{i + 1} ({p.get('id', 'no id')})"
        for field in ("id", "name", "category", "note", "image", "link", "added"):
            if not p.get(field):
                errors.append(f"{where}: missing '{field}'")
        pid = str(p.get("id", ""))
        if pid and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", pid):
            errors.append(f"{where}: id must be lowercase letters, digits and dashes")
        if pid in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(pid)
        for c in categories_of(p):
            if c not in CATEGORIES:
                errors.append(f"{where}: unknown category '{c}' (use {', '.join(CATEGORIES)})")
        link = str(p.get("link", ""))
        u = urlparse(link)
        if link and (u.scheme != "https" or u.hostname not in ALLOWED_LINK_HOSTS):
            errors.append(f"{where}: link must be https://amzn.to/... or https://www.amazon.com/dp/...?tag=...")
        if u.hostname in {"www.amazon.com", "amazon.com"} and "tag=" not in (u.query or ""):
            errors.append(f"{where}: amazon.com link has no tag= tracking ID")
        for field in ("name", "note"):
            m = BANNED.search(str(p.get(field, "")))
            if m:
                errors.append(f"{where}: '{field}' contains '{m.group(0)}' (no prices, ratings, reviews, deal or 'tested' wording)")
        note = str(p.get("note", ""))
        if len(note) > 220:
            errors.append(f"{where}: note is {len(note)} characters; keep it to 1-2 short sentences (max 220)")
        img = str(p.get("image", ""))
        if img:
            if img.startswith(("http:", "https:", "//")):
                errors.append(f"{where}: image must be our own file in img/products/, not a web link")
            else:
                f = ROOT / img
                if not f.is_file():
                    errors.append(f"{where}: image file not found: {img}")
                elif f.stat().st_size > MAX_IMAGE_BYTES:
                    errors.append(f"{where}: image is {f.stat().st_size // 1024} KB (max 150 KB)")
        try:
            dt.date.fromisoformat(str(p.get("added", "")))
        except ValueError:
            errors.append(f"{where}: 'added' must be a date like 2026-11-20")
    return errors


def sort_newest(products: list[dict]) -> list[dict]:
    # newest first; for the same date, the one listed later in the file comes first
    indexed = list(enumerate(products))
    indexed.sort(key=lambda t: (str(t[1]["added"]), t[0]), reverse=True)
    return [p for _, p in indexed]


def card(p: dict, eager: bool) -> str:
    cats = categories_of(p)
    label = " · ".join(CATEGORIES[c] for c in cats)
    alt = p.get("image_alt") or p["name"]
    loading = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return (
        f'  <li class="card" id="{esc(p["id"])}" data-cat="{esc(" ".join(cats))}">\n'
        f'    <img class="card-img" src="{esc(p["image"])}" alt="{esc(alt)}" width="400" height="500" {loading} decoding="async">\n'
        f'    <div class="card-body">\n'
        f'      <p class="card-cat">{esc(label)}</p>\n'
        f'      <h3 class="card-name">{esc(p["name"])}</h3>\n'
        f'      <p class="card-note">{esc(p["note"])}</p>\n'
        f'      <a class="btn" href="{esc(p["link"])}" rel="sponsored nofollow noopener" target="_blank">'
        f'Check it on Amazon<span class="sr-only"> (opens Amazon in a new tab)</span></a>\n'
        f'      <p class="card-ad">Affiliate link</p>\n'
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
  <p>Follow us so you see them first. We post short videos of kitchen, cleaning and home finds, and each one lands here with a link to check it on Amazon.</p>
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


def write_sitemap(products: list[dict]) -> None:
    today = dt.date.today().isoformat()
    home_mod = max([str(p["added"]) for p in products] + [today if not products else ""])
    rows = []
    for page in PAGES:
        f = ROOT / (page or "index.html")
        lastmod = home_mod if page == "" else dt.date.fromtimestamp(f.stat().st_mtime).isoformat()
        rows.append(f"  <url>\n    <loc>{SITE_URL}{page}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>")
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
    write_sitemap(products)
    print(f"Built index.html with {len(products)} product(s) and sitemap.xml.")


if __name__ == "__main__":
    main()
