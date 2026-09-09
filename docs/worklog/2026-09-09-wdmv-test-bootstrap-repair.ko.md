# Moneyverse 테스트 bootstrap 복구 — 2026-09-09

## 범위

후보 배포가 helper image/runtime tool 호환성 문제로 막힌 `wdmv-test` Secret bootstrap을 복구합니다. Production 애플리케이션/DB 자원은 변경 대상이 아니며 그대로 유지해야 합니다.

## 원인

기존 staging bootstrap은 helper image가 제공하는 shell utility에 의존했습니다. 이전 시도에서 `wget` 옵션 호환성 문제와 non-root/read-only 보안 계약에 맞지 않는 runtime package 설치 가정이 연속으로 발생했습니다. 그 결과 자격증명 생성이 helper image 구현에 종속되어 테스트 namespace가 정상 기동하지 못했습니다.

## 변경

- shell/curl/JSON 문자열 파싱을 Python 표준 라이브러리 기반 HTTPS/JSON 처리로 교체합니다.
- `secrets.token_hex`로 테스트 전용 임의 자격증명을 생성합니다.
- Pod의 projected ServiceAccount identity와 cluster CA를 그대로 사용합니다.
- 최소권한 RBAC를 유지합니다: `wdmv-test`에서는 Secret create/get만, namespace 간에는 `wdmvp/ghcr-pull` 하나만 읽습니다.
- Production registry Secret에서는 `.dockerconfigjson`만 복사하고 Production 앱/DB 자격증명은 복사하지 않습니다.
- non-root 실행, capability 전체 제거, read-only root filesystem, 자원 제한을 유지합니다.
- helper runtime이 쓸 수 있도록 메모리 기반 `/tmp`만 제공합니다.

## 근거

Kubernetes 공식 문서에 따라 Pod에 지정한 ServiceAccount의 단기 projected credential을 사용하고, namespace 간 접근은 Role/RoleBinding으로 필요한 자원만 허용합니다. Private registry image pull Secret은 해당 Pod와 같은 namespace에 있어야 하므로 registry credential만 테스트 namespace로 제한 복제합니다.

## 검증 / 승격 상태

이 브랜치에서 GitOps render/isolation CI가 필수입니다. 현재 승인된 원격 미니PC가 연결되지 않아 실제 cluster 검증은 아직 필요합니다. 실제 `wdmv-test`가 정상 기동하고 exact-candidate QA를 통과하기 전에는 이 인프라 수정 병합이나 애플리케이션 Production 승격을 완료로 처리하지 않습니다.
