# ⚖️ hanlaw-skill

> 한국 법령·판례·법령해석을 Claude에서 바로 조회하는 **Claude Skill**
>
> 원본 [SeoNaRu/lexguard-mcp](https://github.com/SeoNaRu/lexguard-mcp)(MIT) 를 Claude Skill로 포팅해 Claude Pro 사용자가 **Cowork 환경에서 API 한도 걱정 없이** 로컬로 쓸 수 있도록 재구성했습니다.

<p align="center">
  <a href="https://dogdogfat.github.io/hanlaw-skill/">
    <img alt="Web Builder" src="https://img.shields.io/badge/%F0%9F%9A%80%20%EC%9B%B9%20%EB%B9%8C%EB%8D%94%20%EC%97%B4%EA%B8%B0-API%20%ED%82%A4%20%EC%9E%85%EB%A0%A5%20%E2%86%92%20ZIP%20%EB%8B%A4%EC%9A%B4%EB%A1%9C%EB%93%9C-0b5ed7?style=for-the-badge&labelColor=1e3a8a" />
  </a>
  <br/>
  <sub>
    <a href="https://img.shields.io/badge/license-MIT-blue">
      <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue" />
    </a>
    &nbsp;
    <a href="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey">
      <img alt="Platform" src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey" />
    </a>
    &nbsp;
    <a href="https://code.claude.com/docs/en/skills">
      <img alt="Claude Skill" src="https://img.shields.io/badge/Claude-Skill-orange" />
    </a>
  </sub>
</p>

## 🚀 바로 시작하기

### 👉 [**웹 빌더로 설치하기 (클릭)**](https://dogdogfat.github.io/hanlaw-skill/)

1. [open.law.go.kr](https://open.law.go.kr) 가입 → Open API 신청 (**자동 승인**)
2. 웹 빌더에 API 키 붙여넣기
3. ZIP 다운로드 → `~/.claude/skills/hanlaw-skill/` 에 풀기
4. Claude 재시작 후 "근로기준법 제50조 알려줘" 로 테스트

> 🔒 입력한 API 키는 브라우저 안에서만 처리되며 외부 서버로 전송되지 않습니다.

## 🎯 주요 기능

- **법령 검색**: 근로기준법, 민법 등 국가법령정보센터 전체 DB 검색
- **조문 정밀 조회**: `근로기준법 제50조 3항` 같은 특정 조항 직접 조회
- **판례 검색**: 대법원·하급심 판례 + 사건번호 직접 인식 (`2023다12345`)
- **법령해석·행정심판·헌재결정·위원회 결정문** 통합 검색
- **계약서/약관 자동 분석**: 문서 붙여넣기 → 조항별 법적 이슈 탐지
- **도메인 자동 분류** (노동·개인정보·부동산·소비자·세금·금융 등 13개)

## 📂 Skill 설치 경로 (macOS)

Claude Desktop·Claude Code 모두 동일한 경로를 사용합니다.

```
~/.claude/skills/hanlaw-skill/
```

Finder에서 `Cmd+Shift+G` → 위 경로 붙여넣기 → 웹 빌더에서 다운로드한 `hanlaw-skill` 폴더를 통째로 복사하세요. 신규 Skill 추가 시 Claude를 1회 재시작하면 됩니다(이후 파일 수정은 자동 감지).

> 공식 문서: [Extend Claude with skills](https://code.claude.com/docs/en/skills)

## 🛠 수동 설치 (개발자)

Web Builder를 쓰지 않고 이 repo를 직접 clone 하는 경우:

```bash
git clone https://github.com/dogdogfat/hanlaw-skill.git
cd hanlaw-skill/skill

# scripts/lexguard_api.py 열어서 __LAW_API_KEY__ 를 본인 키로 교체
# 또는 환경변수로 주입: export LAW_API_KEY=발급받은키

# Skill 폴더로 복사
mkdir -p ~/.claude/skills/hanlaw-skill
cp -r . ~/.claude/skills/hanlaw-skill/
```

## 📋 사용 예시

설치 후 Claude에게 이렇게 물어보세요:

```
프리랜서인데 근로자성 인정된 판례 있나요?
근로기준법 제50조 내용 알려줘
최근 3년 부당해고 판례 알려줘
개인정보 유출됐는데 법적으로 어떻게 되나요?
2023다12345 판례 찾아줘
```

## ⚖️ 면책 조항

이 Skill은 **법률 자문을 대체하지 않습니다.** API 결과는 공식 데이터 기반이지만 참고 용도이며, 구체적인 법률 판단은 반드시 변호사·법무사 등 전문가와 상의하세요.

## 🙏 크레딧

- 원본 MCP 서버: [SeoNaRu/lexguard-mcp](https://github.com/SeoNaRu/lexguard-mcp) (MIT © 2026 SeoNaRu)
- 데이터 출처: [국가법령정보센터 Open API](https://open.law.go.kr)
- 상세: [CREDITS.md](./CREDITS.md) · [LICENSE](./LICENSE)

## 📄 라이선스

MIT License. 원저작자의 라이선스에 따라 재배포됩니다. 상세는 [LICENSE](./LICENSE) 참조.
