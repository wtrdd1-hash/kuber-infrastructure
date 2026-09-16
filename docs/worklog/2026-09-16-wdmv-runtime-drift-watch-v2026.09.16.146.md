# 2026-09-16 — Moneyverse runtime drift watchdog v2026.09.16.146

- Confirm the current GitOps desired Test and Production SHAs against public `/api/version`.
- Add an independent scheduled watchdog that detects persistent desired-vs-live SHA drift.
- Keep the watchdog read-only: it must not mutate Test or Production workloads.
- Verify Test noindex and public backend smoke only after the exact desired SHA is served.
- Record the current cluster-wide reconciliation incident without weakening release gates.
- Implemented `.github/workflows/wdmv-runtime-drift-watch.yml`; read-only, retries for about three minutes, then fails on persistent Test or Production SHA drift.
