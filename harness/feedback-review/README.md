# Feedback review journal

공개 연구에서 정리한 개발자/팀 10개·규칙 30개를 HTML에서 읽고 채택·거절·미정 및 이유를 기록합니다. 배포본은 빈 SQLite DB로 시작합니다. 원래 사용자의 판단·DB·스크린샷·원시 실행 기록은 포함하지 않습니다. `catalog.json`은 당시 조사 시점의 조건부 평가와 원문 링크이며, 사용자 채택 결과가 아닙니다. 저자의 최신 직책·프로젝트 상태를 보장하지 않습니다.

```sh
cd harness/feedback-review
docker compose up --build -d
```

접속: http://127.0.0.1:8851 . 포트는 `.env.example`의 `REVIEW_PORT`로 변경할 수 있습니다. 새 기록은 `review-data` named volume에 남습니다. 종료 시 `docker compose stop`을 사용합니다. 볼륨 삭제 명령을 사용하지 마세요.

이 서비스는 인증 없는 로컬 단일 사용자 검토 도구입니다. loopback 포트를 유지하며 인터넷·공유 네트워크에 공개하지 않습니다. 요청 Origin/Host 검사는 로그인 인증을 대체하지 않습니다.

`GET /api/export`로 판단·원문 이유·당시 규칙 snapshot을 읽습니다. `/api/history/{rule_id}`는 append-only 이력을 반환합니다. 내보내기에는 이후 사용자가 입력한 개인 정보가 있을 수 있으므로 공개 Git에 넣지 마세요. 저장이 설치된 플러그인을 자동 수정하지는 않습니다.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
```

테스트는 새 임시 DB에서 저장·중복 요청·동시 수정 충돌·재조회·부적절한 Origin/Host를 확인합니다. 실제 사용자 DB에는 접근하지 않습니다. `build_catalog.py`는 이 패키지의 공개 연구 catalog 생성 원본입니다. `research/primary-sources.json`에는 공개 저장소·라이선스 표기·commit 메타데이터만 담고 README 원문 발췌는 제외했습니다. 연구 링크의 원문 코드나 저작물을 이 서비스가 전부 번들한 것은 아닙니다. 공유 프레임워크의 출처·라이선스는 저장소 루트의 고지를 따릅니다.
