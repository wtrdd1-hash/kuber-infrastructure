# 2026-09-16 — Moneyverse 런타임 드리프트 감시 v2026.09.16.146

- 현재 GitOps의 Test/Production 목표 SHA와 공개 `/api/version`을 대조한다.
- 목표 SHA와 실제 SHA 불일치가 지속되면 실패시키는 독립 주기 감시를 추가한다.
- 감시는 읽기 전용으로 유지하며 Test/Production workload를 직접 변경하지 않는다.
- Test가 정확한 목표 SHA를 제공한 뒤 noindex 및 공개 백엔드 smoke를 확인한다.
- 릴리스 게이트를 약화하지 않고 현재 클러스터 전체 reconcile 장애를 기록한다.
- `.github/workflows/wdmv-runtime-drift-watch.yml`을 구현했다. 약 3분 재시도 후 Test 또는 Production SHA 불일치가 지속되면 fail-closed로 실패한다.
