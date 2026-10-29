# UX 판단 레시피 색인

확인일: 2026-10-29. 10명·공개 원문 24개에서 20개 **조건부 후보**를 정리했다. 저자 보고와 우리의 적용 가설을 구분하며, 실제 제품 검증·사용자 승인은 아직 수행하지 않았다. 원문 권리는 저자에게 남고 자체 요약만 포함한다.

현재 증상에 맞는 한두 후보만 사용한다. 기존 사용자 판단의 이유와 좋아한 부분이 우선이다. 모든 저자의 철학을 한 화면에 혼합하지 않는다.

검색 예시는 [SKILL.md](../SKILL.md), 상세 출처와 수리·반례·실험은 [author-library.json](author-library.json)에 있다. 검색 결과의 점수는 어휘 일치 정도이며 품질·권위·사용자 선호 점수가 아니다.

## 증상에서 선택

| 증상 | 먼저 읽을 후보 | 핵심 질문 |
| --- | --- | --- |
| 조사·방법론 선택만 반복 | A-SD-1, A-SD-2 | 다음 결정을 바꿀 근거인가, 놓친 관점인가? |
| 구조 대안의 손익이 불명확 | A-IA-1 | 같은 과업을 서로 어떻게 다르게 돕는가? |
| 기능은 되지만 사용자가 싫어함 | A-IA-2, uxb-laurel-evidence-to-rule | 기능과 선호를 분리했으며 원문·범위를 보존했는가? |
| 모든 폼/패널 동시 노출 | uxb-nielsen-task-minimalism | 지금 필요한 정보와 접어도 다시 찾을 정보는 무엇인가? |
| 메뉴·달력·뒤로가기에서 길을 잃음 | uxb-norman-discovery | 행동을 찾고 취소·복귀할 수 있는가? |
| 회의→업무 전달 누락 | uxb-norman-activity, uxb-spool-find-to-outcome | 어느 전달·발견·완료 단계가 끊겼는가? |
| 비동기 상태·재시도·AI 결과가 모호 | A-DS-1, uxb-spool-two-party | 실제 실행 상태와 근거·책임이 분리돼 있는가? |
| 너무 큰 수리 또는 부실한 임시 실험 | A-DS-2, A-AB-1 | 국소 원인인가, 구조 원인인가, 되돌릴 수 있는가? |
| 생성 화면이 제품의 행동과 모순 | A-AB-2 | 기존 상태·위계·동선 계약을 지키는가? |
| 개인 검색·기억·세션 범위가 부정확 | A-LW-1, A-LW-2, uxb-nielsen-delegation | 질문의 종류·자료 근거·지속 범위를 구분했는가? |
| 기록이 쌓인 뒤 중단·복구가 불명확 | uxb-laurel-continuity | 보존·내보내기·철회 범위가 실제로 무엇인가? |
| 오류/완료 표현이 감정·빈도와 어긋남 | uxb-walter-tone | 다음 행동에 도움이 되는 표현인가? |
| 느린 연결·소형 기기에서 초안 유실 | uxb-walter-constraints | 실제 환경에서 어느 상태가 사라지는가? |

## Sarah Doody

