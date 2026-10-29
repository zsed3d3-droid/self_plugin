# Scenario UI/UX 0.4.0

사용자 기능을 레퍼런스·디자이너 판단·실행 검증에 연결하는 gstack 기반 UI 전문 플러그인입니다. 캡처 기능을 더하는 대신, 화면의 구조와 과업에서 발견한 문제를 왜·어떻게 고칠지 다룹니다.

흐름은 **기능/시나리오 → 레퍼런스 선택 → 원인 진단 → DESIGN.md → 구현 → Hook 검수·수정·재검증 → 근거 축적**입니다. 외부 저자의 규칙은 조건별로 선별하며 기존 사용자 연결된 프로젝트 판단과 현재 요청이 우선합니다.

- [실행 스킬](skills/scenario-ui-ux/SKILL.md): 단계별 자동 경로
- [구조·흐름 수리법](skills/scenario-ui-ux/references/runtime-ux-method.md): 증상 8종, 원인·개입·역효과·재검증
- [UX Judgment](skills/ux-judgment/SKILL.md): 10명·24개 원문·20개 조건부 판단, 적용 범위와 반례
- [디자이너 판단](skills/scenario-ui-ux/references/designer-judgment.md): 공개 실무 경험과 적용 한계
- [Taste·Emil·Impeccable 검토](skills/scenario-ui-ux/references/design-source-review.md), [MengTo·ThreeUI](skills/scenario-ui-ux/references/mengto.md)
- [프레임워크 프로필](skills/scenario-ui-ux/references/framework-profiles.md): Vercel/Next/React/Tailwind·Remotion을 실제 스택에서만 선택
- [엔지니어링 검토](skills/scenario-ui-ux/references/engineering-review.md): Addy의 DevTools·5축 리뷰·보안·단순화
- [Hook 하네스](skills/scenario-ui-ux/references/design-hooks.md): 변경 검사·hash·명령 입력·실제 브라우저 근거·독립 Broker 검수·유한 수정 예산·CI gate

호출은 `$scenario-ui-ux`, Cursor는 `/scenario-ui-ux`입니다. 저장소 루트에서 `python3 scripts/setup-development.py --project /path/to/project`로 프로젝트에 설치합니다. 기존 AGENTS.md/CLAUDE.md는 보존합니다.

레퍼런스 후보 검색(네트워크·추가 패키지 불필요):

```sh
cd plugins/scenario-ui-ux/skills/scenario-ui-ux
python3 scripts/reference-plan.py --task '업무 추가 모달, 기한 달력, 상태 선택' --stack vanilla
```

프로젝트에 DESIGN.md와 명시적 계약을 작성한 뒤 `scripts/install-design-hooks.py --project /path/to/project`로 로컬 Hooks를 병합합니다. 호스트 신뢰는 별도이며 자동 승인하지 않습니다. 실제 gate는 생성된 `.design-hooks/design-hook.py --project . --event CI`를 사용합니다. 설정만 만들었거나 필수 단계가 미실행이면 통과가 아닙니다.

원래 개발 환경에는 실제 Hooks 설정을 만들고 정적/개인 판단/구문/격리 브라우저 경로를 실행했습니다. 전용 Broker 인증·연결이 없는 독립 검수는 not_run으로 gate를 차단합니다. Broker와 Hook의 이미지 첨부·영수증 검사를 구현했으며, 전용 로그인과 실제 시각 추론은 아직 미검증입니다. 사용자 만족은 별도 미평가 상태입니다.

원문/핀/라이선스는 [sources/NOTICE.md](skills/scenario-ui-ux/sources/NOTICE.md)와 `*-research.json`에 있습니다. newly selected source installers/scripts는 실행하지 않습니다. UIUX ProMax 오프라인 검색 코드는 기존 MIT snapshot을 유지합니다. 유료 자산·고정 색상·강제 밀도·필수 3안·중첩 카드를 기본값으로 만들지 않습니다.

## 0.5.0

원천별 상태와 실제 검증 랩을 [적용 계약](skills/scenario-ui-ux/references/reference-adoption.md)에 연결했습니다. Anti-slop·Unslop의 조건별 검수 기준을 네 번째 해시 검증 가이드로 설치·전달합니다. 새 가이드의 변조 거절을 포함한 Hook36검사를 통과했습니다. 실제 실행은 [검증 랩](../../harness/reference-labs/)을 참고합니다. 기존 프로젝트 설치본과 호스트 신뢰는 자동 변경하지 않습니다.
