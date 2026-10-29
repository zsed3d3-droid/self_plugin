# UI/UX 참고 근거

확인일: 2026-10-08. 아래는 원문을 복제한 규정이 아니라 이 스킬의 판단에 사용한 요약이다. 링크된 시스템을 설치할 필요는 없다.

## 사용자 제공 자료

「카드카드네모병 탈출용 디자인 점검표」와 `sniperfactory_official`의 여섯 참고 이미지에서 여백·정렬·배경 차이·구분선·타이포 위계·라벨 원칙을 반영했다. 원본 이미지와 Notion HTML은 패키지에 복제하지 않는다. 예시의 간격 2배, 폰트 3단계는 보편 규격이 아니라 초기 탐색 기준으로 취급한다.

## 정보 관계와 위계

- [NN/g — Proximity Principle in Visual Design](https://www.nngroup.com/articles/gestalt-proximity/): 관련 요소를 가깝게 두고 그룹 사이의 여백으로 관계를 드러낸다. 반응형 재배치가 이 관계를 깨뜨릴 수 있으므로 좁은 화면에서도 확인한다.
- [NN/g — Visual Hierarchy in UX](https://www.nngroup.com/articles/visual-hierarchy-ux-definition/): 크기·대비·그룹화로 읽기 우선순위를 만든다. 여백으로 부족하면 표면/경계를 추가할 수 있지만 시각적 잡음을 경계한다. 스퀸트 확인은 강조와 그룹을 살피는 보조 방법이다.
- [GOV.UK — Spacing](https://design-system.service.gov.uk/styles/spacing/): 일관된 간격 척도와 반응형 간격을 사용한다. 이 스킬에서는 대상 제품의 기존 spacing 토큰을 쓰며 GOV.UK의 픽셀값을 강제하지 않는다.
- [GOV.UK — Summary list](https://design-system.service.gov.uk/components/summary-list/): 키/값은 description list, 단순 목록은 목록, 비교 데이터는 표로 구분한다. 서로 독립된 복수 객체에는 summary card도 사용하므로 카드 자체를 금지할 근거는 아니다.

## 카드가 필요한 경우

- [IBM Carbon — Tile guidelines](https://www.carbondesignsystem.com/building-blocks/core/components/tile/guidelines): 정적·이동·선택·확장 타일을 구분한다. 전체가 이동하는 타일 안에 별도 행동을 중첩하지 않고, 선택 상태와 포커스/키보드 조작을 유지한다. 중첩 컴포넌트가 있을 수 있다는 점도 참고한다.

스킬의 판단: 중첩의 존재가 아니라 **같은 관계를 중복 표현하는 장식**이 제거 대상이다. 경계가 독립 객체나 상호작용을 이해하는 데 도움을 주면 유지한다. 이는 위 자료와 사용자 요구를 합친 설계 기준이며 외부 표준의 일괄 카드 금지 조항이 아니다.

## 경계 제거 시 접근성 확인

- [W3C — Contrast (Minimum), SC 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html): 적용 대상 일반 텍스트는 배경 대비 4.5:1 이상, 큰 텍스트는 3:1 이상. 보조정보라는 이유만으로 읽기 대비를 낮추지 않는다.
- [W3C — Non-text Contrast, SC 1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html): 적용 대상 컨트롤/상태 식별에 필요한 시각 정보는 인접 색 대비 3:1 이상. 모든 장식 구분선에 이 수치를 강제하는 규칙은 아니다. 텍스트 등으로 컨트롤을 식별할 수 있으면 경계가 필수는 아니지만 포커스 식별은 보존한다.
- [W3C — Use of Color, SC 1.4.1](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html): 상태 의미를 색상만으로 표현하지 않는다. 읽을 수 있는 라벨·형태 등의 단서를 함께 제공한다.
- [W3C — Reflow, SC 1.4.10](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html): 일반 세로 흐름 내용은 320 CSS px 상당 폭에서 정보/기능 손실과 양방향 스크롤을 점검한다. 표 등 본질적으로 2차원인 내용의 예외를 구분하며, 비교 구조를 훼손해 억지로 카드나 일렬 목록으로 바꾸지 않는다.

공식 문서의 일부 기준을 확인하는 것과 제품 전체의 WCAG 적합성을 입증하는 것은 다르다. 측정/실행하지 않은 검증을 통과로 보고하지 않는다.
