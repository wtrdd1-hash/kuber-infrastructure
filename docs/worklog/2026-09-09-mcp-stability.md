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
