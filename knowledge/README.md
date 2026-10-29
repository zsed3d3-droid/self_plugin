# 제품을 만들며 수리한 경험

공개본에는 **56개 assistant 경험 요약**을 포함합니다. 실제 사용자 채택·만족도 연구가 아닙니다. 원래 과업과 소스 검사, 가설, 검증도구 오류의 구분과 반례를 보존합니다. 화면·원본 보고서·제품 DB는 이 저장소에 없으므로 여기의 요약만으로 새 검증이 통과했다고 주장하지 않습니다.

새 작업에서 증상과 원인이 모두 맞는 사례만 고르고, 반례와 한계를 함께 읽은 뒤 같은 과업으로 확인합니다. `harness/evidence-memory`에 import할 경우 role은 assistant로 유지합니다. 자동 규칙 승격이나 의미 검색은 구현했다고 표시하지 않습니다.

| 제품 | 사례 수 |
|---|---|
| 001-proofline | 2 |
| 002-spine | 5 |
| 003-cadence | 8 |
| 004-offcut | 8 |
| 005-clearing | 8 |
| 006-looproom | 7 |
| 007-cueframe | 7 |
| 008-commonhour | 6 |
| 009-handoff | 5 |

## 사례 색인

- **001-proofline · proofline-context-identity-20261029** — `proofline-context-identity-20261029`
- **001-proofline · proofline-retention-workspace-20261029** — `proofline-retention-workspace-20261029`
- **002-spine · Spine 주기 1 | PNG 글자 누락·투영 이음선** — `spine-002-complete-v2-ux-cycle-01`
- **002-spine · Spine 주기 2 | 이력 열기와 편집 버전 혼동** — `spine-002-complete-v2-ux-cycle-02`
- **002-spine · Spine 주기 3 | 모바일 미리보기 왕복·Canvas PNG 불일치** — `spine-002-complete-v2-ux-cycle-03`
- **002-spine · Spine 주기 4 | 재시도 영수증이 다른 프로젝트·새 의도를 덮음** — `spine-002-complete-v2-ux-cycle-04`
- **002-spine · Spine 주기 5 | QA 누적으로 홈 작업이 묻힘·보관 복원 초점** — `spine-002-complete-v2-ux-cycle-05`
- **003-cadence · 장면 선택과 편집 맥락을 가까이 두기** — `cadence-003-complete-v1-experiment-01`
- **003-cadence · 최신본 열람과 초안 폐기를 구별하기** — `cadence-003-complete-v1-experiment-02`
- **003-cadence · 응답 불명 재시도의 입력 의도를 고정하기** — `cadence-003-complete-v1-experiment-03`
- **003-cadence · 완료 후 행동·링크 모양·파일 정체성을 맞추기** — `cadence-003-complete-v1-experiment-04`
- **003-cadence · 글자 수 대신 실제 출력 경계로 지원 범위를 정하기** — `cadence-003-complete-v1-experiment-05`
- **003-cadence · 강조 중 글자 좌표와 가독성을 보존하기** — `cadence-003-complete-v1-experiment-06`
- **003-cadence · 입력 버전과 표현 코드·결과 바이트를 함께 결속하기** — `cadence-003-complete-v1-experiment-07`
- **003-cadence · audit 숫자와 실제 배송 코드·도달성을 구분하기** — `cadence-003-complete-v1-experiment-08`
- **004-offcut · Offcut 사례 1 | 비례 SVG가 글자까지 늘림** — `offcut-004-complete-v1-experiment-01`
- **004-offcut · Offcut 사례 2 | A초안이 B주소의 저장공간을 덮음** — `offcut-004-complete-v1-experiment-02`
- **004-offcut · Offcut 사례 3 | 모바일 제목이 보조도구에 밀림** — `offcut-004-complete-v1-experiment-03`
- **004-offcut · Offcut 사례 4 | root 넘침0이어도 SVG 파일 글자는 잘림** — `offcut-004-complete-v1-experiment-04`
- **004-offcut · Offcut 사례 5 | 배포 뒤 같은 완료 요청이409** — `offcut-004-complete-v1-experiment-05`
- **004-offcut · Offcut 사례 6 | 보관 뒤 키보드 focus가 숨김 버튼으로 감** — `offcut-004-complete-v1-experiment-06`
- **004-offcut · Offcut 사례 7 | A4 재고2의 그림은01·목록은1.1.** — `offcut-004-complete-v1-experiment-07`
- **004-offcut · Offcut 사례 8 | 출력 과업보다 SVG/CSV 형식이 앞섬** — `offcut-004-complete-v1-experiment-08`
- **005-clearing · 레퍼런스 추천을 CSV 과업에 맞춰 고르기** — `clearing-005-complete-v1-experiment-01`
- **005-clearing · 빈 셀과 실제 ‘빈 값’ 문자열을 구별하기** — `clearing-005-complete-v1-experiment-02`
- **005-clearing · 늦은 응답과 읽기 설정의 소유권 지키기** — `clearing-005-complete-v1-experiment-03`
- **005-clearing · 보기 상태와 저장 출력 범위를 분리하기** — `clearing-005-complete-v1-experiment-04`
- **005-clearing · 앱 밖에서도 불변 원본·버전 파일을 식별하기** — `clearing-005-complete-v1-experiment-05`
- **005-clearing · 숨은 input의 테스트 실패와 실제 조작을 구분하기** — `clearing-005-complete-v1-experiment-06`
- **005-clearing · 다음 행동뿐 아니라 첫 데이터 행도 보이게 하기** — `clearing-005-complete-v1-experiment-07`
- **005-clearing · 완료 설명보다 파일 받기를 먼저 배치하기** — `clearing-005-complete-v1-experiment-08`
- **006-looproom · 늦은 가져오기 응답이 새 선택을 덮음** — `looproom-006-complete-v1-experiment-01`
- **006-looproom · 보관 응답이 제목과 오디오 identity를 갈라놓음** — `looproom-006-complete-v1-experiment-02`
- **006-looproom · 잘못된 시각을 둔 채 이전 유효 범위를 저장함** — `looproom-006-complete-v1-experiment-03`
- **006-looproom · 같은 음원의 늦은 저장 확인이 새 편집을 저장됨으로 표시** — `looproom-006-complete-v1-experiment-04`
- **006-looproom · 일반 저장 확인이 도구를60.59375px밀어냄** — `looproom-006-complete-v1-experiment-05`
- **006-looproom · 시작 라벨이 desktop/320에서 세로로 갈라짐** — `looproom-006-complete-v1-experiment-06`
- **006-looproom · 0.1초 구간에서 A/B hit target이 겹침** — `looproom-006-complete-v1-experiment-07`
- **007-cueframe · 분리 줄을 한꺼번에 만들던 메모리 증가** — `cueframe-007-complete-v1-experiment-01`
- **007-cueframe · UI build와 계산 의미를 구분** — `cueframe-007-complete-v1-experiment-02`
- **007-cueframe · 부분 preview를 보존하며 다시 완성** — `cueframe-007-complete-v1-experiment-03`
- **007-cueframe · Native BODY 경계와 앱의 focus 계약** — `cueframe-007-complete-v1-experiment-04`
- **007-cueframe · 글자 수와 실제 줄 높이는 다름** — `cueframe-007-complete-v1-experiment-05`
- **007-cueframe · 입력 직후 첫 More 클릭이 사라짐** — `cueframe-007-complete-v1-experiment-06`
- **007-cueframe · 긴 본문 끝에서도 Close를 보이게** — `cueframe-007-complete-v1-experiment-07`
- **008-commonhour · 저장 성공과 결과 화면의 값 동일성** — `commonhour-jsonb-value-equality`
- **008-commonhour · 모바일 비교 위치와 실제 글자 기하** — `commonhour-mobile-comparison-geometry`
- **008-commonhour · 확정한 뒤 파일 받기를 먼저** — `commonhour-file-first-result`
- **008-commonhour · 검색 글자와 확정 option의 소유권** — `commonhour-uncommitted-search`
- **008-commonhour · label 복귀가 popup을 다시 열던 회귀** — `commonhour-controlled-popup-intent`
- **008-commonhour · 완료 확인 뒤 옛 빨간 경고 제거** — `commonhour-confirmed-request-warning`

