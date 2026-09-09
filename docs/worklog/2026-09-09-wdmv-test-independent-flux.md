# Moneyverse isolated staging reconciliation — 2026-09-09

## Why this change exists

`wdmv-test` was restored under the shared `apps` Flux Kustomization and a Deployment selector drift caused the entire application reconciliation set to fail. Staging must never be able to block Production reconciliation.

## Implemented design

- `staging/wdmv-test` is the source of truth for the isolated test stack.
- `clusters/minipc/wdmv-test.yaml` reconciles staging independently from the production `apps` Kustomization.
- Staging uses its own namespace, PostgreSQL database, generated application/database encryption credentials, internal API token, and resource quota.
- The only cross-namespace permission is read-only access to the named Production `ghcr-pull` credential so the private immutable test images can be pulled. Production application/database Secrets are neither readable nor copied.
- The bootstrap Job creates test-only credentials idempotently and keeps frontend credentials separated from DB/encryption credentials.
- GitHub validation renders Production and staging separately and fails if staging objects leak into the Production render.

## Validation performed before Git integration

- Production Kustomize render: PASS.
- Staging Kustomize render: PASS.
- Kubernetes server-side dry-run for staging objects: PASS.
- Kubernetes server-side dry-run for the independent Flux Kustomization: PASS.
- Namespace/database isolation check: PASS.
- Staging Secret bootstrap v4: PASS; five test-only Secrets created without printing values.
- PostgreSQL StatefulSet: 1/1 Ready.
- Test backend: 1/1 Ready.
- Test frontend: 1/1 Ready.
- Production `wdmvp` was not modified by the staging repair.

## Remaining release gate

The currently running test images are a historical immutable test SHA. The application repository still needs an authenticated workflow that builds immutable `-test` images for the exact candidate SHA and the QA automation must promote that exact SHA into this isolated stack before direct-play QA can PASS.
