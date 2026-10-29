# Self Plugin

요구사항 대화에서 작동하는 컨테이너 제품, 실제 브라우저 UX 진단과 같은 과업의 재검증까지 연결하는 개인 개발 도구 모음입니다. 제품을 만들며 발견한 결함과 수리 경험을 조건부 규칙으로 축적합니다.

## 포함된 플러그인

| 플러그인 | 버전 | 구성 |
|---|---|---|
| `da-development-method` | 0.2.0 | 신규. gstack 기반 개발·라우팅·피드백 회수 |
| `scenario-ui-ux` | 0.5.0 | 신규. 디자인 레퍼런스·정보 구조·DESIGN 계약·실제 UX 수리 |
| `ux-judgment` | — | Scenario 하위 skill. UX 저자 10명·원문 24개·조건부 판단 20개 |
| `text-wireframe-planner` | 2.0.0 | 개편. 사용자 과업별 진입·행동·결과 와이어프레임 |
| `craft-ui-motion` | 2.0.0 | 개편. 여백·타이포·목적 있는 모션·반응형 구조 |
| `live-browser-session` | 0.1.0 | 기존 재사용. 실제 브라우저 조회·캡처·기능 검증 |
| `plain-writing` | 0.1.0 | 기존 재사용. 상투어·과장·중복을 줄이는 글쓰기 |
| `unbox-ui` | 1.5.0 | 기존 재사용. 중첩 카드와 불필요한 경계 개선 |

외부 레퍼런스는 별도 신규 플러그인으로 세지 않습니다. 라이선스와 출처는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에 있습니다.

## 프로젝트 설치

Python 3.11 이상을 사용합니다. Python 검증 도구에는 `requirements-dev.txt`가 필요합니다. gstack을 실행하려면 Node/npm 또는 Bun도 필요합니다.

```sh
git clone https://github.com/zsed3d3-droid/self_plugin.git
cd self_plugin
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
source .venv/bin/activate
python scripts/setup-development.py --project /absolute/path/to/your-project
```

9개 프로젝트 skill wrapper와 Cursor 규칙, 서비스 검사·라우터를 설치합니다. 프로젝트의 기존 `AGENTS.md`를 대체하지 않습니다. 복사한 프로젝트를 이동하면 같은 명령으로 경로를 다시 연결합니다. 선택적으로 gstack을 준비합니다.

```sh
bash scripts/setup-gstack.sh
```

라우터는 실행 계획을 출력합니다. 선택한 스킬이나 gstack 검증이 실행됐다는 뜻은 아닙니다.

```sh
python3 scripts/route-development.py --request '{"work_type":"ui","new_flow":true}'
```

## 하네스와 훅

| 경로 | 역할·상태 |
|---|---|
| `scripts/setup-development.py` | 관리 파일 해시를 유지하는 프로젝트 설치기 |
| `scripts/route-development.py` | 작업별 개발 경로 선택 |
| `scripts/check-containers.py` | Compose·health·볼륨 선언 정적 검사 |
| `plugins/scenario-ui-ux/.../scripts/design-audit.py` | DESIGN·토큰·간격·타이포·개인 정책 정적 검사 |
| `plugins/scenario-ui-ux/.../scripts/design-hook.py` | 소스 해시에 연결한 구문·브라우저 과업·캡처·선택적 critic·수리 예산 |
| `harness/feedback-review/` | HTML에서 규칙 채택/거절·이유 기록, SQLite 검토 데모 |
| `harness/evidence-memory/` | 프로젝트·주제·목적별 근거 저장과 어휘 검색 |
| `harness/codex-broker/` | 별도 Codex 컨테이너·주제별 세션 재개·요청 멱등성 |
| `harness/preservation/` | 소스·실행 이미지 태그·해시·실패 상태 보존 |
| `harness/capacity-retry/` | 구조화된 용량 오류의 60초 재시도 정책. 전달 어댑터 제약으로 자동 활성화되지 않음 |
| `knowledge/` | 제품별 assistant 수리 사례. 사용자 채택 기록과 구분 |

디자인 Hook은 프로젝트의 `DESIGN.md`와 유효한 계약을 먼저 준비한 뒤 설치합니다. [설정 안내](docs/hooks-and-verification.md)를 따릅니다.

```sh
python3 plugins/scenario-ui-ux/skills/scenario-ui-ux/scripts/install-design-hooks.py \
  --project /absolute/path/to/your-project --host both
```

`PostToolUse`는 짧은 정적 검사를, `Stop`/명시적 CI는 구문·브라우저 검증을 수행합니다. **설치와 호스트 신뢰 승인은 별개**입니다. 원래 개발 환경의 수동 CI 통과를 새 설치의 자동 발화로 표시하지 않습니다. 전용 Broker 로그인은 건너뛴 상태이므로 실제 AI 시각 critic은 미실행입니다.

## 검증과 경험

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest discover -s plugins/scenario-ui-ux/skills/scenario-ui-ux/tests -p 'test_*.py'
python3 -m unittest discover -s plugins/scenario-ui-ux/skills/ux-judgment/tests -p 'test_*.py'
python3 harness/preservation/tests/test_preserve_product.py
python3 scripts/verify-distribution.py
```

배포 시 실제 실행 결과와 경계는 [검증 상태](docs/verification-status.md)에 기록합니다. 공개본은 설치 코드·연구·일반화한 경험을 포함하며, 개인 DB·판단 원문·인증·실행 세션·제품 이미지와 DB 백업은 포함하지 않습니다. 개발 과정의 제품과 원본 증거는 기존 로컬 보관소에 유지됩니다.

## 원천별 실제 실행 랩 · 0.5.0

기존 목록에서 빠졌던 원문·통합·실행 검증을 세 개의 컨테이너 랩으로 보완했습니다. [조사·선별 기록](research/reference-gap-20261029/README.md)과 [적용 계약](plugins/scenario-ui-ux/skills/scenario-ui-ux/references/reference-adoption.md)에 범위를 구분합니다.

| 랩 | 기본 접속 | 검증한 범위 |
|---|---|---|
| [Interaction](harness/reference-labs/interaction/README.md) | http://127.0.0.1:8871 | Next·React·Tailwind, CSS/Motion/Anime.js/Animate.css/GSAP 5개 판의 동일 과업 |
| [Motion Canvas](harness/reference-labs/canvas/README.md) | http://127.0.0.1:8872 | 실제 Player·Stage 프레임·PNG·재생/정지·반복 출력·보존 |
| [Anti-slop / Unslop](harness/reference-labs/anti-slop/README.md) | http://127.0.0.1:8873/after.html | 선별 규칙·전후/반례·키보드·선택 상태 보존 |

각 디렉터리에서 `docker compose up -d --build`로 실행합니다. 기존 개발 실험실8861–8863과 충돌하지 않게 공개본은8871–8873을 사용합니다. 실제 제품 사용과 독립 synthetic 실험은 다릅니다. 모션 랩은 짧은 상세 열기/닫기 과업이며 모든 layout·spring·타임라인 기능이나 사용자 선호 우위를 검증하지 않았습니다. Motion Canvas 범위는 브라우저 렌더와 PNG이며 영상 인코딩은 포함하지 않습니다.

공개 복사본도 새 이미지로 빌드하고 실제 브라우저 과업을 검증했습니다. 각 `VERIFICATION.json`에 원래 실험과 공개 포트·helper·Origin 경계 차이를 기록합니다. 테스트용 Playwright는 루트의 `npm ci`와 `npx playwright install chromium`으로 준비합니다. 서비스는 컨테이너에서 실행합니다.
