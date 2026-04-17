# Credits

## 원본 프로젝트 (Upstream)

이 저장소는 다음 오픈소스 프로젝트를 기반으로 합니다.

- **Project**: [lexguard-mcp](https://github.com/SeoNaRu/lexguard-mcp)
- **Author**: [SeoNaRu](https://github.com/SeoNaRu)
- **License**: MIT (커스텀 상업용 고지 조항 포함)
- **Description**: 국가법령정보센터 Open API를 AI가 이해하기 쉬운 형태로 연결한 MCP 서버

원저작자의 허가(MIT License) 하에 재배포되며, 원본의 LICENSE·저작권 고지를
그대로 유지합니다 ([LICENSE](./LICENSE) 참조).

## 본 저장소의 변경 사항

원본 MCP 서버를 Claude Skill 형태로 포팅하면서 다음을 추가/변경했습니다.

- **형식 변환**: Python FastAPI 기반 MCP 서버 → Claude Skill (단일 `SKILL.md` + Python 스크립트 기반)
- **목적**: Claude Pro 사용자가 Cowork 환경에서 MCP 서버 호스팅 없이, 로컬 Skill로 API 한도 걱정 없이 사용할 수 있도록 재구성
- **보안 처리**: 하드코딩된 개발용 API 키 제거 (`__LAW_API_KEY__` 플레이스홀더로 대체)
- **Web Builder 추가** (`docs/`): 사용자가 자기 OpenLaw API 키를 입력하면 브라우저에서 바로 커스텀 ZIP을 다운로드할 수 있는 GitHub Pages 정적 사이트
- **플랫폼 범위**: 현재 macOS/Linux 대상. Windows는 추후 지원 예정

## 외부 의존성

- **국가법령정보센터 Open API** ([open.law.go.kr](https://open.law.go.kr))
  - 본 Skill을 사용하려면 사용자가 직접 Open API 이용 신청 및 키 발급을 받아야 합니다.
  - 본 저장소는 API 키를 포함하지 않으며, 제공하지도 않습니다.

- **JSZip** (Web Builder에서 클라이언트 사이드 ZIP 생성용)
  - [JSZip](https://stuk.github.io/jszip/) — MIT License
  - CDN: `https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js`

## 문의 및 기여

- 원본 기능/버그 관련: [SeoNaRu/lexguard-mcp](https://github.com/SeoNaRu/lexguard-mcp/issues)
- 포팅/빌더 관련: 본 저장소의 Issues 탭
