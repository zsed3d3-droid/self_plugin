# 캡처 픽셀을 전달하는 Codex 검수

확인일: 2026-10-29. [OpenAI CLI 공식 문서](https://learn.chatgpt.com/docs/cli/reference)와 로컬 Codex 0.165의 `exec --help`, `exec resume --help`에서 `--image` 지원을 확인했다. 이 경로는 전용 로그인으로 실행하는 native Codex CLI이며 별도 REST API key 경로를 추가하지 않는다.

## 입력과 실행

기존 `/turns`의 `scope`, `request_id`, `prompt`, 선택적 `model`을 유지하고 `images`만 선택적으로 추가한다.

```json
{
  "scope": "design:project:task:critique",
  "request_id": "UUID",
  "prompt": "검수 요구와 I1 등의 근거 메타데이터",
  "images": [{"mime_type": "image/png", "data_base64": "BASE64_BYTES"}]
}
```

- PNG/JPEG/WebP 정지영상만 받는다. 최대 3장, 장당 디코딩된 파일 4 MiB, 합계 12 MiB, 장당 16,000,000 pixels와 변 길이 16,000 이하로 제한한다. Pillow 13.0.0으로 format·MIME 일치와 실제 decode를 확인한다. SVG/HTML, data URL, 경로·URL 필드는 입력으로 받지 않는다.
- 검증은 DB 요청·세션 생성 전에 한다. 이미지가 없으면 이전 텍스트 요청 digest를 유지한다. 이미지가 있으면 순서대로 MIME과 원본 바이트 SHA-256을 포함하므로 같은 UUID에 다른 이미지는 409다.
- 이미지 요청에서 전용 로그인 파일이 없으면 DB 진입 전 `503 / not_started / codex_authentication_required`다. 파일 존재 확인은 로그인 유효성·모델 접근 권한의 완전한 검증이 아니다.
- 검증한 바이트를 요청 전용 `/tmp` 디렉터리의 mode 600 파일에 쓰고, 새 실행 및 동일 thread의 resume에 `--image FILE`을 반복한다. 이미지 옵션 뒤 `--`로 옵션을 끝내고 resume UUID와 마지막 stdin prompt `-`를 둬 variadic image 옵션과 구분한다. 프로세스 종료/정리 뒤 임시 파일을 삭제하고 제품의 원본 캡처는 보존한다.
- 완료 결과는 `image_count`와 `images:[{mime_type,sha256,width,height}]` 영수증을 포함한다. Base64·이미지 파일 경로·인증 토큰을 DB 이벤트나 Hook 보고서에 저장하지 않는다. Codex가 관리하는 세션과 제공자 보존 정책을 이 임시 파일 정리로 변경했다고 주장하지 않는다.

## Hook의 시각 검수 계약

`checks.critique.enabled=true`, `required=true`, `require_visual=true`일 때 기존 browser stage가 통과한 fresh/hash-bound PNG 캡처만 읽는다. 경로·파일·record hash를 다시 확인하고 동일한 크기/pixel 제한을 적용한다. 새 캡처 서비스나 임의의 제품 파일 수집은 하지 않는다.

이미지 순서대로 `I1…` ID를 부여해 픽셀을 첨부한다. `O1`은 테스트 작성자가 기록한 행동, `S1…`은 소스이며 DESIGN.md·계약·개인 판단 원문/이유와 적용 범위를 함께 유지한다. 다음을 구분하도록 요구한다.

- `image_observation`: 공급된 픽셀에 보이는 현상. 해당 I ID를 인용한다.
- `recorded_behavior`: browser 기록의 행동 주장. 정지 화면만으로 동작 성공을 만들어내지 않는다.
- `source_inference`: 소스에서 추론한 동작/원인.
- `hypothesis`: 아직 확인하지 않은 원인·영향.

응답의 `visual_coverage`는 `inspected_supplied_images` 또는 `inconclusive`다. pass는 모든 공급 I ID의 확인, 일치하는 브로커 영수증, inspected coverage가 있어야 한다. 소스 전용 모드에서는 기존 `not_inspected` 계약을 유지한다. 구조화된 검토 표시는 모델의 보고이며 실제 사용자의 만족이나 모든 화면·상태 검증을 증명하지 않는다.

이미지 부재·변경·invalid payload·미인증은 시각 검수 pass가 아니다. 로그인 미완료의 명시적 `not_started`와 실행 후 `completion_unconfirmed`를 구분한다. 후자는 동일 세션·불명확한 결과·실패 예산을 보존하고 새 UUID나 세션으로 자동 재실행하지 않는다. 기존 Hook의 hash/cache·max budget·사용자 판단 절차를 그대로 따른다.

## 검증 범위

오프라인 fake Codex/브로커, 테스트 전용 무작위 PostgreSQL schema, 합성 이미지로 입력 검증·argv·exec/resume·600 권한·파일 정리·UUID 충돌·영수증·근거 전달과 기존 텍스트/Hook 회귀를 확인한다. 실제 전용 로그인과 live multimodal inference가 확인되기 전에는 구현 계약 검증으로만 보고하며, 실제 시각 판단의 품질이나 운영 연결 완료로 보고하지 않는다.

로컬 0.165의 `codex debug prompt-input --image <합성 PNG> -- VISION_PARSER_SENTINEL`도 실행했다. 종료 코드 0, model-visible JSON에 `input_image` 1개와 별도 sentinel 텍스트가 보존됨을 확인했다. 이는 이미지/positional 분리의 native 렌더링 확인이며 실제 `exec/resume`의 제공자 호출이나 시각 판단 품질을 검증한 것은 아니다.
