# 운영 SEO 런타임 수정 — v2026.09.16.144

운영 frontend manifest에 SEO 활성화 값이 명시되지 않아 실제 운영이 `robots.txt: Disallow: /`, 빈 sitemap, 공개 페이지 `noindex,nofollow` 상태로 서비스되고 있었습니다.

이번 변경은 운영에만 `APP_BASE_URL=https://easy-scraping.com`, `SEO_INDEXING_ENABLED=true`를 명시합니다. 격리 Test 환경은 계속 전체 noindex를 유지합니다. Flux 반영 뒤 robots/sitemap/canonical/index 상태를 실제 운영에서 다시 검증해야 완료입니다.
