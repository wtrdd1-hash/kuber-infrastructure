# Moneyverse staging bootstrap repair — 2026-09-09

## Scope

Repair the isolated `wdmv-test` secret bootstrap after candidate deployment was blocked by helper-image/runtime-tool incompatibilities. Production application/database resources are out of scope and must remain unchanged.

## Root cause

The staging bootstrap path depended on shell utilities supplied by a helper image. Earlier attempts encountered incompatible `wget` options and then runtime package-install assumptions that conflicted with the non-root/read-only security contract. This made credential provisioning image-dependent and prevented the test namespace from becoming healthy.

## Change

- Replace shell/curl/JSON text scraping with Python standard-library HTTPS and JSON handling.
- Generate test-only random credentials with `secrets.token_hex`.
- Reuse the Pod's projected ServiceAccount identity and cluster CA.
- Keep least-privilege RBAC: create/get Secrets only in `wdmv-test`; read only `wdmvp/ghcr-pull` across namespaces.
- Copy only `.dockerconfigjson` from the Production registry Secret; never copy Production application/database credentials.
- Preserve non-root execution, dropped capabilities, read-only root filesystem, and bounded resources.
- Add a memory-backed `/tmp` for the helper runtime without making the image filesystem writable.

## References

- Kubernetes Service Accounts documentation: Pod-assigned ServiceAccounts receive short-lived projected credentials and cross-namespace access can be scoped with Role/RoleBinding.
- Kubernetes Images documentation: private-registry `imagePullSecrets` must be in the same namespace as the Pod and use Docker config Secret types.
- Kubernetes projected volume guidance supports short-lived ServiceAccount token projection rather than long-lived static credentials.

## Validation / promotion state

GitOps render/isolation CI is required on this branch. Direct cluster validation is still required before declaring the blocker fixed because the authorized remote mini PC is currently unavailable. Do not merge this infrastructure repair or promote the application candidate to Production until the real `wdmv-test` namespace boots and exact-candidate QA passes.
