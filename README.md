# kuber-fluxcd

**Everything a bare Kubernetes cluster is missing, delivered by Flux.**

`kubeadm` leaves you with an API server and nodes that will not go Ready: no CNI, no ingress,
no storage, no certificates. This repository is the other half — the platform, in the order it
has to arrive, reconciled from git.

It is the companion of [kuber-nixos-flakes](https://github.com/ridanit-ruma/kuber-nixos-flakes),
which builds the machines. That repository ends with a node that has joined; this one is what
makes the cluster useful.

> **Built for a four-node cluster of small x86 machines at home.** A working setup rather than
> a distribution: read it, take what you need, and expect to change the addresses.

---

## What arrives, and in what order

Flux applies three Kustomizations, each waiting on the one before it. The order is the whole
point — a certificate issuer with no ingress to answer challenges, or a workload asking for a
volume before Rook exists, fails on nothing more interesting than sequencing.

```
infrastructure-controllers   the operators themselves
   ├── Cilium                 CNI, kube-proxy replacement, LB IPAM
   ├── cert-manager           ACME
   ├── Traefik                ingress
   ├── Rook                   Ceph operator
   └── kubelet-csr-approver   signs the kubelet's serving certificates
        ↓ waits until Ready
infrastructure-configs       what those operators are told to build
   ├── CephCluster + block pool + CSI driver
   ├── ClusterIssuer          Let's Encrypt, DNS-01 through Cloudflare
   ├── Cilium LB IP pool
   └── cloudflared            outbound tunnel, if you use one
        ↓
apps                         everything the platform exists to serve
```

`kubelet-csr-approver` is the piece most clusters skip and then miss: without it the kubelet's
serving certificate is never signed, and `kubectl logs` and `kubectl top` fail against the node
with a TLS error that does not name the cause.

## Making it yours

Six values, and the repository will tell you where each of them lives.

| | |
|---|---|
| `.sops.yaml` | your age public key — the private half goes into the cluster as the `sops-age` secret and nowhere else |
| `infrastructure/controllers/kubelet-csr-approver.yaml` | the subnets your nodes are on |
| `infrastructure/configs/cilium-lb-ippool.yaml` | a range for load-balancer services, off every subnet in use |
| `infrastructure/configs/rook-ceph-cluster.yaml` | which node gives which disk, named by serial |
| `infrastructure/configs/cluster-issuer.yaml` | your DNS zone |
| `apps/` | your services, one directory each, listed in `apps/kustomization.yaml` |

Then point Flux at it:

```sh
flux bootstrap github \
  --owner=<you> --repository=kuber-fluxcd \
  --branch=main --path=clusters/<your-cluster> --personal
```

Bootstrap writes `clusters/<your-cluster>/flux-system/` itself — it is deliberately not in this
repository, because half of a `flux bootstrap` output is worse than none of it.

## Secrets

No secret is committed here in the clear, and none is committed at all: this repository carries
the shape, not the contents. `*.sops.yaml` files are encrypted with
[sops](https://github.com/getsops/sops) and age, with only `data` and `stringData` encrypted so
the surrounding manifest stays readable in review and in `git log`.

Two are needed before certificates work — a Cloudflare API token for cert-manager, and a tunnel
token if you use cloudflared. Both are documented where they are referenced.

## Storage, honestly

Rook takes whole disks, named by serial (`/dev/disk/by-id/...`) rather than by `nvme0n1`.
That is not fussiness: `nvme0n1` moved across a reboot on this cluster and pointed at the
system disk, and only Rook's refusal to touch a device with a partition table on it kept the
mistake from being carried out.

Three replicas across three hosts, failure domain `host`. A four-node cluster survives losing
one; it does not survive losing two.

## Thanks

The host-side preparation this repository depends on — what a machine has to do before Rook
will take one of its disks, and the ordering that gets containerd and the kubelet up in the
right sequence — started from [minco](https://github.com/mincomk)'s
[server-nixos-flakes](https://github.com/mincomk/server-nixos-flakes). Thank you.

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Woldeok Moneyverse automatic release reconciliation (v2026.09.12.13)

`wdmv-auto-reconcile.yml` checks the application repository on a five-minute GitHub Actions schedule. It promotes only the latest successful `main` Test Candidate SHA into the isolated `wdmv-test` manifests. Production is changed only when the application repository has emitted a successful `production-ready` deployment for that same SHA and the exact SHA plus backend/database smoke path are still healthy on `test.easy-scraping.com`.

The workflow writes only GitOps image/source references. Flux remains responsible for cluster mutation. Test (`wdmv-test`) and Production (`wdmvp`) keep separate namespaces and PostgreSQL databases. Production post-reconcile smoke requires the exact SHA on `easy-scraping.com`, `/status`, and the public catalog backend/database path.
