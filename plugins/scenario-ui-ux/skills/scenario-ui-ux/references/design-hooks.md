# 디자인 검사의 실행 계약

이 도구는 소스나 사용자 결정을 자동 수정하지 않는다. `PostToolUse`는 짧은 정적 검사를, `Stop`은 정적 검사 → 명시한 구문 검사 → 브라우저 과업 검사 → 선택한 독립 critique를 실행한다. CSS 토큰 통과, 실제 기능 통과, UX 판단, 사용자 취향을 별도로 기록한다.

## 프로젝트 계약

`templates/DESIGN.md`와 `templates/design-contract.example.json`은 시작 예제다. 프로젝트에 맞게 파일·토큰·과업·검증 명령을 정한 뒤 사용한다. 예제 자체가 프로젝트 검증을 통과했다는 뜻은 아니다.

`DESIGN.md`에 둘 중 정확히 하나를 둔다.

1. `design-contract` 언어 이름을 사용한 fenced JSON 블록.
2. `<!-- design-contract: design-contract.json sha256:... -->` 링크. 해시는 해당 JSON 파일의 실제 UTF-8 바이트 SHA-256이다.

계약의 `design.sha256`는 그 fenced 블록 또는 링크를 제거한 인간용 본문을 LF로 통일하고 양끝 공백 제거 후 개행 하나를 붙인 해시다. `python3 scripts/design-audit.py --project PROJECT --print-design-hash`로 읽기만 하여 계산할 수 있다. 본문 변경 시 계약의 본문 해시를 갱신하고 외부 JSON이면 링크의 파일 해시도 갱신한다. 둘 중 하나라도 오래되면 실패한다. 이 해시는 drift 검출이며 사용자 승인이나 신뢰 서명은 아니다.

- `task_id`: 같은 요청에서 고정한다. 예산은 프로젝트/과업 키로 영속화한다. 같은 본문 해시에 task_id만 바꾸면 거부한다. 새 과업은 현재 시나리오를 본문에 적는다. 이 장치가 사람의 의도를 인증하지는 않으므로 실패 우회를 위해 새 과업·프로젝트·결과 폴더를 만드는 행동은 금지한다.
- `scope.paths`: 이번 과업에 포함한 UI 파일의 명시 목록. 전체 저장소 lint를 강제하지 않는다. CSS, HTML, JS/MJS, TS, JSX/TSX만 허용하며 비밀·환경·호스트 설정 경로와 symlink는 거부한다.
- `scope.evidence_paths`: 같은 허용 확장자의 UI JS·프로젝트 테스트 중 해시/무결성/critic 입력에만 포함할 명시 목록. 이 파일의 스타일을 정적 검사했다고 주장하지 않는다. 팝업 위치 계산처럼 합당한 JS geometry는 이 범위에서 브라우저로 검증할 수 있다. 변경하면 캐시가 무효화된다.
- `tokens`: 색·간격·타입의 CSS 변수/정확한 선언값, 선택적으로 `radius`. 정의 누락·값 drift·관리되지 않는 참조·raw literal을 검출한다. 0·CSS 기본 키워드처럼 의미상 기본값을 허용하되 이 검사는 완전한 CSS 파서가 아니다.
- `scope.allow`: `{path, rule, values, reason}`. `rule`은 color/spacing/typography/radius. 기존 값의 파일별 예외만 허용한다. 모든 색상·파일을 허용하는 wildcard는 없다. 예외에 없는 새 색은 실패한다.
- `shapes`: `{path, role, selector, radius, reason}`. `radius`는 선언한 CSS 변수 이름이다. 명시 selector의 border-radius를 검사한다. 입력·포커스 selector가 같은 변수로 지정되면 곡률 drift를 찾는다. pseudo-element/상속/계산된 실제 기하를 보장하지는 않으며 브라우저로 함께 확인한다.
- `utility_classes`: Tailwind 사용 프로젝트만 `enabled:true`로 켜고 정적 클래스의 color/spacing/typography/radius 허용 목록을 지정한다. vanilla의 `text-button` 같은 자체 클래스 이름을 Tailwind로 오해하지 않는다. 임의 hex·arbitrary 값도 켠 검사에서 목록 밖이면 실패한다. 끈 상태는 utility_class_scan=not_configured로 기록한다. HTML inline style도 검사한다. 동적 className, JSX style 객체, JS `.style` 변경은 AST로 해석하지 않으므로 검사 범위에 있으면 지원하지 않는 스타일 문법으로 실패한다. CSS 검사만 통과시키고 전체 TSX 스타일이 검증됐다고 말하지 않는다. 이 경우 프로젝트 AST 검사를 만들거나 해당 작업의 검증 범위를 명시적으로 재정의해야 한다.
- `policy`: 원문 개인 결정 JSON과 해석 JSON의 읽기 경로. required일 때 파일 누락·형식·전체 건수·event/revision/decision·watermark 불일치는 실패한다. adopt와 reject 모두 원문 이유와 범위별 해석을 유지한다. 원본 expert-review SQLite에는 접근하거나 쓰지 않는다.

