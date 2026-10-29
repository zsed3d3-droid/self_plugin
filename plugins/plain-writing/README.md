# Plain Writing 0.1.0

AI가 답변·설명·요약·보고서를 직접적이고 구체적인 문장으로 작성하도록 돕는 `$plain-writing` 스킬이다.

다루는 표현은 불필요한 `A가 아니라 B`, `B를 말하는 것은 아니다`, `B가 검증된 건 아니다`, `A이지만 B는 아니다`, 정책·능력 안내 서론, 상투적인 강조·과장과 반복 결론이다. 사실·근거·필요한 정정·미확인 범위는 유지한다.

## 사용

DA Plugin Sets marketplace에서 **Plain Writing**을 설치한 환경에서 호출한다.

```text
$plain-writing 질문에 바로 답하고 불필요한 대조·부정·과장·반복을 덜어줘.
사실과 필요한 조건은 유지해줘.
```

```text
$plain-writing 아래 답변을 자연스럽게 다듬어줘. 교정한 본문만 보여줘.
```

```text
$plain-writing 이 보고서의 AI 상투 표현을 검토하고 문제 구절·이유·대안을 알려줘.
```

[스킬 본문](skills/plain-writing/SKILL.md)에 생성·교정·검토 기준을 모았다. [교정 예시](skills/plain-writing/references/examples.md)는 가상 문장과 의미 보존 사례이고, [정리 근거](skills/plain-writing/references/sources.md)는 SEAM·Craft·CosPedia에서 반영한 텍스트 지침을 기록한다.

## 적용 방식

기존 생성 요청의 지침으로 사용하고, 답변을 내보내기 전에 같은 작업 안에서 문장을 점검한다. 사실과 표현을 함께 검토하며 개별 단어·줄을 자동 삭제하지 않는다. 구조화 출력에는 기존 Schema와 출처 ID를 유지한다.

플러그인은 텍스트 답변의 글쓰기에 한정한다. 추가 실행기 없이 기존 텍스트 생성 작업의 지침으로 사용한다. 원본 SEAM·CosPedia와 기존 통합 규칙은 그대로 유지한다. 사용 중인 호스트가 스킬을 발견하고 로드하는 설정을 따른다.

## 검증

저장소 루트에서 실행한다.

```sh
python3 -B plugins/plain-writing/tests/test_package.py
bash scripts/doctor.sh
```

패키지 검사는 manifest 일치·marketplace/스킬 연결·문서 링크를 확인한다. 답변 품질은 루트 `evals/cases.md`의 PW 사례로 평가하며, 실제 모델 평가의 실행 여부와 패키지 검사 결과를 구분한다.
