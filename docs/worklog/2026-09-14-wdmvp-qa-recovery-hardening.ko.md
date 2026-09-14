# WDMVP QA 및 복구 보강 — v2026.09.14.78

날짜: 2026-09-14
브랜치: `fix/wdmvp-qa-recovery-v2026.09.14.78`
상태: 구현 / 운영 전 Test 클러스터 검증 필수

## 변경 사항

1. GitOps 자동 승격이 폐기된 비-v1 경로 대신 Test와 Production 모두 `/app-api/v1/shop/public-catalog`을 검증합니다.
2. Production 런타임은 `APP_BASE_URL=https://easy-scraping.com`, `SEO_INDEXING_ENABLED=true`를 명시하고, 격리 Test는 Test URL과 `SEO_INDEXING_ENABLED=false`를 명시합니다.
3. exact-SHA Production smoke에서 `X-Robots-Tag: noindex`가 남아 있으면 실패 처리합니다.
4. 시간별 백업은 원자적 공개, 체크섬, PostgreSQL archive 검사 후 최근 48개 복구 지점을 유지합니다.
5. 복구 검증은 실제 저장된 백업을 읽기 전용으로 사용하여 SHA-256과 최신성을 확인하고 격리 recovery DB에 전체 복원한 뒤 조회 가능 여부를 확인합니다.

## 안전 조건

- DB dump나 자격증명은 Git에 커밋하지 않습니다.
- recovery job의 백업 저장소는 읽기 전용입니다.
- Test/비운영 환경에서 manifest 렌더링, v1 API smoke, Test noindex, persisted dump 실제 복원이 검증되기 전에는 이 브랜치를 Production에 승격하지 않습니다.

## 필수 Test 검증

- `staging/wdmv-test`, `apps/wdmvp` manifest 렌더/검증;
- Test exact SHA 및 `/app-api/v1/shop/public-catalog` 확인;
- Test `X-Robots-Tag: noindex` 유지 확인;
- 격리 storage/DB로 비파괴 backup/recovery rehearsal;
- 작업 중 backend health 정상 확인;
- 모두 통과한 뒤에만 Production 승격.
