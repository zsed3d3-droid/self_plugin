# Scoped evidence memory

`memory.py`를 원본 그대로 재사용하고, 기존 메모리 import·어휘 search·검색 피드백 API만 독립 FastAPI/PostgreSQL 컨테이너로 분리했습니다. 시작 시 빈 DB입니다. 개인 기록·45개 실험 데이터·사용자 판단·제품 코드·Codex 로그인·LLM/Broker 기능을 포함하지 않습니다.

```sh
cd harness/evidence-memory
python3 init-env.py
docker compose up --build -d
```

API: http://127.0.0.1:8852 . `/health` 외 `/api/*`는 새 `.env`의 `MEMORY_API_TOKEN`을 `Authorization: Bearer <token>` 헤더로 요구합니다. 생성기는 기존 `.env`를 덮어쓰지 않으며 토큰을 출력하지 않습니다. 다른 로그인이나 계정의 인증을 복사하지 않습니다. `.env.example`은 설명용 자리표시자이며 실행 인증이 아닙니다.

- `POST /api/memory/import`: `text`, `source`, `format`(`text`/`jsonl`), `project`, `topic`, `purpose`.
- `GET /api/memory/search?q=...&project=...&topic=...&purpose=...`: PostgreSQL FTS·부분 문자열 어휘 검색, 최대8건. 의미 검색이나 LLM 추론이 아닙니다.
- `POST /api/memory/retrieval-feedback`: 같은 scope의 `evidence_id`, `kind`(`suppress`/`correct`/`unsuppress`), `reason`, 선택적 `correction`. 원문을 덮어쓰지 않습니다.

JSONL에서 role은 `user` 또는 `assistant`로 보존됩니다. AI 실험을 사용자 채택으로 취급하지 않습니다. 동일 원천·scope·내용의 중복 import는 추가되지 않습니다. 반환문에는 원문이 있을 수 있으므로 기록을 공개 저장소나 불필요한 로그로 내보내지 마세요. 내장 정규식 마스킹은 완전한 개인 정보/비밀 탐지 기능이 아닙니다. 수집 전에 본인이 제공할 수 있는 자료인지 판단해야 합니다.

컨테이너 PG 포트는 호스트에 공개하지 않습니다. `evidence-db` named volume은 종료·재기동 후 유지됩니다. `docker compose stop`으로 정지하고 볼륨 삭제 명령을 사용하지 마세요. DB 이미지는 기존 검증 환경과 같은 `postgres:18.6`이며 이 배포본이 최신 안정 버전을 자동 추적하지는 않습니다. 갱신 전 마이그레이션·백업·복원을 확인하세요.

원본 스키마에서 `evidence`, `retrieval_feedback`, `feedback`만 포함했습니다. `feedback`은 기존 검색 결과의 평가 join을 유지하는 호환 테이블이며 이 어댑터에는 평가 생성 API가 없습니다. 회의·할일·교훈 승격·semantic search·자동 선호 학습은 포함하지 않습니다. 원본 라이브러리를 통합할 경우 psycopg dict-row 연결과 이 세 테이블이 필요합니다.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
```

통합 확인은 `MEMORY_TEST_URL=http://127.0.0.1:8852`와 새 테스트용 `MEMORY_API_TOKEN`이 있을 때만 수행합니다. 테스트는 고유한 synthetic scope에 기록을 추가하며 기존 자료를 삭제하지 않습니다. 라이브 API를 대상으로 했다면 테스트 기록도 DB에 유지됩니다. API 토큰은 로컬 단일 사용자 접근 제어이며 다중 사용자 권한·행 수준 보안을 제공하지 않습니다.
