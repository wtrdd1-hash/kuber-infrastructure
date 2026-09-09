# MCP 안정성 강화 — 2026-09-09

## 목표
MiniPC MCP 제어 계층을 Flux 소스 오브 트루스에 영속화하고, 호스트 전체 안전 제한을 제거하지 않으면서 불필요한 장애를 줄인다.

## 확인된 문제
- `gpt-plugin`은 수동 복구 상태였고 Flux reconcile/prune이 비활성화되어 재부팅·정리 후 다시 사라질 수 있었다.
- MCP 서버는 컨테이너 시작 때마다 Python 의존성을 설치했고 startup/readiness/liveness probe가 없었다.
- `desktop-commander-agent`는 OAuth device code 만료로 반복 재시작했다. 아직 호스트에 영속 device session이 없다.
- Desktop Commander가 `@latest`를 사용해 upstream 변경이 검증 없이 반영될 수 있었다.
- 최신 공식 v0.2.48에는 remote session persistence/socket 관련 수정이 있어 0.2.48로 고정했다.
- 현재 SSE 구현은 프로세스 내 세션 상태를 가질 수 있어 검증 없이 2 replicas로 늘리지 않았다.

## 변경
- Flux 관리 Namespace, MCP Deployment/Service/Ingress, PDB, Desktop Commander agent를 추가했다.
- MCP 서버에 startup/readiness/liveness probe와 maxUnavailable=0 롤링 정책을 추가했다.
- MCP 서버 request 250m/512Mi, limit 4 CPU/4Gi를 유지했다.
- Desktop Commander에 명시적 리소스를 추가하고 0.2.48로 고정했다.
- 소스 리소스에서 reconcile/prune disabled 설정을 제거했다.

## 테스트
- 격리 네임스페이스 `gpt-plugin-staging`에서 MCP 서버 rollout 성공.
- Pod 1/1 Ready, restart 0 확인.
- 내부 `/health` HTTP 200 확인.
- Kustomize 렌더링 및 client dry-run PASS.
- 스테이징 기동 시 실제 DDNS worker가 시작되는 부작용을 발견해 즉시 스테이징을 제거했다. 향후 별도 테스트에서는 DDNS 비활성화 기능이 필요하다.

## 보안/수동 항목
- 현재 Git 밖의 MCP 로컬 소스에 Cloudflare 자격증명 fallback이 존재한다. 평문을 Git에 옮기지 않았으며 자동 Secret 추출/이관은 안전 검사에서 차단되어 강행하지 않았다.
- 해당 자격증명은 회전 후 SOPS/Kubernetes Secret으로 주입하고 코드 fallback을 제거해야 한다.
- Desktop Commander 원격 기능은 1회 OAuth device pairing이 완료되어야 v0.2.48의 영속 세션 재사용을 검증할 수 있다.

## 최종 반영 업데이트
- PR #7 병합: MCP GitOps 영속화, 프로브/리소스/PDB, Desktop Commander 버전 고정, 영문/한글 작업기록 추가.
- PR #8 병합: Desktop Commander 배포 전략을 유효한 단일 에이전트 RollingUpdate(`maxSurge: 0`, `maxUnavailable: 1`)로 수정.
- PR #9 병합: 대화형 기기 인증 만료 때문에 반복 재시작하던 선택적 Desktop Commander 원격 에이전트를 기본 비활성화(`replicas: 0`). miniPC1/miniPC2는 핵심 gpt-plugin MCP 경로를 사용하므로 계속 사용 가능.
- PR #10 병합: 검증된 Python 런타임 의존성 버전 고정, 장시간 MCP/SSE 트래픽에서 오탐 재시작을 줄이기 위해 startup/liveness는 TCP, readiness는 여유 있는 HTTP 프로브로 조정.
- Flux가 `apps/minipc/gpt-plugin`의 네임스페이스/리소스를 실제로 소유·동기화하도록 전환했고, 과거 수동 `reconcile/prune=disabled` 잠금을 제거함.
- 현재 핵심 MCP Pod는 miniPC1/miniPC2 양쪽에서 접근 가능하며 최근 확인 재시작 횟수는 0회.
- 격리 staging에서 Ready, `/health` HTTP 200, 재시작 0회를 확인함. 단 staging에서도 DDNS worker가 자동 시작되는 사실을 발견했으므로 향후 격리 테스트 전 `DDNS_ENABLED=false` 같은 명시적 비활성 경로가 필요함.

## 남은 보안 문제 (CRITICAL / 수동 자격증명 조치 필요)
호스트에 마운트된 MCP 애플리케이션 설정 코드에 Cloudflare API 자격증명이 fallback 기본값으로 남아 있음. 해당 값은 출력·Git 기록·작업기록에 노출하지 않았으며, 현재 클러스터에는 재사용 가능한 `CF_API_KEY` Kubernetes Secret이 없음. 실행 안전 게이트가 자격증명 자동 추출/이관을 차단한 뒤 이를 우회하지 않았음. 필수 후속조치: 자격증명 회전 → 승인된 SOPS/Kubernetes Secret 생성 → `secretKeyRef` 주입 → 소스 fallback 제거 → staging/운영 재검증.

## 최종 결과
MCP 가용성/안정성 강화는 PASS WITH WARNINGS. GitOps 영속화와 런타임 안정화는 운영 반영 완료. Cloudflare 하드코딩 자격증명과 staging DDNS 격리 스위치는 미해결이며 PASS로 기록하지 않음.

## DDNS 이벤트 루프 격리 후속조치
- 간헐적 readiness timeout의 원인을 60초마다 async DDNS 루프 내부에서 동기식 `sync_ddns()`를 직접 실행해 FastAPI/MCP 이벤트 루프를 막는 구조로 확인함.
- 호스트 마운트 MCP 소스를 수정해 백그라운드 DDNS 호출을 `await asyncio.to_thread(...)`로 실행하도록 변경하여 Cloudflare/공인 IP HTTP I/O가 MCP 이벤트 루프를 차단하지 않도록 함.
- FastAPI lifespan에 `DDNS_ENABLED` 런타임 스위치를 추가했고 운영은 `DDNS_ENABLED=true`를 명시. 향후 격리 staging에서는 시작 전 반드시 `false`로 설정해야 함.
- Secret 값은 Git으로 복사하지 않았으며 수정된 두 Python 파일 모두 문법 컴파일 검증 PASS. 롤백용 백업 파일도 호스트에 생성함.

## DDNS 전체 A 레코드 동기화 강화
- 외부 공인 IPv4가 변경되면 이전 공인 IP를 가리키는 Cloudflare의 모든 A 레코드를 새 IP로 갱신하도록 변경했습니다.
- 각 레코드의 proxied/TTL 속성은 그대로 보존합니다.
- SPF TXT의 `ip4:<이전IP>`도 새 공인 IP로 갱신합니다.
- A/SPF 갱신 중 하나라도 실패하면 공인 IP 캐시를 전진시키지 않아 다음 주기에 자동 재시도합니다.
- staging에서는 DDNS를 비활성화하고 모의 회귀 테스트로 대상 A/SPF만 선택되고 관계없는 A 레코드는 변경하지 않는 것을 검증했습니다.
- Cloudflare 자격증명은 버전 관리 소스에 포함하지 않고 root 소유 read-only 비밀파일을 런타임에 마운트하도록 정리했습니다.
