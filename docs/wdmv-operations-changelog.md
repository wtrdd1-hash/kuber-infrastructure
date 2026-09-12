# Woldeok Moneyverse Operations Changelog

## OPS-v2026.09.12.2 — Production self-healing

Date: 2026-09-12

### English

- Added explicit `restartPolicy: Always` to Production frontend and backend Deployments.
- Added startup probes so slow starts are tolerated before liveness enforcement begins.
- Added readiness probes so unhealthy pods stop receiving Service traffic.
- Added liveness probes so wedged frontend/backend processes are restarted automatically.
- Backend probes use `/health`; frontend probes use `/`.
- No database schema, data, credentials, image tags, or application business logic changed.
- GitOps validation for the backend Production manifest passed before this entry was written; frontend validation was still running at that instant and is checked separately before final verification.

### 한국어

- 운영 프론트엔드와 백엔드 Deployment에 `restartPolicy: Always`를 명시했습니다.
- 느린 기동 중에는 liveness 판정을 유예하도록 startup probe를 추가했습니다.
- 비정상 Pod가 Service 트래픽을 받지 않도록 readiness probe를 추가했습니다.
- 응답 불능 상태가 지속되면 컨테이너를 자동 재시작하도록 liveness probe를 추가했습니다.
- 백엔드는 `/health`, 프론트엔드는 `/`를 점검합니다.
- 데이터베이스 스키마·데이터·자격 증명·이미지 태그·비즈니스 로직은 변경하지 않았습니다.

## OPS-v2026.09.12.1 — Test self-healing gate

### English

- Added startup probes to the isolated Test frontend/backend Deployments.
- Existing Test readiness and liveness probes were retained.
- GitOps validation passed for both Test manifest commits before Production self-healing was applied.

### 한국어

- 격리 테스트 프론트엔드/백엔드 Deployment에 startup probe를 추가했습니다.
- 기존 readiness/liveness probe는 유지했습니다.
- 테스트 매니페스트 두 건의 GitOps 검증 성공을 확인한 뒤 운영 반영을 진행했습니다.
