# Woldeok Moneyverse Internal Operations Record

> This file contains operational notes only. Do not place credentials, secret values, private keys, database dumps, member data, or recovery tokens here.

## OPS-v2026.09.12.2

### English

Incident: the public site was reported unavailable on 2026-09-12.

Observed during response:
- The authorized minipc remote agent was offline, so direct `kubectl` inspection was not available from the operator session.
- The public homepage became reachable again during the response.
- Production frontend/backend manifests had no Kubernetes startup, readiness, or liveness probes.
- Test already had readiness/liveness probes; startup probes were added there first and GitOps validation passed.

Mitigation:
- Production frontend/backend now explicitly use `restartPolicy: Always`.
- Startup/readiness/liveness probes are declared for both application Deployments.
- The change is GitOps-managed through `wtrdd1-hash/kuber-infrastructure`; no imperative `kubectl set image` drift was introduced.

Remaining host-level gap:
- Kubernetes self-healing cannot recover a physically powered-off, suspended, network-isolated, or kubelet-dead single node.
- Host-level power/suspend and kubelet/cloudflared restart policy must be verified on minipc when the remote agent is online.

### 한국어

장애: 2026-09-12 공개 사이트 접속 불가가 보고되었습니다.

대응 중 확인:
- 미니PC 원격 에이전트가 오프라인이라 현재 세션에서 직접 `kubectl` 점검은 할 수 없었습니다.
- 대응 중 공개 홈페이지는 다시 접속 가능한 상태가 되었습니다.
- 운영 프론트엔드/백엔드 매니페스트에는 Kubernetes startup/readiness/liveness probe가 없었습니다.
- 테스트 환경에는 readiness/liveness가 이미 있었고 startup probe를 먼저 추가한 뒤 GitOps 검증 성공을 확인했습니다.

조치:
- 운영 프론트엔드/백엔드에 `restartPolicy: Always`를 명시했습니다.
- 두 Deployment 모두 startup/readiness/liveness probe를 추가했습니다.
- 변경은 `wtrdd1-hash/kuber-infrastructure`의 GitOps 선언으로 관리하며 임시 `kubectl set image` 드리프트는 만들지 않았습니다.

남은 호스트 수준 항목:
- 단일 노드 자체가 전원 종료·절전·네트워크 단절되거나 kubelet이 중단되면 Kubernetes의 Pod 자가복구만으로는 복구할 수 없습니다.
- 미니PC 원격 에이전트가 다시 온라인이 되면 절전 방지와 kubelet/cloudflared 자동 재시작 정책을 실서버에서 확인해야 합니다.
