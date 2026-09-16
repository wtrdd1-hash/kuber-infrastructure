# 2026-09-16 — WDMV Test Flux reconcile 복구 v2026.09.16.145

- GitOps main은 `cef23d5...`까지 최신 검증 후보를 가리키지만 공개 Test는 `73588498...`에 머물러 있었습니다.
- 중첩 Test Kustomization을 명시적으로 unsuspend하고 새 reconcile을 요청합니다.
- Production manifest는 변경하지 않습니다.
- 병합 전 staging 렌더링과 cluster 정의를 검증합니다.