공식 사이트: [Sarah Doody](https://www.sarahdoody.com/). 현재 직함은 규칙의 근거로 사용하지 않는다.

| 후보 | 적용할 상황 | 보존할 것 / 역효과 |
| --- | --- | --- |
| A-SD-1 · 다음 결정을 바꾸는 질문만 조사한다 | 명확한 수정인데 방법론 선택·레퍼런스 수집만 반복된다. | 필요한 위험 조사 · 명확한 사용자 요구 / 문제 자체가 불명확하거나 되돌리기 어려운 권한·데이터 변경은 조사 깊이를 유지한다. |
| A-SD-2 · 같은 화면을 다른 과업 관점으로 반박한다 | 만든 사람에게는 명확하지만 첫 진입·실패 복구가 비어 있다. | 실제 근거와 추정의 구분 / 사소한 CSS 수정에 근거 없는 persona 여러 개를 만들어 절차를 늘리지 않는다. |

공개 근거:
- [Designing With Lenses: See ideas through a different design lens](https://www.sarahdoody.com/designing-with-lenses/) · 2017-09-11 · `author_case_retrospective` · SD1
- [Are You Stuck In Research Mode?](https://www.sarahdoody.com/are-you-stuck-in-research-mode/) · 2016-01-23 · `reasoned_essay` · SD2
- [Accelerate Failure & Get More Insights In To Your Work](https://www.sarahdoody.com/accelerate-failure/) · 2017-11-28 · `reasoned_essay` · SD3

## Irene Au

공식 사이트: [Irene Au](https://www.ireneau.com/). 현재 직함은 규칙의 근거로 사용하지 않는다.

| 후보 | 적용할 상황 | 보존할 것 / 역효과 |
| --- | --- | --- |
| A-IA-1 · 갈등이 있는 구조만 낮은 비용으로 비교한다 | 목록/상세 병렬 또는 전환처럼 서로 다른 사용 가치가 충돌한다. | 같은 콘텐츠와 과업 · 이미 확정된 선택 / 이미 사용자 선택이 명확한 수정이나 픽셀 오류는 대안 탐색을 반복하지 않는다. |
| A-IA-2 · 기능 통과와 감각적 피드백을 분리해 반복한다 | 테스트는 통과했지만 사용자가 답답하거나 기본 앱 같다고 평가한다. | 프로젝트에서 실제 긍정 평가를 받은 컴포넌트 구성 · 기능·접근성 / 사용자 감각을 이유로 정확성·접근성을 낮추지 않는다. |

공개 근거:
- [The Architecture of Creative Collaboration](https://www.ireneau.com/blog/the-architecture-of-creative-collaboration) · 2025-12-15 · `author_case_retrospective` · IA1
- [Rethinking the canonical design process diagram, and a call for beauty](https://www.ireneau.com/blog/rethinking-the-canonical-design-process-diagram-and-a-call-for-beauty) · 2025-12-15 · `reasoned_essay` · IA2

현 페이지의 2025-12-15 게시 메타데이터와 집 설계 경험의 2014–2017 맥락을 구분한다.

## Luke Wroblewski

공식 사이트: [Luke Wroblewski](https://www.lukew.com/). 현재 직함은 규칙의 근거로 사용하지 않는다.

| 후보 | 적용할 상황 | 보존할 것 / 역효과 |
| --- | --- | --- |
| A-LW-1 · 질문 유형을 보존하고 새 검색을 직접 비교한다 | 개인 경험 검색이 최신/과거·원문 찾기·정확한 개수를 같은 의미검색으로 뭉갠다. | 원문·시점·판단 변경 · 이전 검색과의 비교 가능성 / 모든 질문에 classifier·reranker 여러 단계를 강제로 추가하지 않는다. |
| A-LW-2 · 빈 AI 화면에 할 수 있는 일과 근거를 보여준다 | 사용자가 개인 학습/검색 기능에서 무엇을 물어야 할지 모르고, 적재 자료도 확인할 수 없다. | 명시적 import·AI 실행 · 원문 위치와 삭제 반영 / 개인 로그를 임의로 긁거나 X 등의 자동 수집을 동의 없이 활성화하지 않는다. |

공개 근거:
- [Ask LukeW: A New Retrieval System](https://www.lukew.com/ff/2157/ask-lukew-a-new-retrieval-system) · 2026-08-17 · `author_case_retrospective` · LW1
- [Always Asking People to Ask](https://www.lukew.com/ff/2160/always-asking-people-to-ask) · 2026-09-08 · `reported_user_research` · LW2
- [Ask LukeW: Instant Content Indexing](https://www.lukew.com/ff/2168/ask-lukew-instant-content-indexing) · 2026-10-20 · `author_case_retrospective` · LW3

## Dan Saffer

공식 사이트: [Dan Saffer](https://www.odannyboy.com/). 현재 직함은 규칙의 근거로 사용하지 않는다.

| 후보 | 적용할 상황 | 보존할 것 / 역효과 |
| --- | --- | --- |
| A-DS-1 · 작은 행동도 시작·진행·결과·반복 계약을 갖게 한다 | 저장·전사·요약이 시작됐는지, 끝났는지, 다시 눌러도 되는지 모른다. | 실제 실행 상태 · 초안과 반복 동작 / 모든 작은 작업에 spinner·toast·축하 모션을 붙이지 않는다. |
| A-DS-2 · 기존 화면의 진짜 동작부터 확인해 수정 범위를 고른다 | 조그만 추가 요구가 전체 재설계로 번지거나 실제 구조 문제가 CSS 처방으로 끝난다. | 기존 화면의 장점 · 연결된 과업 동작 / 원글의 외형을 기능보다 우선할 수 있다는 주장은 채택하지 않는다. |

공개 근거:
- [New Book: Microinteractions](https://www.odannyboy.com/2012/07/new-book-microinteractions/) · 2012-07-09 · `reasoned_essay` · DS1
- [Tackling Maintenance Projects](https://boxesandarrows.com/tackling-maintenance-projects/) · 2002-11-04 · `author_case_retrospective` · DS2
- [The UX of Commercial Drones](https://uxmag.com/articles/the-ux-of-commercial-drones) · 2014-01-09 · `reasoned_essay` · DS3

2012 출간 전 글의 모델을 최종 책과 혼동하지 않는다. 책과 무관한 사이트로 이동한 오래된 Microinteractions 도메인과 원문 대신 일반 홈으로 이동한 O’Reilly 링크는 제외했다.

## Andy Budd

공식 사이트: [Andy Budd](https://andybudd.com/). 현재 직함은 규칙의 근거로 사용하지 않는다.

| 후보 | 적용할 상황 | 보존할 것 / 역효과 |
| --- | --- | --- |
| A-AB-1 · 검증 깊이를 실패 비용과 복구 가능성에 맞춘다 | 작은 수정에도 전체 절차를 강요하거나 큰 변경을 임시 실험이라며 방치한다. | 되돌림 경로 · 보안·데이터 무결성 / 빠르게 출시하자는 주장을 실제 배포 권한이나 파괴적 변경 허용으로 사용하지 않는다. |
| A-AB-2 · 생성 화면의 외형과 제품 일관성을 따로 비평한다 | 보기에는 익숙하고 세련됐지만 목적·행동·용어·상태가 어긋난다. | 공유된 행동·위계·상태 계약 / AI trope 탐지를 근거로 모든 gradient·카드·폰트·여백을 금지하지 않는다. |

공개 근거:
- [Designing Fast and Slow](https://andybudd.com/archives/2026/07/designing-fast-and-slow) · 2026-07-23 · `reasoned_essay` · AB1
- [The Battle Between Shipping and Perfection: A Designer’s Dilemma](https://andybudd.com/archives/2024/12/the-battle-between-shipping-and-perfection-a-designer-s-dilemma) · 2024-12-06 · `reasoned_essay` · AB2
- [Notes from the future of design](https://andybudd.com/archives/2026/07/notes-from-the-future-of-design) · 2026-07-09 · `author_case_retrospective` · AB3

일부 web 도구 요청은 403이었으나 canonical HTTPS 공개 본문을 직접 확인했다. 자세한 fetch/날짜 근거는 JSON에 보존했다.

## Don Norman

공식 사이트: [Don Norman](https://jnd.org/). 현재 직함은 규칙의 근거로 사용하지 않는다.

| 후보 | 적용할 상황 | 보존할 것 / 역효과 |
| --- | --- | --- |
| uxb-norman-activity · 고장난 화면보다 끊어진 과업을 먼저 찾기 | 회의에서 나온 할 일이 작업 목록까지 전달되지 않는 등 여러 화면·서비스를 잇는 과업이 실패할 때. | 회의 원문과 작업의 연결 · 중복·누락을 구분할 수 있는 결과 / 한 버튼의 오타나 국소 시각 오류까지 전체 서비스 관찰을 강제하지 않는다. |
| uxb-norman-discovery · 주요 동작은 찾을 수 있고 잘못 눌러도 돌아올 수 있게 | 드롭다운, 달력, 스와이프나 아이콘 전용 조작을 새로 만들 때. | 키보드·터치 조작 · 안쪽 팝업부터 닫기·focus 복귀 / 고급 기능을 모두 펼칠 필요는 없으며 숙련자 단축 경로는 유지할 수 있다. |

공개 근거:
- [The Four Fundamental Principles of Human-Centered Design and Application](https://jnd.org/the-four-fundamental-principles-ofhuman-centered-design-and-application/) · 2019-07-23 · `principle_synthesis` · b-norman-hcd
- [Gestural Interfaces: A Step Backwards In Usability](https://jnd.org/gestural-interfaces-a-step-backwards-in-usability/) · 2010-05-28 · `reported_user_research` · b-norman-gestures

## Brenda Laurel

공식 사이트: [Brenda Laurel](https://www.tauzero.com/Brenda_Laurel/). 현재 직함은 규칙의 근거로 사용하지 않는다.

| 후보 | 적용할 상황 | 보존할 것 / 역효과 |
| --- | --- | --- |
| uxb-laurel-evidence-to-rule · 관찰을 조건과 이유가 있는 구현 지침으로 변환 | 사용자가 수정 이유를 설명했거나 새 사용자군에 맞춘 경험을 만들 때. | 원문과 이유 · 화면·과업의 적용 범위 / 집단 경향을 개인 선호로 대입하거나 한 화면의 불호를 모든 제품에 적용하지 않는다. |
| uxb-laurel-continuity · 사용자가 쌓은 관계와 자료의 종료 경로까지 설계 | 회의·요청 세션, 개인 기억, 장기 자동화처럼 사용자가 시간이 지나며 자료를 쌓을 때. | 내보낸 자료의 연결 무결성 · 실제 보존 범위 / 영구 보존·무제한 자동 응답을 약속하지 않으며 실제 개인정보 삭제를 테스트하지 않는다. |

공개 근거:
- [Technological Humanism and Values-Driven Design](https://www.tauzero.com/Brenda_Laurel/Recent_Talks/Technological_Humanism.html) · 1998-04 · `reported_user_research` · b-laurel-humanism
- [New Players, New Games](https://www.tauzero.com/Brenda_Laurel/Recent_Talks/NewPlayersNewGames.html) · 1999 · `author_case_retrospective` · b-laurel-new-players

## Jared M. Spool

공식 사이트: [Jared M. Spool](https://articles.centercentre.com/). 현재 직함은 규칙의 근거로 사용하지 않는다.

| 후보 | 적용할 상황 | 보존할 것 / 역효과 |
| --- | --- | --- |
| uxb-spool-find-to-outcome · 기능의 존재와 실제 과업 성과를 따로 계측 | 기능은 구현되어 있지만 찾기 어렵거나 설정 단계에서 멈춘다는 피드백이 나올 때. | 현재 과업 문맥 · 완료와 실제 성과의 구분 / 클릭·이용량 증가만을 성과로 보지 않고 불필요한 작업 증가도 확인한다. |
| uxb-spool-two-party · AI 사용의 편익과 영향을 받는 당사자를 함께 확인 | 대화 요약·담당자 추출·공유처럼 AI 결과가 다른 사람의 말이나 책임을 표현할 때. | 발언 원문 · 불확실성·초안/확정/공유의 실제 상태 / 낮은 영향의 개인 초안마다 승인을 추가하지 않으며 타인의 만족을 추정하지 않는다. |

공개 근거:
- [Experience Strategists Approach UX Differently](https://articles.centercentre.com/experience-strategists-approach-ux-differently/) · 2026-03-06 · `reported_client_case` · b-spool-strategy
- [Nobody Likes Being on the Receiving End of AI](https://articles.centercentre.com/nobody-likes-being-on-the-receiving-end-of-ai/) · 2026-02-06 · `reasoned_essay` · b-spool-two-party-ai

## Jakob Nielsen

공식 사이트: [Jakob Nielsen](https://www.uxtigers.com/). 현재 직함은 규칙의 근거로 사용하지 않는다.

| 후보 | 적용할 상황 | 보존할 것 / 역효과 |
| --- | --- | --- |
| uxb-nielsen-task-minimalism · 비어 보이는 화면보다 필요한 정보의 접근성을 평가 | 카드와 패널이 많거나 화면을 단순화해 달라는 요청이 있을 때. | 필요 정보·기본값·저장/오류 상태 · 접은 기능의 찾을 수 있는 진입점 / 고빈도 비교 데이터를 분리해 왕복을 늘리거나 여백 비율을 고정하지 않는다. |
| uxb-nielsen-delegation · 요청의 지속 범위와 실행 권한을 분리 | 피드백을 장기 기억으로 전환하거나 AI가 여러 요청을 지속 처리할 때. | 요청의 범위·권한 구분 · 규칙 철회와 세션 경계 / 이미 합의된 개발에 모드 선택·반복 승인을 추가하거나 우발적 불만을 영구화하지 않는다. |

공개 근거:
- [10 Usability Heuristics for User Interface Design](https://www.nngroup.com/articles/ten-usability-heuristics/) · 1994-04-24 · `principle_synthesis` · b-nielsen-heuristics
- [3 AI Interaction Styles: Turn-Taking, Task Agents, Always-On](https://www.uxtigers.com/post/ai-interaction-styles) · 2026-10-14 · `reasoned_essay` · b-nielsen-ai-styles

## Aarron Walter

공식 사이트: [Aarron Walter](https://aarronwalter.com/). 현재 직함은 규칙의 근거로 사용하지 않는다.

| 후보 | 적용할 상황 | 보존할 것 / 역효과 |
| --- | --- | --- |
| uxb-walter-tone · 상태와 감정에 맞추되 업무를 방해하지 않는 표현 | 완료·진행·오류 문구나 성취 애니메이션을 설계할 때. | 오류의 원인과 복구 행동 · reduced motion · 공유 문체 / 반복 저장마다 성취 연출을 넣거나 실패 상황에 농담을 앞세우지 않는다. |
| uxb-walter-constraints · 실제 기기·연결·운영 흐름을 구현 계약에 포함 | 모바일·느린 연결·여러 담당자가 이어받는 서비스의 기술 선택을 할 때. | 초안·요청 상태 · 기존 자료 연결 · 컨테이너 원칙과 승인된 MLX 호스트 예외 / 과거 사례의 저장소·프레임워크를 새 서비스 기본값으로 복사하거나 불필요한 인프라를 추가하지 않는다. |

공개 근거:
- [Mailchimp](https://aarronwalter.com/portfolio/mailchimp) · 게시일 미공개 · `author_case_retrospective` · b-walter-mailchimp
- [Resolve to Save Lives](https://aarronwalter.com/portfolio/rtsl) · 게시일 미공개 · `author_case_retrospective` · b-walter-rtsl

## 기록과 승격

[경험 로그 예시](../templates/experience.example.json)에 product/cycle·증상·원인·수정·근거·실제 결과·한계·source recipe를 연결한다. `not_run`을 성공으로 바꾸지 않는다. 기술적 통과와 사용자 선호는 별도 상태다. 범위가 달라지면 다시 판단하며 자동으로 전역 규칙을 만들지 않는다.
