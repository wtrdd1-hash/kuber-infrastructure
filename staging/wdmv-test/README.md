# Woldeok Moneyverse test stack

This directory is the isolated pre-production environment for `test.easy-scraping.com`.

## Isolation contract

- Namespace: `wdmv-test`; production remains `wdmvp`.
- PostgreSQL: a dedicated StatefulSet and 5 GiB PVC; it never points at `wdmvp-db`.
- Application/database credentials: generated inside the test namespace and never copied from Production.
- Frontend credentials: a separate reduced Secret; the frontend does not receive the test database password.
- GHCR: the bootstrap ServiceAccount may read exactly the Production `ghcr-pull` Secret so the private test images can be pulled. It cannot read other Production Secrets.
- ResourceQuota/LimitRange bounds the test stack so QA cannot consume the whole single-node cluster.
- Ads and Search indexing remain disabled on the test origin.
- Discord interactions/outbox are disabled so staging cannot emit Production community side effects.

## Secret bootstrap

The bootstrap Job runs as a non-root, read-only-root-filesystem container and uses the Pod's short-lived ServiceAccount credentials to call the Kubernetes API. The implementation uses Python standard-library HTTPS/JSON primitives only; it does not install packages at runtime and does not scrape API JSON with shell text tools.

The ServiceAccount can create/get Secrets only in `wdmv-test`. A separate `wdmvp` Role allows `get` on the single `ghcr-pull` Secret so the registry credential can be copied into the test namespace. Production application and database Secrets remain inaccessible.

## Candidate pinning

Backend image, frontend image, and migration source must identify the same application commit. A candidate is not eligible for application `main` or Production merely because the images build. The test namespace must run that exact candidate and pass the relevant database, health, user-flow, security, responsive/accessibility, and SEO/noindex checks first.

## Database startup

On a fresh PVC the PostgreSQL entrypoint downloads the public application source archive pinned to the candidate SHA and runs the repository's `000-create-app-role.sh` and `001-economy-core.sql`. Before the backend starts, an init container downloads the same candidate source and runs `packages/database/migrate.sh` plus `deploy/seed.sh` as `moneyverse_migrator`.

This preserves the application's existing immutable migration checksum contract. The backend itself still connects only as `moneyverse_app`.

## Updating a candidate

1. Build successful `-test` backend/frontend images for the candidate SHA.
2. Change the backend image, frontend image, `TEST_SOURCE_SHA`, and candidate labels together.
3. Run the GitOps validation workflow.
4. Reconcile the isolated test Kustomization without adding it to the shared Production `apps` Kustomization.
5. Verify the namespace is Ready and that `test.easy-scraping.com` serves the exact candidate.
6. Run QA. Do not promote the application candidate if any mandatory gate fails.