## 실제 실행과 결과

`checks.syntax`와 `checks.browser`는 검토한 `argv` 문자열 배열만 받는다. 명령이 있으면 `input_paths`에 실행 스크립트·package/lock·테스트 설정처럼 그 명령 결과를 바꾸는 입력 파일도 명시해야 한다. 해시가 바뀌면 캐시를 무효화한다. 선언하지 않은 의존성·실행 환경 변화까지 추적하는 hermetic build는 아니다. shell=False로 한 번 실행하며 셸/env 실행기는 거부한다. 정해진 명령 자체는 실행 코드이므로 권한 경계나 샌드박스가 아니다. UI 테스트에만 필요한 명령·fixture를 사용하고 원본 자료를 수정하는 명령을 넣지 않는다. 소스/정책 해시가 실행 중 바뀌면 실패로 기록하며 이미 발생한 변경을 취소하지는 않는다. 자식 프로세스 stdout/stderr는 비밀 유출을 막기 위해 원문 대신 해시만 남긴다.

브라우저 명령은 `.design-audit/` 아래의 `record` 경로에 다음 JSON을 새로 작성해야 한다. 캡처가 이미 있다는 이유로 구조·UX 문제 진단을 생략하지 않는다.

```json
{
  "format": "scenario-browser-observation/v1",
  "status": "pass",
  "task": "할 일 추가 창에서 입력하고 저장한다",
  "expected": "별도 창이 열리고 저장 후 목록에 새 행이 나타난다",
  "observed": "실제 수행한 단계와 확인한 화면/상태를 적는다",
  "screenshots": [{"path": ".design-audit/browser/after.png", "sha256": "실제 파일 해시"}]
}
```

명령 0만으로 브라우저 검증을 통과시키지 않는다. 오래된 결과·없는 캡처·해시 불일치는 실패한다. 캡처는 non-interlaced PNG를 사용하며 헤더·CRC·크기·scanline 스트림을 검사한다. 그래도 이미지가 실제 브라우저에서 촬영되었다는 증명은 아니다. 테스트가 써 둔 expected/observed는 테스트의 관찰 주장이고, hook이 이미지를 시각적으로 심사했다는 뜻이 아니다. 캡처를 건너뛰어야 하는 별도 과업은 `require_screenshot:false`를 명시하며 생략 사실을 보고한다. 명령 미지정·실행 불가·미인증·선행 실패는 `not_run`이다. 필수 단계의 not_run은 gate 실패다.

## 브라우저 실행별 이력 보관

브라우저 명령의 고정 출력 경로는 staging이다. 명령 실행 뒤 record 형식, 원본 record/PNG의 freshness와 해시를 먼저 검증하고, 통과한 증거를 `.design-audit/browser-runs/<새 UUID>/`에 추가한다. 복사를 오래된 결과의 freshness를 갱신하는 수단으로 쓰지 않는다.

```text
.design-audit/browser-runs/<UUID>/
  source-record.json      # 검증한 생산자 record의 원본 바이트
  screenshot-001.png      # 검증 후 다시 해시를 확인한 PNG
  screenshot-002.png      # 있을 때만 보관
  observation.json        # screenshots 경로를 이 실행 보관본으로 바꾼 record
```

