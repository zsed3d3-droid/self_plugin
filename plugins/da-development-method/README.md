# Development Method

gstack 기반 요구사항·과업·와이어프레임·구현·실제 브라우저 검증·피드백 회수를 연결합니다. `scripts/setup-development.py`로 프로젝트에 설치합니다.

개인 판단은 배포에 포함되지 않습니다. `harness/feedback-review`에서 직접 검토한 뒤 `skills/da-development-method/scripts/sync-decisions.py --db <private-review.sqlite> --catalog <catalog.json> --output <private-policy/personal-decisions.json>`으로 내보냅니다. `--check`는 원본을 변경하지 않는 검증입니다. 적용표는 이유와 범위를 읽고 별도로 작성합니다. 기본 라우터는 결정적 분류이며 경험의 의미 검색이나 실제 스킬 실행을 수행하지 않습니다.
