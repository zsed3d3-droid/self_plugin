# Dedicated Codex Broker

원래 구현의 Broker를 독립 Compose 프로젝트로 묶었습니다. PostgreSQL이 scope별 세션·요청 UUID·결과·이벤트를 보관하고, 전용 `/codex` 볼륨이 Codex의 자체 세션을 유지합니다. 같은 주제의 새 요청은 그 주제의 thread를 재개합니다. 완료 불명 요청은 자동 재실행하지 않습니다.

```sh
cd harness/codex-broker
python3 init-env.py
docker compose up -d --build
```

API는 `http://127.0.0.1:8853`에만 바인딩됩니다. DB는 호스트에 노출하지 않습니다. `/health`의 인증 파일 존재는 실제 모델 접근 성공을 뜻하지 않습니다. 의존성은 개발 당시의 재현용 고정 버전이며 자동 업그레이드하지 않습니다.

**인증은 미구성입니다.** 배포 과정에서는 새 로그인을 시작하지 않았고 기존 계정 인증을 복사하지 않았습니다. 나중에 사용자가 전용 로그인을 진행할 때만 `docker compose exec broker codex login --device-auth`를 사용합니다. 실제 모델/이미지 검수는 그 전까지 미실행입니다.

상세 API·요청 멱등성·불명 상태·실패 예산·이미지 제한은 [실행 계약](broker/README.txt)을 참고합니다. 공급자의 overload 알림을 다루는 `../capacity-retry`와 이 Broker의 결과 불명 정책은 다릅니다. 불명 상태를 용량 오류라고 추정해 재전송하면 안 됩니다.

기존 단위·통합 검증은 가짜 Codex 실행기와 별도 PostgreSQL 스키마를 사용합니다. 공개본에 테스트를 포함했지만 DB 접속이 없으면 통합 테스트는 skip입니다. 개인 세션이나 인증 자료는 포함하지 않습니다.
