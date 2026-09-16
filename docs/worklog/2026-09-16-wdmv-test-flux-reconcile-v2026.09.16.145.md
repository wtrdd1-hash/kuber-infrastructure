# 2026-09-16 — WDMV Test Flux reconcile recovery v2026.09.16.145

- Public Test remained on application SHA `73588498...` while GitOps main pinned newer validated candidates through `cef23d5...`.
- Make the nested Test Kustomization explicitly unsuspended and request a fresh reconciliation.
- Keep Production manifests unchanged.
- Validate rendered staging and cluster definitions before merge.
