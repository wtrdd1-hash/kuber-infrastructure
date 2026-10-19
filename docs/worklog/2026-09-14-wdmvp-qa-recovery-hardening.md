# WDMVP QA and Recovery Hardening — v2026.09.14.78

Date: 2026-09-14
Branch: `fix/wdmvp-qa-recovery-v2026.09.14.78`
Status: implementation / Test-cluster validation required before Production

## Changes

1. GitOps auto-reconcile now verifies `/app-api/v1/shop/public-catalog` in both Test and Production instead of the retired non-v1 path.
2. Production runtime explicitly pins `APP_BASE_URL=https://easy-scraping.com` and `SEO_INDEXING_ENABLED=true`; isolated Test explicitly pins its Test base URL and `SEO_INDEXING_ENABLED=false`.
3. Production smoke fails if the exact-SHA runtime still returns `X-Robots-Tag: noindex`.
4. Hourly backup publication is atomic, checksummed, parse-checked and retains 48 restore points.
5. Recovery verification consumes the actual persisted backup read-only, verifies SHA-256 and staleness, restores it into the isolated recovery database and proves it is queryable.

## Safety

- No database dump or credential is committed to Git.
- The recovery job mounts backup storage read-only.
- Production is not promoted from this branch until Test/non-production validation proves the manifests render, the v1 API smoke passes, Test remains noindex, and a persisted dump restores successfully.

## Required Test validation

- render/validate `staging/wdmv-test` and `apps/wdmvp` manifests;
- confirm Test exact SHA and `/app-api/v1/shop/public-catalog`;
- confirm Test keeps `X-Robots-Tag: noindex`;
- run a non-production backup/recovery rehearsal against isolated storage/database;
- confirm backend health remains green;
- only then promote to Production.
