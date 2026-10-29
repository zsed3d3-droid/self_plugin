# UI/UX 원본 스킬 검토와 사용 범위

확인일: **2026-10-29**. 아래 평가는 원본의 장단점을 현재 프로젝트 목적에 맞춰 해석한 것이다. 실제 렌더링·사용자 판단을 대신하는 미적 정답이나 성능 보장으로 쓰지 않는다. 정확한 commit, 원본 경로, Git blob SHA, 복사본 SHA-256과 변경 내역은 [design-research.json](../sources/design-research.json)에 있다.

## 어떤 상황에 무엇을 읽는가

| 지금 해결할 문제 | 참고할 조각 | 이 프로젝트에서의 적용 |
| --- | --- | --- |
| 화면이 누구에게 무엇을 하게 하는지 모호함 | Taste의 page/app 구분 | 홍보 페이지와 실제 작업 화면을 구별하고 주요 과업을 먼저 정함 |
| 모든 폼·옵션이 한 화면에 나와 복잡함 | Impeccable `distill` | 현재 필요한 목록/행동을 앞에 두고 등록·가져오기·보조 설정은 명확한 진입점 뒤에 둠 |
| 카드 중첩·간격·정렬·밀도가 어색함 | Impeccable `layout` | 그룹 관계와 읽기 순서를 확인하고 여백·정렬·영역별 밀도로 해결 |
| 모션 중간에 정보가 다른 좌표에서 나타남 | Emil animation standards | 트리거·origin·이동 경로·중단·중간 프레임을 확인 |
| 모션이 버벅이거나 입력을 막음 | Emil animation performance | 속성·렌더링 단계·main-thread 부하를 나눠 재현·측정 |
| 코드는 정상인데 결과가 여전히 일반적임 | Taste `critique` | 실제 스크린샷과 사용자 참고 화면을 비교하고 구체적 차이부터 수정 |

사진·URL·실제 앱이 기준으로 주어지면 구현 전에 읽기 순서, 남겨야 할 정보, 간격, 컨트롤과 상태를 구체적으로 분석한다. 사용자가 좋다고 한 부분은 보존하고 불편하다고 한 부분을 먼저 고친다. 출처의 스타일을 통째로 덮어쓰거나 매 작업에 별도 디자인 세계관을 만들지 않는다.

## Taste Skill

[공식 사이트](https://www.tasteskill.dev/)와 [문서](https://www.tasteskill.dev/docs)는 [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill)의 소개다. 독립적인 두 근거로 중복 집계하지 않는다.

- **확인한 원본:** commit `12af471f627f866411b4bd785b19646d3672784c`, `skills/taste-skill/SKILL.md`의 이름은 `design-taste-frontend`. MIT, Leonxlnx 2026.
- **가져올 부분:** 작업용 앱과 읽고 설득하는 페이지를 구분하고, 코드의 의도보다 실제 화면에서 읽기 순서와 주요 행동을 확인한다. 장식을 줄인 후 내용까지 비어 버리지 않도록 실제 정보와 과업을 남긴다. [app-screens 복사본](../sources/selected/taste-skill/app-screens.md), [critique 복사본](../sources/selected/taste-skill/critique.md).
- **제외할 기본값:** 뽑힌 스타일을 반드시 따르는 방식, 모든 블록을 첫 화면에 채우는 규칙, 특정 색·폰트 금지와 마케팅 페이지의 여백 수치를 업무 앱 전체에 강제하지 않는다. 원문도 보라색 금지를 연구 결과가 아닌 저자의 취향으로 구분한다.
- **확인 한계:** 사이트의 13개 스킬 안내와 이번 저장소의 단일 `SKILL.md` 구조가 다르다. 설치/파일 구성은 pinned source를 기준으로 한다. 사이트 연구 수와 blind test는 저자의 설명이며 독립 검증한 결과로 취급하지 않는다.

## Emil Kowalski Skills

[공개 저장소](https://github.com/emilkowalski/skills)와 [작성자의 소개](https://emilkowal.ski/skill)를 확인했다.

- **확인한 원본:** commit `2d228630ba1446365f614a108cb8252f1feda202`. `emil-design-eng`, `animation-performance`, `review-animations` 등의 실제 스킬과 standards 파일이 있다. MIT, Emil Kowalski 2026.
- **가져올 부분:** 사용 빈도와 과업에 맞는 모션, 트리거에서 이어지는 공간 관계, 빠른 반대 동작에도 끊기지 않는 전환, 느린 재생과 중간 프레임 검토. 성능은 속성·layout/paint·main-thread 원인을 나눠 확인한다. [animation standards](../sources/selected/emil-skills/animation-standards.md), [performance](../sources/selected/emil-skills/animation-performance.md).
- **제외할 기본값:** 모든 키보드 동작의 모션 금지, 고정 duration이나 stagger의 일괄 적용, 특정 속성만으로 GPU/프레임률을 보장하는 표현. 사용자가 채택한 모션 원칙을 기준으로 필요한 경우만 사용한다. Vaul을 임의 배제하거나 교체하는 근거로 쓰지 않는다.
- **확인 한계:** 실제 기기 벤치마크는 수행하지 않았다. 공개 MIT 자료만 반입했고 유료 강의의 추가 스킬·자산은 사용하지 않았다.

## Impeccable

[공개 저장소](https://github.com/pbakaus/impeccable)를 기준으로 확인했다.

- **확인한 원본:** commit `7510e233b228864606888d252abacf5e7148bf87`. 실제 source entry는 `skill/SKILL.src.md`; `.agents/skills/impeccable/SKILL.md`는 host용 배포본이다. Apache-2.0, Paul Bakaus. `NOTICE.md`도 함께 보존했다.
- **가져올 부분:** `distill`의 정보 과다·단계적 공개·불필요한 카드 제거, `layout`의 근접성·그룹·읽기 순서·영역별 밀도·화면 폭별 구조 검토. 기능과 접근성을 없애지 않고 인지 부담을 줄이는 방향이다. [distill](../sources/selected/impeccable/distill.md), [layout](../sources/selected/impeccable/layout.md).
- **제외할 기본값:** 회색 화면을 실패로 보는 판단, 시그니처 효과·색·새 세계관의 의무화, 사이드바 무조건 제거, 항상 3안이나 독립 reviewer/검출기를 동원하는 절차. source의 brief 우선 원칙을 적용하고 현재 사용자의 흑백·간결한 작업 흐름 요청을 우선한다.
- **확인 한계:** README의 24 commands·62 detector 소개는 확인했지만 CLI/검출기를 실행해 결과를 검증하지 않았다. `skill/SKILL.md`는 존재하지 않아 404였고 실제 source 경로를 다시 확인했다.

## 오프라인 자료와 실행 경계

`sources/selected/`는 필요한 상황에만 읽는 **원본 참고 자료**다. 별도의 활성 스킬로 설치하지 않았으며 그 안의 명령·강제 미학·전체 워크플로우를 자동 실행하지 않는다. 상위 스킬의 적용 범위와 현재 사용자 판단이 우선한다.

MIT 원본의 저작권·라이선스와 Apache 원본의 LICENSE·NOTICE를 보존했다. 읽기 편의를 위해 일부 상대 Markdown 링크만 pinned canonical URL로 바꿨고 해당 파일 앞에 변경 사실을 표시했다. 원본/로컬 해시는 JSON에서 구분한다. source의 scripts·바이너리·설치기·hooks는 반입하거나 실행하지 않았다. 기존 UI/UX Pro Max 자료는 중복 반입하지 않았다.