보고서의 `record_path`, `record_sha256`, `record.screenshots`는 이 보관본을 가리킨다. 원본 metadata는 유지하고, `archive_provenance`에 원래 record 경로/해시와 캡처 경로 대응을 남긴다. 다음 실행이 `.design-audit/browser/after.png`나 원래 record를 덮어써도 이전 보고서·시각 검수는 이전 보관본을 사용한다. 캐시와 이미지 첨부는 보관된 record·PNG 및 원본 record 사본의 해시를 검증한다. 검증된 `status:fail` 기록도 같은 방식으로 보존한다.

보관 디렉터리는 새로 생성하며 파일은 exclusive 생성으로만 쓴다. 기존 경로 충돌, symlink, 경로 이탈이면 거부하고 덮어쓰지 않는다. 복사 중 실패하면 `archive_status:incomplete`와 가능한 `browser_run_path`를 남기고 이미 쓴 부분 증거를 삭제하지 않는다. 검증하지 않은 임의의 파일은 복사하지 않는다. 이 보관은 명령 자체의 권한을 제한하는 샌드박스가 아니며, 보관본의 외부 변경은 해시 검사로 발견한다.

이 변경 이후의 실행부터 보존한다. 이전 버전에서 고정 경로가 덮어써져 이미 사라진 과거 캡처는 이 기능으로 복구할 수 없다. 기존 제품 결과·실패 기록을 설치 전에 별도로 보존한 사본이 있다면 함께 유지한다. 이 기능을 이유로 이전 보고서나 `.design-audit/` 상태를 지우지 않는다.

`checks.critique`의 enabled를 켜면 오직 `BROKER_URL`의 `POST /turns`와 `BROKER_TOKEN`을 사용한다. 다른 모델·embedding API·provider key를 만들거나 재사용하지 않는다. 현재의 컨테이너 전용 Codex 로그인 선택을 유지한다. 인증 대기 상태에서는 live 호출을 검증했다고 표시하지 않는다.

독립 critic에는 소스와 브라우저 과업 관찰, 상황별 UX 진단, 디자이너 경험의 적용 이유, 개인 판단/해석을 데이터로 전달한다. 근거 ID가 없는 의견은 수락하지 않는다. 역할별 정보 우선순위·한 화면의 동시 작업·상태·포커스·호평한 컴포넌트 보존을 평가하되 저자의 권위 자체를 근거로 삼지 않는다. `require_visual:true`이면 fresh/hash-bound 캡처 픽셀을 Broker에 첨부하고 이미지별 검사 및 영수증을 확인한다. [이미지 입력 계약](vision-critique.md)을 따른다. 이미지가 없거나 인증이 없으면 not_run이며, 소스 전용 리뷰와 시각 리뷰를 구분한다. 실제 로그인·live 시각 추론은 아직 미검증이다. 사용자 기호는 항상 not_reviewed로 둔다. 회신은 실행 명령으로 사용하지 않는다. timeout/불명확 완료는 요청 ID를 보존하고 자동 재전송하지 않는다.

## 설치와 호스트 연결

```sh
python3 scripts/install-design-hooks.py --project /path/to/project --host both
python3 /path/to/project/.design-hooks/design-hook.py --project /path/to/project --event CI
```

설치는 `.design-hooks/`에 두 실행 파일과 최소 UX reference 세 개를 해시와 함께 복사하고 프로젝트 `.codex/hooks.json`, `.claude/settings.json`의 기존 설정을 보존하여 병합한다. 설치된 critic도 이 검증된 reference를 읽는다. 같은 정의로 재설치하면 중복하지 않는다. 관리 runtime 변경·중복/충돌·symlink·동일 Codex layer의 inline hooks가 있으면 덮어쓰지 않는다. 전역 사용자 설정, 신뢰 기록, permission/approval 설정을 수정하지 않는다. 기존 CI는 출력된 `ci_argv`를 필수 단계로 호출하면 되며 GitHub Actions 파일을 자동 추가하지 않는다.

