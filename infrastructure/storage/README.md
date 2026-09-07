# Storage is a per-cluster choice

Two directories, and a cluster picks exactly one.

| | when |
|---|---|
| `rook/` | several machines with disks to spare. Ceph replicates across them, so a node can die without taking the data with it. |
| `local-path/` | one machine. A directory on a disk, handed out as PersistentVolumes. |

Rook on a single node is the wrong tool rather than a smaller version of the
right one: every replica lands on the same disk, so "three replicas" is three
copies that die together, and the operator, the mons and the OSDs cost memory
that the workloads wanted.

Point a cluster at one of them from `clusters/<name>/infrastructure-storage.yaml`.
Moving between them is a migration, not a switch: the volumes do not follow.
