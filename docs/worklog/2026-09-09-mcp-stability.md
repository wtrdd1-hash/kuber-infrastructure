# MCP stability hardening — 2026-09-09

## Goal
Persist the MiniPC MCP control plane in the Flux source of truth and reduce avoidable outages without weakening host-level safety limits.

## Findings
- `gpt-plugin` was restored manually and explicitly excluded from Flux reconcile/prune, so it could disappear again.
- The MCP server installs Python dependencies at container start and had no Kubernetes startup/readiness/liveness probes.
- `desktop-commander-agent` restarted after OAuth device codes expired. No persisted device session exists on the host yet.
- The agent used `@latest`, allowing an upstream release to change behavior without review.
- The official Desktop Commander v0.2.48 release includes remote-session persistence/socket fixes, so the agent is pinned to 0.2.48 pending a successful one-time device pairing.
- The core MCP server remains one replica because the current SSE implementation may keep session state in-process; horizontal replication requires verified session affinity/shared state first.

## Changes
- Added Flux-managed namespace, MCP Deployment/Service/Ingress, PDB, and Desktop Commander agent.
- Added startup/readiness/liveness probes and zero-unavailable rolling update policy for the core MCP server.
- Preserved 250m/512Mi requests and 4 CPU/4Gi limits for the core server.
- Added explicit resources for Desktop Commander and pinned it to 0.2.48.
- Removed `reconcile: disabled` / `prune: disabled` from the source-of-truth resources.

## Remaining risk / manual item
Desktop Commander remote access needs one successful OAuth device pairing before its persisted session can be reused. This is separate from the custom MiniPC MCP endpoint used by ChatGPT.

## Validation
Pending kustomize/server-side dry-run and isolated test deployment before merge to main.

## Staging validation
- Created isolated namespace `gpt-plugin-staging`.
- Deployment rolled out successfully with 1/1 Ready and 0 restarts.
- `/health` returned HTTP 200 from inside the staging pod.
- The staging run revealed that application startup launches the real DDNS worker; the staging namespace was immediately removed. Future isolated tests must disable DDNS in application code before repeating this deployment pattern.

## Security finding
- The current local MCP application contains a Cloudflare credential fallback in unversioned host-local source. Automated credential extraction/migration was intentionally not forced after the tool safety gate blocked credential handling.
- This remains a CRITICAL remediation item: remove the fallback, rotate the credential, and supply it through an encrypted Secret/SOPS path. Do not commit plaintext credentials.

## Gate status
- Core MCP Kubernetes manifest: staging rollout PASS.
- Health probe: PASS.
- GitOps source integration: pending branch commit/push and Flux reconciliation.
- Desktop Commander one-time OAuth pairing: MANUAL REVIEW REQUIRED.
- Secret migration/rotation: BLOCKED from automated handling; requires approved secure rotation/injection path.

## Finalization update
- PR #7 merged: GitOps persistence, probes/resources/PDB, pinned Desktop Commander remote package, EN/KO worklogs.
- PR #8 merged: corrected Desktop Commander rollout strategy to a valid single-agent RollingUpdate (`maxSurge: 0`, `maxUnavailable: 1`).
- PR #9 merged: disabled the optional Desktop Commander remote agent by default (`replicas: 0`) because interactive device pairing expiry caused repeated restarts; miniPC1/miniPC2 use the primary gpt-plugin MCP path and remain available.
- PR #10 merged: pinned validated Python runtime dependency versions and changed startup/liveness probes to TCP while retaining a more tolerant HTTP readiness probe to avoid false restarts during long-lived MCP/SSE traffic.
- Flux now owns and reconciles the `gpt-plugin` namespace/resources from `apps/minipc/gpt-plugin`; prior manual `reconcile/prune=disabled` locks were removed.
- Current primary MCP pod is healthy and accessible through both miniPC1 and miniPC2; latest observed pod restart count is 0.
- Isolated staging rollout reached Ready with `/health` HTTP 200 and restart count 0. The staging test also revealed that the application starts its DDNS worker automatically; isolated future staging must add an explicit `DDNS_ENABLED=false` path before repeating tests that could contact production DNS APIs.

## Remaining security issue (CRITICAL / manual credential action required)
The host-mounted MCP application source still contains a Cloudflare API credential as a fallback default in configuration code. The credential value was not printed, copied into Git, or exposed in this worklog. No existing Kubernetes Secret containing the required `CF_API_KEY` was found. Automated secret extraction/migration was intentionally not forced after the execution safety gate blocked handling the credential. Required follow-up: rotate the credential, create an approved SOPS/Kubernetes Secret, inject it by `secretKeyRef`, remove the source-code fallback, and then re-run staging/production validation.

## Final result
PASS WITH WARNINGS for MCP availability/stability hardening. GitOps ownership and runtime stability fixes are deployed. The hardcoded Cloudflare credential and staging DDNS isolation switch remain unresolved and must not be marked PASS.

## DDNS event-loop isolation follow-up
- Root cause of intermittent readiness timeout was traced to synchronous `sync_ddns()` calls running directly inside the async DDNS background loop every 60 seconds.
- The host-mounted MCP source was patched so background DDNS calls execute via `await asyncio.to_thread(...)`, preventing Cloudflare/public-IP HTTP I/O from blocking the FastAPI/MCP event loop.
- Added a `DDNS_ENABLED` runtime switch to the host-mounted FastAPI lifespan; production explicitly sets `DDNS_ENABLED=true`. Isolated staging must set it to `false` before startup.
- Source values/secrets were not copied into Git. Python syntax compilation passed for both patched files and rollback backups were created beside them.

## DDNS full-A reconciliation hardening
- DDNS now updates every Cloudflare A record whose content matches the previously cached public IPv4 address when the WAN address changes.
- Existing record attributes such as proxied and TTL are preserved.
- SPF TXT `ip4:<old-ip>` is updated to the new public IP.
- If any A/SPF update fails, the cached public IP is not advanced so the next scheduled run retries the incomplete reconciliation.
- Staging keeps DDNS disabled and a mocked regression test verified that matching A records and SPF are selected while unrelated A records are untouched.
- Cloudflare credentials are no longer expected in versioned source; the runtime reads a root-owned host secret file mounted read-only.