공식 [Codex Hooks](https://learn.chatgpt.com/docs/hooks)에 맞춰 프로젝트/플러그인 hook은 호스트에서 정확한 정의를 검토·신뢰해야 실행된다. 설치 자체로 신뢰되었다고 표시하지 않는다. `/hooks`에서 확인한다. `PostToolUse`는 이미 발생한 쓰기를 되돌릴 수 없고 일부 도구는 hook 경로 밖이다. `Stop`의 block은 재개 요청이다. [Claude Hooks](https://code.claude.com/docs/en/hooks)의 프로젝트 설정도 기존 호스트 정책을 따른다. 따라서 이 pipeline을 배포 차단 경계로 쓰려면 CI에서 반환 코드를 필수 검사로 설정한다. 자동 신뢰/bypass 옵션을 주입하지 않는다.

## 반복 상한과 쓰기 경계

`max_repairs`는 2 또는 3이다. 첫 실패 후 허용된 수정 요청을 하나 기록하고, 변경된 소스를 검사한 다음 실패가 계속되면 남은 수정 요청만 사용한다. 정적 보고서 전체·소스/정책/명령 입력·runtime 코드/UX reference 해시가 같을 때만 캐시를 재사용하여 브라우저·LLM을 재실행하지 않는다. 재사용 전 보고서 해시와 캡처/관찰 파일도 검증한다. 새 정적 실패를 예전 통과로 치환하지 않는다. Stop 재귀인데 실패 상태가 그대로면 바로 사용자 판단이 필요한 상태를 반환한다. 상한 소진·필수 도구 부재·Broker 완료 불명은 needs_user로 남기고 자동 반복을 멈춘다. 성공해도 과거 소비 예산을 자동 초기화하지 않는다.

이전 과업이 통과하면 새 과업을 정상적으로 시작할 수 있다. 미해결 과업이 남았는데 task_id와 본문을 함께 바꾸는 것도 자동 허용하지 않는다. 사용자가 실제로 다른 일을 시작하라고 지시했을 때 `--activate-task --decision-reason ... --decision-ref ...`로 전환 이유를 남긴다. 이전 과업과 예산은 유지한다. 현재 과업의 차단 해제는 아래 `--resolve`를 사용한다.

관리 marker·보고서·과업 상태는 고정된 `.design-audit/` 아래에 원자적으로 쓰고, 검증된 브라우저 증거는 `browser-runs/`의 실행별 추가 전용 경로에 보관한다. 비어 있지 않은 미관리 디렉터리, symlink, 포맷이 다른 기존 출력은 거부한다. hook은 소스를 직접 고치거나 원본 판단·DB·사용자 데이터를 수정하지 않는다. 결과/상태를 삭제하거나 task_id를 바꾸어 시도 상한을 우회하지 않는다. 사람이 보존된 보고서를 확인하고 후속 진행을 명시적으로 결정한 뒤에만 새 범위/예산을 정한다.

실제 사용자가 후속 진행을 지시한 경우에만 아래 CLI에 그 이유와 원천 대화/이벤트 ID를 적는다. 이 옵션은 인간의 의도를 인증하지 않으므로 agent가 스스로 승인하거나 단순 실패를 이유로 호출하면 안 된다. 기본 해제는 사용한 예산을 유지하고, 사용자가 새 수정 횟수를 허용한 경우에만 `--grant-repairs 2` 또는 `3`을 더한다. 기존 보고서와 이전 소비 횟수를 보존하고 generation만 올린다. Broker 완료 불명은 Broker 세션을 별도로 검사·해결한 후 진행한다.

```sh
python3 .design-hooks/design-hook.py --project . --resolve \
  --decision-reason '사용자가 인증 완료 후 재검증을 요청함' \
  --decision-ref 'conversation:event-id'
```

## 첫 설치의 검수 폴더 소유권

실제 UI scaffold·유효한 DESIGN 계약 뒤, 첫 브라우저 관찰·캡처를 쓰기 전에 Hook을 설치한다. 설치기는 모든 기존 설치 preflight가 성공한 후 runtime·native 설정을 쓰기 직전에 기존 `artifact_root` guard로 새/빈 `.design-audit/managed.json`만 초기화한다. 기존 managed 폴더의 marker·예산·보고서·관찰·캡처는 수정하지 않는다. 비어 있지 않은 미관리 artifact 폴더와 symlink는 runtime·호스트 설정 변경 전에 실패한다. 출처가 알려진 과거 산출물의 보존·이관은 별도 작업이며 설치기가 자동 채택하지 않는다. 이 변경은 설치 전체의 파일 시스템 transaction이나 호스트 신뢰 승인, 검수 통과를 뜻하지 않는다.
