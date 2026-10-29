# 프레임워크별 선택 프로필

기존 프로젝트의 실제 stack을 먼저 읽는다. 일반 HTML/CSS/JS 앱에 Next.js·React·Tailwind·Remotion을 설치하는 기본 규칙이 아니다. 버전 의존 API·캐시·지원 상태는 해당 버전의 공식 문서로 확인한다. 정확한 조사 commit과 경로는 [engineering-research.json](../sources/engineering-research.json)에 있다.

| 조건 | 로드할 지식 | 적용·확인 |
| --- | --- | --- |
| React 렌더·데이터 로딩·번들 문제가 있는 프로젝트 | Vercel `skills/react-best-practices/SKILL.md`의 주제 분류 + React 공식 문서 | 요청 waterfall·실제 번들 비용·불필요한 리렌더를 측정하고 해당 규칙만 검토 |
| 기존 Next App Router 앱 | 위 분류 + Next 서버/클라이언트 공식 문서 | 서버 경계·비밀·직렬화·버전별 캐시를 검증. 상호작용 부분에 필요한 client 경계만 적용 |
| 기존 Tailwind 또는 사용자와 합의한 신규 stack | Tailwind 공식 theme 문서 | 기존 버전에 맞는 의미 토큰·공유 스타일 사용. v4 문법을 구버전 앱에 강제하지 않음 |
| 웹 접근성·폼·상태·탐색 검토 | Vercel web-design-guidelines의 검토 주제 + 현 앱의 시나리오 | 의미 있는 control·label·키보드·포커스·오류/로딩/빈 상태를 실제 브라우저에서 검사 |
| React 기반 영상·모션그래픽 제작 요청 | Remotion 공식 skills의 영상별 라우팅 + 실제 버전 문서 | 타임라인·프레임·자막/음성·preview·export 조건 검증. 일반 웹 hover 효과에 영상 엔진을 추가하지 않음 |

## React / Next / Tailwind

Vercel 실제 React skill은 async waterfall, 번들, 서버·클라이언트 데이터, 리렌더·렌더링, JS, 고급 패턴의 8개 범주를 담는다. 이를 모든 규칙의 자동 적용 명령으로 가져오지 않는다. 사용자 시나리오와 측정된 문제에 관련된 항목만 읽고 변경 전후를 확인한다.

[Next 서버/클라이언트 문서](https://nextjs.org/docs/app/getting-started/server-and-client-components)에 맞춰 서버에서 가능한 일과 상태·이벤트·브라우저 API가 필요한 경계를 나눈다. [React 문서](https://react.dev/learn/you-might-not-need-an-effect)에 따라 렌더 중 계산할 값·사용자 행동을 불필요한 Effect로 옮기지 않는다. [Tailwind theme 문서](https://tailwindcss.com/docs/theme)의 토큰 개념은 프로젝트 버전에 맞춰 사용한다. 작은 정적 앱은 기존 CSS 변수를 유지할 수 있다.

`nextjs-react-tailwind`라는 이름의 공식 통합 skill은 확인하지 못했다. 실제로 추적된 자료는 PatrickJS/awesome-cursorrules의 `rules/nextjs-react-tailwind-cursorrules-prompt-file.mdc`라는 커뮤니티 Cursor 규칙이다. 공식 Next/React/Tailwind 공동 제작물로 표시하거나 그대로 설치하지 않는다. 특정 디렉터리·shadcn·Framer Motion·nuqs를 일괄 요구하고 오래된 FID 기준을 담으므로, 이 로컬 프로필은 공식 문서와 검증된 Vercel 주제만 조합한다.

## Vercel 웹 디자인 검토

실제 upstream web-design-guidelines 파일은 외부의 최신 `web-interface-guidelines/main/command.md`를 가져오는 작은 라우터다. mutable 원격 지침을 자동 실행 정책으로 승격하지 않는다. 필요시 읽은 파일의 버전·내용을 확인하고 프로젝트 권한 내 검토 자료로만 사용한다.

폼/버튼 역할, 접근 가능한 이름, 키보드·포커스, 상태 피드백, overflow·반응형, reduced motion, 이미지 크기·레이아웃 안정성을 실제 동작과 함께 확인한다. “테스트 통과”를 사용자의 디자인 채택으로 치환하지 않는다. 카드 중첩·불필요한 보조 패널은 [개인 UI 기준](personal-ui.md)에 따라 과업 중심으로 줄인다.

## Remotion은 영상 요청에만

실제 Remotion skill router는 create·markup·Studio·render 등 과업을 나눈다. 기존 composition·fps·duration과 React/Remotion 버전을 읽고 Studio preview부터 확인한다. 내보내기를 요청한 경우에만 렌더 경로와 출력 형식을 선택한다. AWS·유료 렌더·유료 자산을 자동 도입하지 않는다.

음성·자막·전환은 정보 전달 목적에 맞추고 프레임 경계, 결정적인 재생, 해상도·안전 영역, 저작권과 실제 export 결과를 검증한다. [Remotion 사용 조건](https://www.remotion.dev/docs/license)은 프로젝트/조직 자격에 따라 확인한다. 제품 사용 조건과 skill 텍스트 재배포 권한은 별개다.

## 복사한 자료와 링크만 둔 자료

Addy MIT 원문은 라이선스를 포함한 최소 파일만 오프라인에 보존했다. Vercel은 README/metadata의 MIT 표기와 달리 조사 commit에 LICENSE 파일이 없고, Remotion skills도 라이선스 부여문을 찾지 못했다. 두 저장소는 자체 문장으로 만든 이 adapter와 immutable 원문 URL/해시만 보존했다. 라이선스가 명확해지기 전에는 원문 복제·재패키징하지 않는다. 저장소 목록만 보고 내용을 검토했다고 표시하지 않는다.
