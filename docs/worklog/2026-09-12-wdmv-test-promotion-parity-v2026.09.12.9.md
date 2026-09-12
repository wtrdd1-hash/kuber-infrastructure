# WDMV test promotion parity — v2026.09.12.9

## Finding
The test promotion workflow updated the backend image/source SHA but left the frontend candidate label and fresh-test-database source SHA stale. This violated the staging contract requiring backend, frontend, migration source, and database bootstrap source to identify one exact application commit.

## Change
- Update both backend and frontend candidate labels during test promotion.
- Update the backend migration source SHA and PostgreSQL fresh-bootstrap source SHA together.
- Fail GitOps validation unless all six test candidate references resolve to one exact 40-character SHA.

## Validation
Run the repository GitOps validation workflow and a rendered staging manifest check before merging.

## Rollback
Revert this change. Existing running workloads are unchanged until a promotion PR is merged and Flux reconciles it.
