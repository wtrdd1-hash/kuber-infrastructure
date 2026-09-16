# WDMV Flux 런타임 복구 v2026.09.16.147

## 목적
`wtrdd1-hash/kuber-infrastructure`와 실제 minipc Kubernetes 런타임 사이에서 끊긴 GitOps 제어 경로를 복구합니다. 애플리케이션 상태를 임시 `kubectl set image` 방식으로 덮어쓰지 않습니다.

## 변경 전 확인 증거
- Test 실제 `/api/version`: `73588498f784421ebf87b4bd7246f306df9af81d`.
- Production 실제 `/api/version`: `104573a8faec6e622bdc36f65f109ba39896db7c`.
- GitOps `main`은 더 새로운 immutable WDMV 이미지를 가리키므로 Test/Production 모두 runtime drift 상태입니다.
- 애플리케이션 저장소 과거 배포 이력에서 기존 SSH Secret 경로 `DEPLOY_HOST`, `DEPLOY_PORT`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`를 확인했습니다.
- 현재 접근 가능한 개발 호스트에는 kubeconfig나 Kubernetes SSH 개인키가 없어 기존 GitHub Actions SSH 제어 경로를 사용해야 합니다.

## 복구 순서
- [x] runtime drift 재확인.
- [x] 현재 Flux source 선언이 이 저장소 `main`을 가리키는지 재확인.
- [x] 기존 GitHub Actions SSH 인증 경로 확인.
- [ ] Secret 값을 출력하지 않는 fail-closed 복구 workflow 추가.
- [ ] 대상 OS를 가정하지 않고 원격 Kubernetes CLI 자동 탐지.
- [ ] Flux `GitRepository` source 계약만 교정하고 강제 reconcile.
- [ ] Kubernetes API 접근이 확인된 경우에만 Flux source/kustomize controller 재시작.
- [ ] `flux-system`, `wdmv-test`, production `apps`를 선언형으로 reconcile.
- [ ] 애플리케이션 Production 승격 전에 Test 수렴 검증.
- [ ] 복구 결과와 남은 차단 요소 기록.

## 안전 조건
- WDMV Deployment image tag를 imperative 방식으로 변경하지 않습니다.
- 애플리케이션 DB나 Secret 값을 수정하지 않습니다.
- SSH 키, registry credential, kubeconfig, Secret 데이터는 출력하지 않습니다.
- Test가 먼저 수렴해야 하며 그 전까지 Production 애플리케이션 승격은 차단합니다.
