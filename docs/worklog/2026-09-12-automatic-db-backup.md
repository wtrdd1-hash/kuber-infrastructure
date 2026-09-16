# Automatic Database Backup — v2026.09.12.1

Date: 2026-09-12
Status: implementation branch / test pending on cluster
Branch: `feat/v2026.09.12.1-auto-db-backup`

## Goal

Make the production PostgreSQL backup path self-checking instead of only producing dump files. The stored backup artifact must be checksummed, parseable by PostgreSQL, recent, and periodically restored into the isolated recovery database.

## Changes

1. `wdmvp-db-backup` continues to run hourly at `:17` Asia/Seoul.
2. Each dump is written to a `.partial` path first, validated with `pg_restore -l`, atomically published, then accompanied by a SHA-256 checksum.
3. The checksum is verified immediately before it is published.
4. Retention increases from 5 hourly restore points to 48 hourly restore points (two days).
5. Abandoned dump/checksum partials older than two hours are deleted.
6. `wdmvp-recovery-refresh` no longer creates a fresh one-off dump. It mounts the persisted backup directory read-only, selects the newest published dump, checks freshness, verifies SHA-256, checks the archive with `pg_restore -l`, restores that exact stored backup into `moneyverse_recovery`, and runs `SELECT 1`.

## Safety properties

- Backup and recovery CronJobs use `concurrencyPolicy: Forbid`.
- A backup is never published under its final filename until `pg_dump` and `pg_restore -l` succeed.
- Recovery reads the backup host path read-only.
- Recovery fails if the newest backup is more than two hours old.
- No database dump or database data is committed to Git.
- No new plaintext credentials are added to Git. Existing Kubernetes Secret references are reused.

## Validation required before production merge

- Render `apps/wdmvp` with Kustomize and confirm both CronJobs are valid.
- Apply the branch manifests to the test environment or a non-production namespace.
- Run one backup Job manually and confirm a `.dump` plus matching `.sha256` are created.
- Run one recovery refresh Job manually and confirm checksum validation, `pg_restore -l`, full restore, and `SELECT 1` all succeed.
- Confirm application backend remains healthy while both jobs run.
- Confirm the production `main` branch is not changed until the above checks pass.

## Internal update note

Update version: `v2026.09.12.1`

This version converts backup verification from “a dump file exists” into “the persisted dump can be restored into the recovery database.” Production promotion remains blocked until cluster-side test execution is completed.
