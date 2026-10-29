# Meng To의 구현 절차와 ThreeUI 적용 범위

확인일 2026-10-29. 정확한 commit·파일·반입 여부는 [mengto-research.json](../sources/mengto-research.json)에 있다. 이번에는 필요한 skill 문서와 MIT license만 보존했다. 저장소의 설치기·자동화·외부 발송·유료 provider를 실행하지 않았다.

## 설계 결정과 반복의 단위를 작게 한다

[MengTo/Skills](https://github.com/MengTo/Skills)의 design-first-ui-prompting에서 과업·독자·출력·위계·타입·색·제약을 구체화하는 절차를 가져온다. 한 번에 1~2개의 원인을 바꿔 결과를 비교하면 왜 나아졌는지 추적하기 쉽다. 이를 모든 작업의 고정 절차나 상시 hero·단일 accent·특정 유료 글꼴 사용 규칙으로 만들지 않는다. 이미 결정한 명확한 수정은 바로 수행한다.

스크린샷·상태·인터랙션 근거를 프로젝트별 reference pack에 보관한다. current user의 ‘모든 결과 보관’ 요청이 우선하므로 원본·실패한 시도·이전 결과를 삭제하지 않는다. 공개 배포 권한이 없는 자료는 연구 기록으로 두고 제품의 재사용 자산과 구분한다.

## 레퍼런스와 결과의 차이도 확인한다

audit-reference-originality에서 실제 구현과 참고 자료의 구체적인 비교 방식을 가져온다. 텍스트·브랜드·수치·이미지·구성·모션의 유사성을 해당 위치와 함께 보고, 일반적인 목록/모달 같은 공통 문법과 고유한 표현 복제를 구분한다. 법적 표절 판정을 내리거나 색만 바꾼 뒤 새 디자인이라고 하지 않는다.

원문의 과거 자료 삭제 제안은 가져오지 않는다. 이 실험에서는 모든 산출물을 보존하고 다음 iteration에서 어떻게 개선했는지 연결한다. 참조되지 않은 파일이 없다고 하거나 접근하지 못한 전체 자료를 검토했다고 하지 않는다.

## ThreeUI는 맞는 과업에서 실제 컴포넌트를 검증한다

[MengTo/threeui](https://github.com/MengTo/threeui)는 무료 Community 구현과 자산 경계를 구분한다. README·MIT LICENSE·ASSET-LICENSES·package와 catalog의 실제 lazy import 코드를 확인했다. 현재는 컴포넌트를 가져와 실행한 단계가 아니므로 제품 사용·GPU 성능·접근성 통과로 기록하지 않는다.

3D·자료 탐색·시각 설명처럼 공간/움직임이 이해에 도움이 되는 제품에서 필요한 무료 컴포넌트만 선택한다. 일반 업무 폼에 shader 배경과 커서 효과를 자동 추가하지 않는다. 버전 호환, local assets, 키보드/텍스트 대체, reduced motion, WebGL 실패, 작은 화면, 실제 성능을 확인한 뒤 적용한다.

저장소 코드의 MIT와 remote catalog thumbnail/video의 권리는 다르다. Pro/Beta source·유료 폰트·entitlement CLI를 도입하지 않는다. 사용한 Community source와 실제 반입 자산별 LICENSE/NOTICE를 제품에 보존한다.
