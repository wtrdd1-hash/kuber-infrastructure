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
