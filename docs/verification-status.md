# 배포 검증 상태 · 2026-10-29

이 파일은 공개 패키징 시 실행한 범위입니다. 원래 제품의 검증 결과를 새 설치의 검증으로 대신하지 않습니다.

| 항목 | 실제 결과 |
|---|---|
| 설치·라우팅·컨테이너 계약·판단 동기화·레퍼런스 단위 검사 | 43 tests 통과 |
| DESIGN Hook | 초기35, 0.5.0에서 새 가이드 설치·변조 검사를 포함한36 tests 통과 |
| UX 저자 판단 선택기 | 14 tests 통과 |
| 결과물 보존 도구 | 24 tests 통과. synthetic 파일·가짜 Docker 어댑터 |
| Capacity 정책·native 어댑터 | 54 tests 통과. fake clock·provider 이벤트·비공개 fake CLI로 deadline·scope·draft·중복·모호한 receipt 경계 확인 |
| 기존 LBS / Plain Writing / Unbox 패키지 | 각각 7 / 2 / 2 tests 통과 |
| 프로젝트 설치 smoke | 유효한 템플릿 계약 로드·9개 wrapper·양쪽 호스트 PostToolUse/Stop 각1개 생성 확인 |
| Feedback / Memory 재사용 서비스 | 두 Docker 이미지 실제 빌드·기동·health 확인. 10 tests 통과 |
| Memory 실제 API | 인증 거절·적재·중복 방지·scope 분리·정정·검색 제외/복구·DB/API 재시작 보존 확인 |
| Feedback 실제 서비스 | 공개 연구 10명/30개 후보. 초기 사용자 판단0건 확인 |
| 공개 파일 검사 | Git에 포함될 경로·고신뢰 비밀 패턴·개인 경로·marketplace 7개 소스 확인. 발견사항0. 최종 push 전 재실행 |

처음 root 단위 검사는 기본 Python에 PyYAML이 없어 import에 실패했습니다. 이미 PyYAML6.0.3/pytest9.2.0이 설치된 개발 환경에서 43개 전체를 재실행해 통과했습니다. 첫 smoke의 macOS `/var` 임시 경로가 canonical 경로가 아니어 거절됐으며, resolved 경로로 같은 smoke를 재실행해 통과했습니다. 제품 결함으로 계산하지 않습니다. 개인 예제를 일반화한 뒤 연구 import 해시가 달라진 검사도 해당 공개 연구 파일의 실제 해시로 갱신해 같은14개 검사를 재실행·통과했습니다. upstream JavaFX의 `/Users/me`는 일반적인 잘못된 경로 사용 예제이며 개인 주소가 아닙니다.

## 완료로 표시하지 않는 항목

- **Native 디자인 Hook 자동 발화:** 프로젝트 설정은 생성하지만 호스트 신뢰는 자동 승인하지 않습니다. 위 smoke는 설정 생성 확인입니다.
- **실제 LLM 시각 검수:** 전용 Codex Broker 로그인을 건너뛴 상태입니다. API/가짜 실행기 검증과 실제 모델 추론은 다릅니다.
- **실제 용량 오류 복구:** 개발 환경에서는 기존 Orca의 1분 예약 shell precheck로 native 자동 재개를 활성화했습니다. Docker observer는 계속 관찰 전용이며 전달은 비활성입니다. 최종 어댑터 변경 후 예약 실행2회가 `skipped_precheck`로 끝났고 agent 생성·dispatch·현재 root prompt 전송은0건입니다. 실제 capacity 오류를 주입하거나 복구를 관찰하지 않았으므로 실오류 복구 성공은 미검증입니다. Orca1.4.230·Codex CLI0.165.0에서 확인한 결과이며 clone에 native 설정이나 개인 scope를 복제하지 않습니다. 새 host daemon·cron·launchd는 만들지 않았습니다. 자세한 범위는 [VALIDATION](../harness/capacity-retry/VALIDATION.json)에 있습니다.
- **Broker 독립 배포본:** 원래 구현 소스·테스트를 유지한 Compose 패키지입니다. 이 공개 패키징에서 추가 Broker 컨테이너 로그인·실제 모델 호출을 하지 않았습니다. 새 Compose는 임시 자리표시자 환경으로 구문 검사를 통과했습니다. 실제 인증은 생성하거나 연결하지 않았습니다.
- **의미 검색·선호 자동 학습:** Memory는 PostgreSQL 어휘 검색입니다. 51개 공개 사례는 assistant 경험 요약이며 사용자 채택이 아닙니다.
- **실제 제품 백업:** 제품과 DB는 이 저장소에 포함하지 않습니다. 소스 보존 도구의 tests가 제품 전체 복원 검증을 의미하지 않습니다.

로컬 데모는 `http://127.0.0.1:8851`(규칙 검토), `http://127.0.0.1:8852/health`(근거 기억)입니다. 상태는 이 개발 환경에서 확인한 시점의 결과이며 clone만으로 실행되지 않습니다.

고정 upstream의 원래 공백을 보존하기 위해 해당 snapshot 경로만 whitespace 검사에서 제외합니다. 자체 배포 파일의 staged whitespace 검사는 별도로 통과시킵니다.

## 0.5.0 원천 갭 보완 · 별도 공개 컨테이너

공개 Interaction8871은 새 이미지 빌드 후20개 과업 검사·25개 캡처를 확인했습니다. 공개 Anti-slop8873은9조건·30개 캡처와 검색 후 선택 유지 검사를 확인했습니다. 공개 Motion Canvas8872는 실제 native 프레임0/150/299·반복 출력·재생/정지·모션 감소·작은 화면·PNG POST/GET과 새 볼륨의8개 파일 재시작 보존을 확인했습니다. 원래 실험의 UI 바이트는 유지하고 출판용 포트·helper·Origin·결과 경로만 구분했습니다.

원래 실험에서 발견한 Animate.css 중복 완료, GSAP 배포 고지 누락, 검색 뒤 작업공간 초기화, Motion Canvas 폰트 프레임 차이와 작은 화면 설명을 좁게 수정하고 같은 과업을 재검증했습니다. 중복 좌표를 더한 geometry probe는 검증 도구 결함으로 따로 기록했습니다. 각 lab의 VERIFICATION.json과 WHY를 참고하세요. 이것은 제품 채택이나 사람의 선호·속도·FPS 우위를 뜻하지 않습니다.
