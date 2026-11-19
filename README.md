# Found at Home website

Static site for **foundathome.qimamai.tech** (GitHub Pages). No framework, no build tools, no cookies; visits are counted with cookieless Cloudflare Web Analytics (beacon in every page head, allowed in the CSP).

## Add a product (3 steps)

1. **Add the image.** Save a frame from OUR video as WebP, about 720x900 (4:5), **150 KB or less**, in `img/products/` (for example `img/products/p004-oil-sprayer.webp`). Never use Amazon's product photos or screenshots.
2. **Edit `products.json`.** Add one entry inside `"products": [ ... ]` (order doesn't matter). The homepage lists only products whose reel has gone live (go-live time comes from `company/social_manager/queue.json`, matched by ASIN, read-only), newest post first; future ones stay hidden until you rebuild after their date. Never add view counts from other creators' videos:

   ```json
   {
     "id": "p004-oil-sprayer",
     "slug": "glass-oil-sprayer",
     "name": "Glass oil sprayer",
     "category": ["kitchen", "gifts"],
     "short_note": "Sprays a thin, even coat of oil for air fryers and salads. Handy if you tend to pour too much.",
     "image": "img/products/p004-oil-sprayer.webp",
     "image_alt": "Hand spraying oil over an air fryer basket",
     "link": "https://amzn.to/XXXXXXX",
     "added": "2026-11-20",
     "headline": "The oil sprayer that stops you over-pouring",
     "intro": "2-3 sentences in our own words.",
     "why_we_like": ["3 to 5 short bullets", "from listing facts only", "in our words"],
     "good_to_know": ["1 to 3 honest caveats, e.g. measure your cabinet first"],
     "who_its_for": "One sentence about who will like it.",
     "faq": [{"q": "Question?", "a": "Short answer."}, {"q": "Second question?", "a": "Answer."}],
     "video": "img/products/p004-oil-sprayer.mp4"
   }
   ```
3. **Build and publish.** In this folder run `python build.py`, then commit and push:
   ```
   python build.py
   git add -A
   git commit -m "Add oil sprayer"
   git push
   ```
   `build.py` writes the hub card, the product page `p/<slug>/index.html` and the sitemap. If it prints "Not built", fix the listed lines in `products.json` and run it again.

## products.json fields

| Field | Required | Rules |
|---|---|---|
| `id` | yes | lowercase letters, digits, dashes; unique. Also the hub anchor. |
| `slug` | no | URL name: page is `/p/<slug>/`. Defaults to `id`. Lowercase letters, digits, dashes; unique. |
| `name` | yes | plain product name. |
| `category` | yes | one of `kitchen`, `cleaning`, `organization`, `decor`, `gifts`, or a list. The first one is used in the breadcrumb. |
| `short_note` | yes | hub-card text, 1-2 original sentences (max 220 chars), from listing facts only. (`note` is still accepted as an old name.) |
| `image` | yes | local path in `img/products/`, WebP, 150 KB max, a frame from our own video. |
| `image_alt` | no | describes the image (defaults to the name) |
| `link` | yes | official link only: `https://amzn.to/...` or `https://www.amazon.com/dp/ASIN?tag=foundsite-20`. Use the **site** tracking ID. |
| `added` | yes | date `YYYY-MM-DD`; newest shows first |
| `headline` | yes | the page H1 |
| `intro` | yes | 2-3 sentences, our own words |
| `why_we_like` | yes | list of 3-5 bullets |
| `good_to_know` | yes | list of 1-3 honest caveats |
| `who_its_for` | yes | one or two sentences |
| `faq` | yes | list of 2-4 `{"q","a"}` pairs (also written as FAQPage JSON-LD) |
| `video` | no | path to OUR short `.mp4` (max 8 MB, lazy-loaded, poster = `image`) or an 11-character YouTube Shorts ID (the player loads only after a tap, so no third-party request before that) |

**Hard rule (Amazon Associates Operating Agreement):** never show Amazon prices, star ratings, review counts, customer review text or "bought in past month" counts. `build.py` rejects `$`, price, rating, stars, reviews, bought, sold, "% off", deal, sale, discount, best seller, and "I/we tested" in every text field, bullets and FAQ included, and refuses to build.

Product pages carry three identical official buy buttons (under the hero, after "Why we like it", at the bottom) plus a sticky bottom bar on phones. All use `rel="sponsored nofollow noopener"` and `target="_blank"`. Structured data is BreadcrumbList + FAQPage only (no Product, Review or AggregateRating).

## Files

- `p/<slug>/index.html` - generated product pages (the whole `p/` folder is rebuilt every run).
- `index.html` - bio-link hub. The block between `<!-- build:products` and `<!-- /build:products -->` is generated; don't edit it by hand.
- `about.html`, `404.html`, `styles.css`, `app.js` (category filter only)
- `fonts/` - Fraunces + DM Sans, self-hosted WOFF2 subsets (SIL Open Font License, licence files included)
- `img/og-image.png` (social share card), `img/icon-512.png`, `favicon.ico`, `apple-touch-icon.png` (made by `assets/brand/make_site_icons.py`)
- `CNAME` (custom domain), `robots.txt`, `sitemap.xml` (generated), `.nojekyll`

## Before going live

- **Facebook link is a placeholder** (`https://www.facebook.com/profile.php?id=61596432606815`). Replace it with the real Page URL in `build.py` (SOCIALS), `index.html` and `about.html` (footer), then run `python build.py`.
- Add `foundathome.qimamai.tech` to the Associates account's website list, and use the site tracking ID in every link.
- DNS: a CNAME record `foundathome` -> `<github-username>.github.io` at Hostinger; then in the repo's Settings > Pages, set the custom domain and tick "Enforce HTTPS".

## Rules this site follows (Amazon Associates)

Disclosure "As an Amazon Associate I earn from qualifying purchases." at the top of every page and in the footer, plus "Affiliate link" under every button. Buttons use `rel="sponsored nofollow noopener"` and open in a new tab. No prices, ratings, reviews, deal text, Amazon images or logos. No cookies; only cookieless Cloudflare Web Analytics.
