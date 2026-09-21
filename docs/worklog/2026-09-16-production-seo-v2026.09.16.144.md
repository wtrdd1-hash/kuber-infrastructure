# Production SEO runtime fix — v2026.09.16.144

Production was serving `robots.txt: Disallow: /`, an empty sitemap, and `noindex,nofollow` on public pages because the frontend manifest did not explicitly enable the source-controlled SEO switch.

This change pins `APP_BASE_URL=https://easy-scraping.com` and `SEO_INDEXING_ENABLED=true` only in Production. The isolated Test environment remains globally noindex. Validation must verify rendered manifests and, after Flux reconciliation, the public robots/sitemap/canonical/index state.
