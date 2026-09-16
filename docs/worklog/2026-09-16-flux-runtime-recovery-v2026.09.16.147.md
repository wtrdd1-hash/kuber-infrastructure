# WDMV Flux Runtime Recovery v2026.09.16.147

## Objective
Restore the broken GitOps control path between `wtrdd1-hash/kuber-infrastructure` and the live minipc Kubernetes runtime without bypassing GitOps application state.

## Evidence before change
- Test live `/api/version`: `73588498f784421ebf87b4bd7246f306df9af81d`.
- Production live `/api/version`: `104573a8faec6e622bdc36f65f109ba39896db7c`.
- GitOps `main` points to newer immutable WDMV images, so both environments are in runtime drift.
- The application repository history shows existing deployment SSH secrets: `DEPLOY_HOST`, `DEPLOY_PORT`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, and `DEPLOY_KNOWN_HOSTS`.
- The currently reachable development host has no kubeconfig or Kubernetes SSH private key, so recovery must use the existing GitHub Actions SSH control path.

## Recovery plan
- [x] Reconfirm runtime drift.
- [x] Reconfirm current Flux source declaration targets this repository `main`.
- [x] Identify the pre-existing GitHub Actions SSH credential path.
- [ ] Add a fail-closed recovery workflow that uses those credentials without printing secret values.
- [ ] Detect the remote Kubernetes CLI without assuming the host OS.
- [ ] Patch only the Flux `GitRepository` source contract and force reconciliation.
- [ ] Restart Flux source/kustomize controllers only when the Kubernetes API is reachable through the authorized host.
- [ ] Reconcile `flux-system`, `wdmv-test`, and production `apps` declaratively.
- [ ] Verify Test converges before any application Production promotion.
- [ ] Record the exact recovery result and remaining blockers.

## Safety constraints
- Do not patch WDMV Deployment image tags imperatively.
- Do not mutate application databases or Secrets.
- Do not print SSH keys, registry credentials, kubeconfigs, or Secret data.
- Test must converge first. Production application promotion remains blocked until Test verification passes.
