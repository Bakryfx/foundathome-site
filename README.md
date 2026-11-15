# Found at Home website

Static site for **foundathome.qimamai.tech** (GitHub Pages). No framework, no build tools, no trackers, no cookies.

## Add a product (3 steps)

1. **Add the image.** Save a frame from OUR video as WebP, about 720x900 (4:5), **150 KB or less**, in `img/products/` (for example `img/products/p004-oil-sprayer.webp`). Never use Amazon's product photos or screenshots.
2. **Edit `products.json`.** Add one entry inside `"products": [ ... ]` (order doesn't matter; the site sorts newest first):

   ```json
   {
     "id": "p004-oil-sprayer",
     "name": "Glass oil sprayer",
     "category": "kitchen",
     "note": "Sprays a thin, even coat of oil for air fryers and salads. Handy if you tend to pour too much.",
     "image": "img/products/p004-oil-sprayer.webp",
     "image_alt": "Hand spraying oil over an air fryer basket",
     "link": "https://amzn.to/XXXXXXX",
     "added": "2026-11-20"
   }
   ```
3. **Build and publish.** In this folder run `python build.py`, then commit and push:
   ```
   python build.py
   git add -A
   git commit -m "Add oil sprayer"
   git push
   ```
   If `build.py` prints "Not built", fix the listed lines in `products.json` and run it again.

## products.json fields

| Field | Required | Rules |
|---|---|---|
| `id` | yes | lowercase letters, digits, dashes; unique. Also the anchor: `https://foundathome.qimamai.tech/#p004-oil-sprayer` |
| `name` | yes | plain product name. No prices, ratings, "deal", "% off", "best seller". |
| `category` | yes | one of `kitchen`, `cleaning`, `organization`, `decor`, `gifts`, or a list like `["kitchen", "gifts"]` |
| `note` | yes | 1-2 original sentences (max 220 characters): what it does and who it's for, only from the listing's own facts. No "I tested" unless we really own and used it. |
| `image` | yes | local path in `img/products/`, WebP, 150 KB max. A frame from our own video. |
| `image_alt` | no | describes the image (defaults to the name) |
| `link` | yes | official link only: `https://amzn.to/...` from SiteStripe, or `https://www.amazon.com/dp/ASIN?tag=OUR-SITE-TAG`. Use the **site** tracking ID. No other shorteners or redirects. |
| `added` | yes | date `YYYY-MM-DD`; newest shows first |

`build.py` checks all of this (and blocks price/rating/deal wording), writes the list into `index.html` (so the page works without JavaScript and is readable by Google), and regenerates `sitemap.xml`. The page also re-reads `products.json` in the browser, so a forgotten build still shows the latest list to JS users.

## Files

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

Disclosure "As an Amazon Associate I earn from qualifying purchases." at the top of every page and in the footer, plus "Affiliate link" under every button. Buttons use `rel="sponsored nofollow noopener"` and open in a new tab. No prices, ratings, reviews, deal text, Amazon images or logos. No analytics or cookies.
