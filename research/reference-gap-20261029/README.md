# 미적용 레퍼런스 8개 심화 조사

2026-10-29에 각 저장소의 현재 commit을 고정하고 README·실제 LICENSE·파일 tree를 읽었다. Anti-slop와 Unslop UI는 SKILL 원문도 확인했다. Next/React/Tailwind는 각각의 공식 문서와 고정된 문서 소스를 읽었다. 이 작업에서 라이브러리 설치·제품 수정·실제 런타임 검증은 하지 않았다.

전체 출처의 immutable URL, commit SHA, 파일 Git blob SHA와 개별 검증 계획은 [review.json](review.json)에 있다. 출처를 읽은 상태와 제품에서 동작을 검증한 상태를 구별한다.

| 항목 | 실제 정체·라이선스 | 유용한 적용 후보 | 무조건 가져오지 않을 것 |
|---|---|---|---|
| Next / React / Tailwind | 공동 제작 skill이 확인된 묶음이 아니라 세 공식 문서에 근거한 로컬 프로필 | 서버 렌더 목록 + client 필터/다이얼로그, 단일 상태 소유권, 의미 있는 theme 토큰 | 모든 파일의 client 선언, 기존 앱을 이유 없이 Next/Tailwind로 변경 |
| Motion | JS/React/Vue 모션 runtime, MIT | 필터 결과 위치 전환과 선택 표시의 공간 관계 | 모든 요소 입장 애니메이션, 측정하지 않은 성능 주장, Motion+ 유료 자산 |
| Anime.js | DOM/SVG/object 모션 runtime, MIT | 설명 도표에서 선택한 관계선만 짧게 강조 | README의 무한 loop를 제품 기본값으로 사용 |
| Animate.css | CSS 애니메이션 유틸리티, **Hippocratic 2.1** | 작업 성공 후 한 번만 나타나는 상태 보조 효과 | MIT라는 가정, 끝없이 움직이는 장식, reduced-motion 규칙 제거 |
| GSAP | 타임라인 모션 runtime, **자체 Standard No Charge License** | 일반 제품 설명의 짧은 SVG 과정 + 정지/재생 | MIT라는 가정, 스크롤 조작 강제, 경쟁 시각 애니메이션 제작 도구로 무조건 사용 |
| Motion Canvas | TS generator 기반 설명용 벡터 애니메이션·편집기, MIT | 고정 시간의 설명 영상과 player 출력 | 폼/목록 UI 모션 도구로 취급하거나 제품에 편집기 전체 탑재 |
| Anti-slop | **에이전트 skill 6개와 규칙집**, MIT | DESIGN의 목적과 컨트롤 의미·상태·키보드·실측 주장 감사 | 반복 모드 질문·설치 wizard·항상 적용하는 40개 규칙·모든 작업의 4단 보고서·강제 liveliness 수치 |
| Unslop UI | **프론트 디자인 안티패턴 skill**, MIT | 중첩 카드·장식 아이콘·비슷한 색의 위계·느린 전환 진단 | 70/20/10 색 비율, 전역 글꼴/이모지 금지, 모든 제품의 중립 미니멀 디자인 강제 |

## 기존 카탈로그에서 잘못 합친 부분

Anti-slop와 Unslop UI는 모션 라이브러리가 아니다. React를 이미 사용한 제품이 있어도 그것이 Next·Tailwind 또는 공식 공동 skill 사용을 증명하지는 않는다. 반대로 공동 skill 출처가 미확정이라고 세 공식 문서의 프로필까지 적용하지 않을 이유는 없다.

Motion·Anime의 MIT 링크나 GSAP 예제를 자료에 두었다는 사실도 실제 package import나 사용자 과업 검증과 다르다. 이번 조사로 원문 검토 범위는 넓어졌지만 제품 적용 성공으로 상태를 올리지 않는다.

Next 저장소는 MIT, React 문서는 CC BY 4.0이다. 확인한 Tailwind 문서 저장소 root에는 LICENSE가 없어서 원문 재배포 권한을 추정하지 않는다. 이번 기록은 원문 복제가 아닌 독립 요약과 출처 링크다. GSAP 약관은 [공식 조건](https://gsap.com/community/standard-license/)을 해당 제품 기능과 대조해야 한다.

## 다음 실험의 형태

기존 완성 제품은 보존하고 별도 컨테이너 비교 실험을 만든다. 같은 데이터·동선·상태 계약을 CSS 기준판과 Motion/Anime/Animate.css/GSAP의 개별 판에 적용한다. Motion Canvas는 설명 영상 출력이라는 다른 과업으로 비교한다. Anti-slop와 Unslop UI는 검수 근거로 선별하고 전역 설치나 별도 승인 절차를 자동 추가하지 않는다.

각 판에서 빠른 반복 입력, 진행 중 취소/역전, 키보드 포커스, reduced motion, 320/390/1440 화면의 실제 과업을 확인한다. package lock·실제 import·소스 해시·전후 캡처·측정한 번들/프레임 정보·채택/제외 이유를 함께 남긴다. 기능 통과와 사용자의 선호 채택은 별도 상태로 유지한다.

이는 다음 구현을 위한 계획이며 아직 실행 영수증이 아니다.
