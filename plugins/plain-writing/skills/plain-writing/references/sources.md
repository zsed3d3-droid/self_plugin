# 정리 근거

확인일: 2026-10-15. 기존 원칙을 일반적인 텍스트 답변용으로 요약·재구성했다. 아래 링크는 확인 시점의 소스다.

| 원본 | 반영한 글쓰기 원칙 |
| --- | --- |
| [SEAM writing-style.md](https://github.com/COSMAX-DA/DA_Plugin_Sets/blob/54117d2371bc16980bab458b6859c5f20d1fead9/plugins/seam/upstream/references/writing-style.md#L3) | 사실·행동·상태를 직접 설명하기, 불필요한 대조와 수사적 반전 줄이기 |
| [SEAM Writing policy](https://github.com/COSMAX-DA/DA_Plugin_Sets/blob/54117d2371bc16980bab458b6859c5f20d1fead9/plugins/seam/upstream/skills/seam/SKILL.md#L48) | 설명·판단 근거를 직접 서술하고 필요한 정정·조건을 보존하기 |
| [Craft의 문구 기준 Gate 6](https://github.com/COSMAX-DA/DA_Plugin_Sets/blob/54117d2371bc16980bab458b6859c5f20d1fead9/plugins/craft-ui-motion/rules/AGENTS.md#L26) | 근거 없는 홍보성 수식어를 구체적인 동작·결과로 바꾸기 |
| [CosPedia RagAnswerService](https://github.com/COSMAX-DA/da_service_portal/blob/7217c9e792001fce0c249bb459ed06f9eafd67c7/apps/cospedia/backend/src/main/java/com/example/ragchat/rag/RagAnswerService.java#L43) | 질문에 바로 답하기, 메타 부정·정책 서론 줄이기, 수치·부정·조건·근거와 구조화 출력 계약 보존하기 |
| [CosPedia 공통 생성 지침](https://github.com/COSMAX-DA/da_service_portal/blob/7217c9e792001fce0c249bb459ed06f9eafd67c7/apps/cospedia/backend/src/main/java/com/example/ragchat/bedrock/BedrockClaudeChatModelClient.java#L48) | 생성한 설명의 문체를 공통 지침으로 적용하고 필요한 한계를 짧게 전달하기 |
| [CosPedia CONTENT_RULES와 domain_text](https://github.com/COSMAX-DA/da_service_portal/blob/7217c9e792001fce0c249bb459ed06f9eafd67c7/apps/cospedia/processor/extraction.py#L20) | 생성·검수 메타 설명을 덜어내면서 도메인의 부정·조건·불확실성과 계획/실행 상태 보존하기 |
| [CosPedia 공통 답변 문체 설계](https://github.com/COSMAX-DA/da_service_portal/blob/7217c9e792001fce0c249bb459ed06f9eafd67c7/apps/cospedia/docs/conversation-rag-improvement-design.md#L736) | 사용자 요청 대상 유지, 부족한 범위만 설명, 짧은 예시·자체 점검 적용, 문체를 위한 추가 모델 호출 생략 |

CosPedia 코드에서는 시스템 지침을 요청에 전달하고 기존 응답 계약으로 근거·구조를 검사한다. 이 플러그인에는 그중 텍스트 작성 원칙을 반영했다. `domain_text`의 줄 삭제 정규식과 모델·검색·추출 구현은 복사하지 않았다. 문장 전체 삭제로 시험 결과·부정·조건이 손실될 수 있어 문맥과 의미를 보존하는 교정 기준을 사용한다.

SEAM의 기존 패키지와 Apache-2.0 LICENSE/NOTICE는 원래 위치에 보존한다. 이 패키지의 지침·예시는 새로 작성했으며 기존 스킬이나 CosPedia 소스를 변경하지 않는다.
