# Google indexing package

This package contains only the public crawling files for
`https://infinityhouseproperties.com/`.

## Files

- `robots.txt` allows crawlers to access public pages and assets, and points
  them to the sitemap. It does not make private routes secure.
- `sitemap.xml` lists only the homepage and the three informational routes
  declared by the frontend router: About, Contact, and Property Management.
  It intentionally contains no property URLs because current listings are
  dynamic and no specific public property records were verified for this
  static package.

The four page titles, descriptions, and canonical URLs are maintained in
`frontend/seo-pages.json`. The frontend build writes route-specific HTML files
for the informational pages, so crawlers receive their metadata in the initial
HTML response. The root page's source metadata is in `frontend/index.html`;
React also updates metadata during client-side navigation.

After `npm run build` in `frontend/`, deploy the complete contents of
`frontend/dist` (including each route directory and its `index.html`, the root
`index.html`, assets, and `.htaccess`). The route folders are served with
trailing slashes, matching their canonical URLs and sitemap entries. Do not
upload or use the source `frontend/index.html` by itself as a replacement for
the built site.

The generated route files are directory indexes (`about/index.html`,
`contact/index.html`, and `property-management/index.html`). The existing
Apache `.htaccess` leaves those real directories to Apache, which normally
redirects a bare route such as `/about` to `/about/`. Confirm that behavior
after upload; the canonical URLs and sitemap use the trailing-slash forms.

## Find the cPanel destination before uploading

The repository's deployment documentation identifies the frontend deployment
as the contents of `frontend/dist`, but this project does not record the
document-root path in your cPanel account. Do not assume it is `public_html`.

1. Sign in to cPanel and open **Domains**.
2. Find `infinityhouseproperties.com` and read its **Document Root**.
3. Confirm that directory is the one currently serving the site's built
   frontend (the directory containing the deployed `index.html` and assets).
4. If the domain is configured as a proxy or points elsewhere, confirm the
   web server serves these files from that document root before uploading.

## Upload with cPanel File Manager

1. In cPanel, open **File Manager** and navigate to the confirmed document
   root from the previous section.
2. Upload `robots.txt` and `sitemap.xml` from this package directly into that
   root, alongside the deployed `index.html`. Do not upload the package
   directory as a subdirectory.
3. If either destination file already exists, inspect and back it up before
   replacing it; preserve any existing site-specific rules or sitemap entries
   that are still needed.
4. Do not upload application source files, `.env` files, API credentials,
   database data, or private media.

## Check after upload

Open these exact HTTPS URLs in a browser and confirm each returns the
corresponding text/XML file rather than the application page or a 404:

- `https://infinityhouseproperties.com/robots.txt`
- `https://infinityhouseproperties.com/sitemap.xml`

The sitemap must be valid XML, have a `urlset` root with the sitemap namespace,
and list canonical URLs on the intended HTTPS domain. A sitemap advertises
URLs; it does not guarantee indexing or make a page private.

To check robots behavior, inspect `/robots.txt` and use Google Search Console's
URL Inspection for the homepage and a public informational page. Confirm
Google can crawl each URL. Do not add `Disallow` rules for public property
pages or rendering assets. Protect management routes with application
authentication and authorization, not robots rules.

## Validate the sitemap locally

From the project root, run this PowerShell command (Python 3 required):

```powershell
python -c "import xml.etree.ElementTree as ET; ET.parse(r'google-indexing-package\sitemap.xml'); print('Sitemap XML is well-formed')"
```

For a schema-level check, use the official sitemap protocol documentation at
`https://www.sitemaps.org/protocol.html`. Google Search Console also reports
sitemap fetch and parsing issues after submission.

## Submit in Google Search Console

1. Add and verify the **Domain** or URL-prefix property for
   `https://infinityhouseproperties.com/` in Google Search Console.
2. In **Sitemaps**, submit `https://infinityhouseproperties.com/sitemap.xml`
   (or the `sitemap.xml` path, depending on the form).
3. Review the sitemap status and any discovered URL or fetch errors.
4. In **URL Inspection**, enter `https://infinityhouseproperties.com/`, run
   **Test Live URL**, and choose **Request Indexing** if the test succeeds.
5. Repeat URL Inspection for public pages as needed. Indexing and timing are
   determined by Google; these steps are requests, not a guarantee.

## Dynamic property pages

Property details are routed at `/properties/:slug`, fetched in the browser
from the public API, and rendered by a Vite/React single-page application.
The static sitemap cannot safely enumerate these URLs without current,
public-only listing data. It also cannot supply server-rendered property
content or per-property metadata. For reliable per-property crawlable HTML,
the smallest suitable next step is a prerender/SSR layer for public routes
that reads only currently published listings and emits each page's content,
metadata, and canonical URL; generate the property sitemap from that same
public data source. Do not add guessed or unpublished property URLs to this
static sitemap.
