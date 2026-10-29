# Live Browser Session 0.1.0

사용자가 직접 로그인한 전용 Chrome으로 실제 웹페이지를 조회·캡처하거나 기능을 테스트하고, 끝나면 Chrome을 닫고 프로필을 지우는 `$live-browser-session` 스킬이다. Claude Code와 Codex에서 같은 스크립트와 절차를 쓴다.

## 쓰는 경우

- 사내 SSO 로그인이 필요한 운영·개발 화면을 캡처해 매뉴얼·보고서에 넣을 때
- 실제 웹페이지에서 화면 이동, 역할별 메뉴, 버튼 노출, 오류 문구 같은 기능을 점검할 때

## 흐름

1. `scripts/browser-session.sh start <URL>` — 새 임시 프로필로 Chrome을 연다(원격 디버깅 `127.0.0.1:9333`).
2. 사용자가 그 창에서 직접 로그인한다. 에이전트는 비밀번호를 다루지 않는다.
3. 에이전트가 Playwright `connectOverCDP`로 연결해 새 탭에서 작업한다. `scripts/page-guard.mjs`가 쓰기 요청을 기본으로 막고, 개인정보를 흐리게 하고, 오류를 모은다.
4. `scripts/browser-session.sh stop --profile <경로>` — Chrome을 닫고 프로필을 지운다.

```text
$live-browser-session 운영 화면 매뉴얼용 캡처를 할 거야. 전용 Chrome을 열어 줘.
내가 로그인하면 쓰기 요청은 막고 캡처하고, 다른 사람 이름은 가려 줘. 끝나면 Chrome 닫고 프로필 지워 줘.
```

```text
$live-browser-session 개발 서버에서 담당자 역할로 메뉴와 완료 버튼이 보이는지 기능 테스트해 줘.
역할 전환 요청만 허용하고 결과에 막힌 요청과 콘솔 오류를 같이 알려 줘.
```

[스킬 본문](skills/live-browser-session/SKILL.md)에 시작·연결·캡처·기능 테스트·정리 기준을 모았다.

## 준비물

- Google Chrome(또는 Chromium). 다른 경로면 `CHROME_BIN`을 지정한다.
- Node 22 이상(내장 `WebSocket`으로 Chrome을 닫는다). 없으면 프로세스 종료로 닫는다.
- `playwright-core`. 없으면 작업 폴더 밖 임시 폴더에 설치하고 `PLAYWRIGHT_CORE`로 경로를 넘긴다.
- Codex는 샌드박스 설정에 따라 Chrome 실행과 `127.0.0.1` 접속에 승인이 필요할 수 있다.

## 안전 기준

- 전용 임시 프로필만 쓰고, 끝나면 지운다. `start`가 만든 표시 파일이 없는 폴더는 지우지 않는다.
- 원격 디버깅은 `127.0.0.1`에서만 연다.
- 쿠키·토큰 값을 읽거나 저장하지 않는다.
- 쓰기 요청은 사용자가 승인한 것만 `"METHOD /경로"` 단위로 허용한다.

## 검증

저장소 루트에서 실행한다.

```sh
python3 -B plugins/live-browser-session/tests/test_package.py
bash scripts/doctor.sh
```

패키지 검사는 manifest 일치·marketplace/스킬 연결·문서 링크, 스크립트 문법, 쓰기 허용 판정, 표시 파일 없는 폴더 삭제 거부를 확인한다. 실제 Chrome 실행과 로그인 화면 작업은 패키지 검사에 포함하지 않는다.
