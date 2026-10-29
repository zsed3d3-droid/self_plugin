# 디자인 검증의 연결

1. 프로젝트의 핵심 과업과 성공 결과를 정하고 `DESIGN.md`에 정보 구조·공용 컨트롤·토큰·예외를 적습니다.
2. `plugins/scenario-ui-ux/skills/scenario-ui-ux/templates/`의 계약을 프로젝트에 맞춥니다. scope 경로, 실제 브라우저 명령과 입력 파일, 기록 위치를 지정합니다. 예제의 브라우저 스크립트는 직접 구현해야 하며, 템플릿 복사만으로 검증되지 않습니다.
3. DESIGN 본문과 계약의 상호 해시를 계산합니다. 템플릿의 해시 의미와 갱신 방법은 [원래 설정 안내](../plugins/scenario-ui-ux/skills/scenario-ui-ux/references/design-hooks.md)를 따릅니다. 이 연결을 끄거나 오래된 증거를 재사용하지 않습니다.
4. `install-design-hooks.py`를 실행합니다. 기존 설정은 보존하며 관리 파일 충돌은 실패합니다. 호스트 신뢰·권한은 자동으로 변경하지 않습니다.
5. `.design-hooks/design-hook.py --project . --event CI`로 명시적인 검증을 실행합니다. 최신 소스 해시에 연결한 실제 과업, 기대와 관찰, 새 캡처를 남깁니다.

검수는 정적 토큰 일치와 구조적인 UX 품질을 구분합니다. 실제 화면에서 첫 클릭, 포커스·키보드, 오류 복구, 지연 응답, 저장 결과, 모바일 읽기 흐름을 과업별로 확인합니다. 원인을 좁혀 수정하고 같은 입력·같은 경로로 재검증합니다. 선호가 확인되지 않았다면 사용자 만족을 통과로 만들지 않습니다.

개인 정책은 공개본에 없습니다. 계약의 `policy.required`를 true로 바꿀 때는 본인이 검토한 비공개 원본과 적용표를 모두 연결해야 합니다. 기본 예제의 optional 상태는 정책 검사 통과를 뜻하지 않습니다.

Codex Broker의 실제 시각 검수는 별도 로그인 전에는 사용할 수 없습니다. 선택적 critic은 미실행 사유를 남기며 required 검수가 불가능하면 gate가 실패합니다. 새로운 로그인이나 기존 인증 복사는 이 배포 과정에서 수행하지 않습니다.

실제 런타임·설정 지원 여부는 설치한 Codex/Claude 버전과 프로젝트 신뢰에 따라 확인해야 합니다. provider 용량 오류는 모델 응답 전 발생할 수 있으므로 프로젝트 PostToolUse만으로 해결할 수 없습니다. `capacity-retry`의 정책 구현과 실제 전달 활성화 상태를 구분합니다.

0.5.0부터 원천 적용 계약을 네 번째 가이드로 설치하고, 독립 검수 입력과 pipeline fingerprint에 그 해시를 연결합니다. 로컬 관리 가이드가 수정되면 설치기는 설정을 바꾸지 않고 거절합니다. 새 가이드를 연결한 수동·테스트 검증이 호스트 자동 Hook 발화를 의미하지 않습니다.

## Capacity native 예약 재개

`harness/capacity-retry/native_precheck.py`는 프로젝트 디자인 Hook과 별개다. 개발 환경에서는 기존 Orca1.4.230의 예약 shell precheck로 활성화했지만 공개 패키지 복사만으로 다른 환경에 설치되지는 않는다. `native-scope.example.json`은 실제 thread·terminal·account·rollout·개인 state 경로가 없는 자리표시자다. 실제 scope·상태·인증은 배포하지 않는다. Docker observer의 전달 비활성 상태도 유지한다.

provider가 쓴 구조화된 `server_overloaded` 이벤트와 정확한 용량 오류 문구만 새 재시도를 시작한다. 기준은 오류 발생시각+60초이며 예약 지연·앱 sleep 때문에 더 늦을 수 있다. 사용자 지시·멈춤·진행 중 작업·draft가 우선하고, 보내기 직전 scope·화면을 다시 확인하고, 기본 placeholder를 허용할 때 현재 host 버전도1.4.230인지 재확인한다. 읽기와 전송 전체는 atomic하지 않은 best-effort이며, 불명 전송을 새 요청으로 반복하지 않는다.

54개 검사는 fake clock·fake provider 이벤트·비공개 fake CLI 기반이다. 실제 예약 precheck 실행과 현재 작업에서0건 전송을 확인했지만, 실 capacity 장애를 주입하거나 복구 성공을 관찰하지는 않았다. scheduled 전용 wrapper는 항상 nonzero로 끝나 placeholder prompt를 건너뛴다. Orca의 수동 Run은 precheck를 우회하므로 사용하지 않는다. 버전별 설치·중지 방법과 검증 경계는 [native 안내](../harness/capacity-retry/README.md)를 따른다.
