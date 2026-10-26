import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const distRoot = resolve(frontendRoot, 'dist');
const indexingRoot = resolve(frontendRoot, '..', 'google-indexing-package');
const metadataPath = resolve(frontendRoot, 'seo-pages.json');
const metadata = JSON.parse(await readFile(metadataPath, 'utf8'));
const privateRoutes = JSON.parse(await readFile(resolve(frontendRoot, 'private-routes.json'), 'utf8'));
const entryPath = resolve(distRoot, 'index.html');
const entryHtml = await readFile(entryPath, 'utf8');
const privateRouteFallbackPath = resolve(distRoot, 'private-route-fallback.html');
await writeFile(privateRouteFallbackPath, createPrivateRouteHtml(entryHtml));

function escapeAttribute(value) {
  return value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;');
}

function setMetaContent(html, name, content) {
  const tagPattern = new RegExp(`<meta\\b(?=[^>]*\\bname="${name}")[^>]*>`, 'gi');
  const matches = html.match(tagPattern) ?? [];
  if (matches.length !== 1) {
    throw new Error(`Expected one ${name} metadata tag, found ${matches.length}`);
  }
  return html.replace(tagPattern, (tag) => {
    const contentPattern = /\bcontent="[^"]*"/i;
    if (!contentPattern.test(tag)) {
      throw new Error(`The ${name} metadata tag has no content attribute`);
    }
    return tag.replace(contentPattern, `content="${escapeAttribute(content)}"`);
  });
}

function setCanonical(html, canonical) {
  const canonicalPattern = /<link\b(?=[^>]*\brel="canonical")[^>]*>/gi;
  const matches = html.match(canonicalPattern) ?? [];
  if (matches.length > 1) {
    throw new Error(`Expected at most one canonical link, found ${matches.length}`);
  }
  const canonicalTag = `<link rel="canonical" href="${escapeAttribute(canonical)}" />`;
  if (matches.length === 1) return html.replace(canonicalPattern, canonicalTag);
  const closingHead = html.lastIndexOf('</head>');
  if (closingHead < 0) throw new Error('The built entry HTML has no closing head element');
  return `${html.slice(0, closingHead)}    ${canonicalTag}\n  ${html.slice(closingHead)}`;
}

function createRouteHtml(html, page) {
  const titlePattern = /<title>[\s\S]*?<\/title>/i;
  if (!titlePattern.test(html)) {
    throw new Error('The built entry HTML has no title element');
  }
  return setCanonical(
    setMetaContent(
      setMetaContent(
        html.replace(titlePattern, `<title>${page.title.replaceAll('&', '&amp;')}</title>`),
        'description',
        page.description,
      ),
      'robots',
      'index, follow',
    ),
    page.canonical,
  );
}

function createPrivateRouteHtml(html) {
  const noindexHtml = setMetaContent(html, 'robots', 'noindex, follow');
  return noindexHtml.replace(/<link\b(?=[^>]*\brel="canonical")[^>]*>/gi, '');
}

function routeDirectoryForPath(path) {
  if (typeof path !== 'string' || !path.startsWith('/')) {
    throw new Error(`Invalid prerender route path: ${path}`);
  }
  const routeSegments = path.split('/').filter(Boolean);
  if (routeSegments.some((segment) => segment === '.' || segment === '..')) {
    throw new Error(`Invalid prerender route path: ${path}`);
  }
  const routeDirectory = resolve(distRoot, ...routeSegments);
  if (!routeDirectory.startsWith(`${distRoot}${sep}`)) {
    throw new Error(`Prerender route is outside the build directory: ${path}`);
  }
  return routeDirectory;
}

for (const page of metadata) {
  const routeHtml = createRouteHtml(entryHtml, page);
  if (page.path === '/') {
    await writeFile(entryPath, routeHtml);
    continue;
  }

  const routeDirectory = routeDirectoryForPath(page.path);
  await mkdir(routeDirectory, { recursive: true });
  await writeFile(resolve(routeDirectory, 'index.html'), routeHtml);
}

for (const route of privateRoutes.paths) {
  const routeDirectory = routeDirectoryForPath(route);
  await mkdir(routeDirectory, { recursive: true });
  await writeFile(resolve(routeDirectory, 'index.html'), createPrivateRouteHtml(entryHtml));
}

const sitemapPath = resolve(indexingRoot, 'sitemap.xml');
const sitemap = await readFile(sitemapPath, 'utf8');
const sitemapUrls = [...sitemap.matchAll(/<loc>\s*(.*?)\s*<\/loc>/gs)].map((match) => match[1]);
const canonicalUrls = metadata.map((page) => page.canonical);
if (
  sitemapUrls.length !== canonicalUrls.length
  || new Set(sitemapUrls).size !== sitemapUrls.length
  || sitemapUrls.some((url, index) => url !== canonicalUrls[index])
) {
  throw new Error('The sitemap URLs must exactly match the public route canonicals in seo-pages.json');
}

await Promise.all(
  ['robots.txt', 'sitemap.xml'].map((filename) =>
    copyFile(resolve(indexingRoot, filename), resolve(distRoot, filename)),
  ),
);