세부 원인·조치·반례·결과·한계: [assistant-ux-cases.json](assistant-ux-cases.json). 출처 해시: [sources.json](sources.json). 공개 배포 때 요약한 것이며 원래 데이터베이스의 경험 건수를 변경하거나 새로 적재하지 않았습니다.

## 009 Handoff에서 추가한5개 조건부 경험

저장본의 검토한 이름 보호, 버전 정렬 계약, 늦은 응답과 현재 보기 범위, 추가 전제조건의 표시, 시각의 사람용 표현을 추가했습니다. 기존51개 요약은 구조와 내용을 그대로 유지했습니다. 원래 실행·root 검토·적재 종료 근거를 읽어 수작업으로 요약했으며 이 배포가 제품·DB·복원을 다시 실행한 것은 아닙니다. 시각 가독성은 assistant의 추론이며 사용자 요구·채택이 아닙니다.

이 색인의56개는 알려진 제품 시리즈의 경험 수입니다. 별도 하네스4건이나 DB 전체 건수를 포함한다고 주장하지 않습니다. 과거 경험을 실제 조회한 뒤에도 보기 범위 문제가 재발했으므로 회수 성공을 자동 예방의 증거로 세지 않습니다. 원문·코드 조각·사진·실제 메모리/작업 ID·개인 경로·판단 이유는 새 요약에 담지 않았습니다.

- **009-handoff · 저장본에서 검토한 이름을 제안이 지움** — `handoff-reviewed-name-protection`
- **009-handoff · 다시 열 때 최신 저장본과 다른 버전이 선택됨** — `handoff-version-order-contract`
- **009-handoff · 현재 보관 보기와 늦은 목록 응답의 소유권** — `handoff-library-response-scope`
- **009-handoff · 입력 전제조건과 추가 동작의 표시 일치** — `handoff-create-prerequisite-affordance`
- **009-handoff · 저장 시각의 표시와 원본 기록을 분리** — `handoff-human-time-presentation`
