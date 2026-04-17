#!/usr/bin/env python3
"""
LexGuard API 래퍼 — 국가법령정보센터 Open API 호출 스크립트

국가법령정보센터 OpenAPI(DRF)를 직접 호출합니다.
주의: 본 스크립트가 실행되는 환경의 공인 IP가 OpenAPI 인증설정에 등록되어 있어야 합니다.

사용법:
    # 법령 검색 및 상세조회
    python3 lexguard_api.py search_law --query "근로기준법" [--page 1]
    python3 lexguard_api.py get_law --law-id "226789" [--article "1"]
    
    # 판례 검색 및 상세조회
    python3 lexguard_api.py search_prec --query "부당해고" [--page 1]
    python3 lexguard_api.py get_prec --prec-id "12345"
    
    # 그 외 조회
    python3 lexguard_api.py search_interp --query "검색어"
    python3 lexguard_api.py get_interp --interp-id "12345"
    python3 lexguard_api.py search_admrul --query "검색어"
    python3 lexguard_api.py get_admrul --admrul-id "12345"   ← NEW
    python3 lexguard_api.py search_ordin --query "검색어"
    python3 lexguard_api.py get_ordin --ordin-id "12345"     ← NEW
    python3 lexguard_api.py search_detc --query "검색어"
    python3 lexguard_api.py get_detc --detc-id "12345"

    # 행정심판 재결례 검색/상세 (NEW)
    python3 lexguard_api.py search_decc --query "과징금" [--page 1]
    python3 lexguard_api.py get_decc --decc-id "12345"

    # 위원회 결정문 검색/상세 (NEW — 11개 위원회 지원)
    python3 lexguard_api.py search_committee --query "부당해고" --committee "노동위원회"
    python3 lexguard_api.py get_committee --committee-id "12345" --committee "노동위원회"
    # 지원 위원회: 노동위원회, 공정거래위원회, 국가인권위원회, 국민권익위원회 등 11종

    # 정부 공식 서식 검색 (국가법령 별표·서식)
    python3 lexguard_api.py search_form --query "근로계약" [--kind 2] [--page 1]
        # kind: 1=별표, 2=서식(기본), 3=별지, 4=별도, 5=부록
    python3 lexguard_api.py get_form --form-id "서식일련번호"

    # 서식 파일 직접 다운로드 (search_form 결과의 flSeq 사용)
    python3 lexguard_api.py download_form --fl-seq "162953437" --out "영수증.pdf"
    python3 lexguard_api.py download_form --fl-seq "162953435" --format hwp --out "영수증.hwp"

    # ── 확장 기능 ──
    # 법령 개정 이력 조회
    python3 lexguard_api.py get_history --law-id "281875"

    # 법령 조문 내 참조 법령 체인 자동 추출
    python3 lexguard_api.py get_related --law-id "281875" [--article "163"]

    # 문서(PDF/TXT) 분석 — 개인정보 감지 + 관련 법령 탐색
    python3 lexguard_api.py analyze_doc --file "계약서.pdf" [--mask-pii]

    ※ 개인정보 처리 원칙
      - 문서 원문은 로컬에서만 처리하며 외부 서버로 전송하지 않습니다.
      - API 전송 대상: 법령명·조문번호만 (문서 내용 미포함)
      - --mask-pii 옵션 사용 시 주민번호·전화번호·이메일 등을 마스킹 후 분석합니다.

    ※ 검증 원칙 (이중검증 지원)
      - 모든 API 결과에는 api_url 필드가 포함되어 사용자가 직접 브라우저에서 확인 가능합니다.
      - 판례·법령해석 인용 시 반드시 사건번호/해석번호를 명시하세요.
      - AI가 생성한 답변은 반드시 API 결과와 대조 검증해야 합니다.
"""

import os
import re
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import pathlib
import xml.etree.ElementTree as ET
from typing import Any, Union

# ==============================================================================
# 경로 설정 (Cowork 호환 — cwd가 스킬 루트와 다를 수 있음)
# ==============================================================================
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
RESOURCES_DIR = SKILL_DIR / "resources"

# ==============================================================================
# 설정 (OpenAPI 키)
# ==============================================================================
_BUILTIN_API_KEY = "__LAW_API_KEY__"

# 환경변수가 있으면 우선 사용, 없으면 내장 키 사용
API_KEY = os.environ.get("LAW_API_KEY") or _BUILTIN_API_KEY

# verify_config, download_form, analyze_doc 은 API 키 없이도 실행 가능 (또는 부분 실행)
_NO_KEY_COMMANDS = {"verify_config", "download_form", "analyze_doc"}
if not API_KEY and not (len(sys.argv) > 1 and sys.argv[1] in _NO_KEY_COMMANDS):
    print(json.dumps(
        {"error": "LAW_API_KEY가 설정되지 않았습니다."},
        ensure_ascii=False
    ))
    sys.exit(1)

BASE_URL = "https://www.law.go.kr/DRF"
DEFAULT_DISPLAY = 20
MAX_RETRIES = 2          # 실패 시 최대 재시도 횟수
RETRY_BASE_DELAY = 1.0   # 재시도 기본 대기 시간(초)

# ==============================================================================
# 위원회 결정문 target 매핑 (원본 MCP 프로젝트에서 포팅)
# ==============================================================================
COMMITTEE_TARGET_MAP = {
    "개인정보보호위원회": "ppc",
    "금융위원회": "fsc",
    "노동위원회": "nlrc",
    "고용보험심사위원회": "eiac",
    "국민권익위원회": "acr",
    "방송미디어통신위원회": "kcc",
    "산업재해보상보험재심사위원회": "iaciac",
    "중앙토지수용위원회": "oclt",
    "중앙환경분쟁조정위원회": "ecc",
    "증권선물위원회": "sfc",
    "국가인권위원회": "nhrck",
}

# ==============================================================================
# 특별행정심판 target 매핑 (원본 MCP 프로젝트에서 포팅)
# ==============================================================================
SPECIAL_APPEAL_TARGET_MAP = {
    "조세심판원": "ttSpecialDecc",
    "해양안전심판원": "kmstSpecialDecc",
    "국민권익위원회": "acrSpecialDecc",
    "소청심사위원회": "adapSpecialDecc",
}

# ==============================================================================
# HTTP 및 XML/JSON 파싱 유틸리티
# ==============================================================================

def _build_url(endpoint: str, params: dict) -> str:
    p = dict(params)  # 원본 dict를 변경하지 않도록 복사
    p["OC"] = API_KEY
    p["type"] = "JSON"  # 기본 요청을 JSON으로 (지원하지 않으면 XML로 반환될 수 있음)
    qstr = urllib.parse.urlencode(p, quote_via=urllib.parse.quote)
    return f"{BASE_URL}/{endpoint}?{qstr}"


def _fetch(endpoint: str, params: dict, *, _retries: int = MAX_RETRIES) -> Union[dict, list, str]:
    """국가법령정보센터 DRF API 호출 및 파싱 (Retry with Exponential Backoff).

    검증 지원: 반환 결과에 api_url 필드를 포함하여 사용자가 브라우저에서 직접 확인 가능.
    """
    url = _build_url(endpoint, params)
    last_error = None
    for attempt in range(_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LexGuard-Skill/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode("utf-8")

                # 인증 실패 메시지가 포함된 구조인지 빠르게 확인
                if "사용자 정보 검증에 실패하였습니다" in data:
                    return {
                        "error": "IP 인증 실패",
                        "msg": "현재 PC의 공인 IP가 국가법령정보센터에 등록되지 않았습니다.",
                        "guide": "https://open.law.go.kr 'API인증값변경' 메뉴에서 현재 IP를 추가해주세요.",
                        "api_url": url,
                        "raw": data.strip(),
                    }

                try:
                    # 1순위: JSON 파싱 시도
                    parsed = json.loads(data)
                    # 검증용 URL 주입 (dict인 경우)
                    if isinstance(parsed, dict):
                        parsed["api_url"] = url
                    return parsed
                except json.JSONDecodeError:
                    # 2순위: XML 파싱 시도 (DRF API는 간혹 type=JSON이어도 XML을 반환함)
                    parsed = _parse_xml(data)
                    if isinstance(parsed, dict):
                        parsed["api_url"] = url
                    return parsed
        except urllib.error.HTTPError as e:
            last_error = {"error": f"HTTP {e.code}: {e.reason}", "api_url": url}
            # 4xx 클라이언트 에러는 재시도 무의미
            if 400 <= e.code < 500:
                return last_error
        except Exception as e:
            last_error = {"error": str(e), "api_url": url}

        # 재시도 대기 (exponential backoff)
        if attempt < _retries:
            time.sleep(RETRY_BASE_DELAY * (2 ** attempt))

    return last_error or {"error": "알 수 없는 오류", "api_url": url}


def _parse_xml(xml_str: str) -> dict:
    try:
        root = ET.fromstring(xml_str)
        # JSON 반환 구조와 동일하게 루트 태그를 최상단 키로 래핑
        return {root.tag: _xml_to_dict(root)}
    except ET.ParseError:
        return {"raw_response": xml_str[:2000]}


def _xml_to_dict(element: ET.Element) -> Union[dict, str]:
    """속성(Attribute)과 혼합 텍스트(Mixed Content) 누락을 방지하는 XML 파서.

    국가법령정보센터 API는 다음과 같은 XML 구조를 자주 사용합니다:
    - 속성: <법종구분 법종구분코드="A0002">법률</법종구분>
    - 혼합 콘텐츠: <조문내용>제1조 <개정>2020.1.1</개정> 한다.</조문내용>
    이 파서는 속성을 @키로, 텍스트를 #text로 보존합니다.
    """
    # 자식 노드와 속성이 모두 없는 경우 단순 텍스트만 반환
    if not element.attrib and len(element) == 0:
        return element.text.strip() if element.text else ""

    result = {}

    # 1. 속성(Attribute) 처리 — @키 형태로 보존
    for k, v in element.attrib.items():
        result[f"@{k}"] = v

    # 2. 태그 내 자체 텍스트 처리 — #text 키로 보존 (element.text)
    if element.text and element.text.strip():
        result["#text"] = element.text.strip()

    # 3. 자식 요소 재귀 파싱
    for child in element:
        tag = child.tag
        value = _xml_to_dict(child)

        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(value)
        else:
            result[tag] = value

        # 4. 혼합 텍스트(tail) 처리 — 자식 태그 뒤에 이어지는 본문 텍스트
        if child.tail and child.tail.strip():
            if "#text" in result:
                result["#text"] += " " + child.tail.strip()
            else:
                result["#text"] = child.tail.strip()

    return result


def _format_jo(article: str) -> str:
    """조문 번호(JO)를 API 요구 형식인 6자리(조번호4+가지번호2)로 변환.

    예시:
        "1"    → "000100"
        "10"   → "001000"
        "10-2" → "001002"
        "10의2" / "10의3" → "001002" / "001003"  (한글 '의' 구분자 지원)
        "000100" (이미 6자리) → "000100" (통과)
    """
    if len(article) == 6 and article.isdigit():
        return article  # 이미 올바른 형식

    # 한글 '의' 구분자 정규화 → '-'로 변환 후 처리 (예: "6의3" → "6-3")
    if "의" in article:
        article = article.replace("의", "-")

    if "-" in article:
        main_art, sub_art = article.split("-", 1)
        if main_art.isdigit() and sub_art.isdigit():
            return main_art.zfill(4) + sub_art.zfill(2)

    if article.isdigit():
        return article.zfill(4) + "00"

    # 알 수 없는 형식: 원본 반환 (None 반환으로 JO=None URL 파라미터 생성 방지)
    return article


# ==============================================================================
# 개인정보(PII) 감지·마스킹 및 문서 텍스트 추출 유틸리티
# ==============================================================================

# PIPA(개인정보보호법) 주요 대상 패턴
_PII_PATTERNS: dict[str, str] = {
    "주민등록번호": r"\d{6}-[1-4]\d{6}",
    "여권번호":     r"[A-Z]{1,2}\d{7,8}",
    "운전면허번호": r"\d{2}-[A-Z0-9]-\d{6}-\d{2}",
    "전화번호":     r"01[016789]-?\d{3,4}-?\d{4}",
    "이메일":       r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}",
    "계좌번호":     r"\d{3}-\d{2,6}-\d{4,7}",
}


def _detect_pii(text: str) -> dict[str, int]:
    """텍스트에서 개인정보 패턴을 감지하고 종류별 발견 건수를 반환.

    배포 시 주의: 반환 결과에는 실제 값이 아닌 건수만 포함합니다.
    """
    return {
        name: len(re.findall(pattern, text))
        for name, pattern in _PII_PATTERNS.items()
        if re.search(pattern, text)
    }


def _mask_pii(text: str) -> str:
    """개인정보 패턴을 '[종류명]' 마스킹 토큰으로 치환."""
    for name, pattern in _PII_PATTERNS.items():
        text = re.sub(pattern, f"[{name}]", text)
    return text


def _extract_law_refs(text: str) -> list[dict]:
    """조문·문서 텍스트에서 '○○법 제○조' 형태 법령 참조를 추출.

    Returns:
        [{"법령명": str, "조문": str}, ...] 형태의 중복 제거된 리스트
    """
    # 기본 패턴: 한글로 끝나는 법령명 + 제N조
    pattern = r"[「『\"']?([가-힣]{2,}(?:\s[가-힣]{2,6}){0,2}(?:법|령|규칙|조례))[」』\"']?\s*제\s*(\d+)\s*조"

    # 조사 목록 — 법령명 중간 단어 끝에 있으면 오매칭으로 판단
    _PARTICLES = {"은", "는", "이", "가", "을", "를", "의", "로", "와", "과", "에", "서", "게", "도"}

    def _is_valid_name(name: str) -> bool:
        """중간 단어가 조사로 끝나면 오매칭 제거."""
        words = name.split()
        for word in words[:-1]:  # 마지막 단어(법/령)는 제외
            if word[-1] in _PARTICLES:
                return False
        return True

    refs: list[dict] = []
    seen: set[tuple] = set()
    for law_name, article in re.findall(pattern, text):
        law_name = law_name.strip()
        if not _is_valid_name(law_name):
            continue
        key = (law_name, article)
        if key not in seen and len(law_name) >= 2:
            seen.add(key)
            refs.append({"법령명": law_name, "조문": article})
    return refs


def _extract_pdf_text(path: pathlib.Path) -> str:
    """PDF 텍스트 추출 — pdfplumber 우선, poppler(pdftotext) 차선.

    외부 전송 금지: 이 함수는 로컬 파일만 처리합니다.
    """
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        pass
    # fallback: poppler pdftotext
    import subprocess
    result = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(path), "-"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        return result.stdout
    raise RuntimeError(
        "PDF 추출 실패. 다음 중 하나를 설치하세요:\n"
        "  pip install pdfplumber\n"
        "  brew install poppler   (macOS)\n"
        "  choco install poppler  (Windows, Chocolatey)\n"
        "  sudo apt install poppler-utils  (Linux)"
    )



def _extract_text_from_file(file_path: str, mask: bool) -> tuple[str, dict[str, int]]:
    """파일 경로로부터 텍스트를 추출하고 PII를 감지합니다.

    Args:
        file_path: 대상 파일 경로 (.pdf / .txt / .md 지원)
        mask: True 시 PII를 마스킹한 텍스트를 반환

    Returns:
        (텍스트, {PII종류: 건수}) 튜플

    개인정보 처리 원칙:
        - 파일 내용은 이 함수 내에서만 처리됩니다.
        - 외부 API로 전송되는 것은 추출된 법령명/조문번호뿐입니다.
    """
    path = pathlib.Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"파일 없음: {path}")
    ext = path.suffix.lower()
    if ext == ".pdf":
        raw = _extract_pdf_text(path)
    elif ext in (".txt", ".md", ".text"):
        raw = path.read_text(encoding="utf-8", errors="replace")
    elif ext in (".hwp", ".hwpx"):
        raise NotImplementedError(
            "HWP 파일은 직접 파싱이 불가합니다. "
            "HWP → PDF 또는 TXT로 변환 후 다시 시도하세요."
        )
    else:
        raise ValueError(f"미지원 형식: {ext}  (지원: .pdf .txt .md)")
    pii = _detect_pii(raw)
    text = _mask_pii(raw) if mask else raw
    return text, pii


# ==============================================================================
# 각 도메인별 검색/상세 API 함수들
# ==============================================================================

def search_law(query: str, page: int = 1, display: int = DEFAULT_DISPLAY) -> None:
    """법령 목록 검색"""
    result = _fetch("lawSearch.do", {"target": "law", "query": query, "display": display, "page": page})
    _print_result("법령 검색", query, result)


def get_law(law_id: str, article: str = "") -> None:
    """법령 상세 조회 (특정 조문 조회 포함)"""
    params = {"target": "law", "MST": law_id}
    if article:
        params["JO"] = _format_jo(article)
    result = _fetch("lawService.do", params)
    _print_result("법령 상세", law_id, result)


def search_prec(query: str, page: int = 1, display: int = DEFAULT_DISPLAY) -> None:
    """판례 검색"""
    result = _fetch("lawSearch.do", {"target": "prec", "query": query, "display": display, "page": page})
    _print_result("판례 검색", query, result)


def get_prec(prec_id: str) -> None:
    """판례 상세 조회"""
    result = _fetch("lawService.do", {"target": "prec", "ID": prec_id})
    _print_result("판례 상세", prec_id, result)


def search_interp(query: str, page: int = 1, display: int = DEFAULT_DISPLAY) -> None:
    """법령해석례 검색"""
    result = _fetch("lawSearch.do", {"target": "expc", "query": query, "display": display, "page": page})
    _print_result("법령해석 검색", query, result)


def get_interp(interp_id: str) -> None:
    """법령해석례 상세 조회"""
    result = _fetch("lawService.do", {"target": "expc", "ID": interp_id})
    _print_result("법령해석 상세", interp_id, result)


def search_admrul(query: str, page: int = 1, display: int = DEFAULT_DISPLAY) -> None:
    """행정규칙(훈령/예규/고시 등) 검색"""
    result = _fetch("lawSearch.do", {"target": "admrul", "query": query, "display": display, "page": page})
    _print_result("행정규칙 검색", query, result)


def get_admrul(admrul_id: str) -> None:
    """행정규칙 상세 조회"""
    result = _fetch("lawService.do", {"target": "admrul", "ID": admrul_id})
    _print_result("행정규칙 상세", admrul_id, result)


def search_ordin(query: str, page: int = 1, display: int = DEFAULT_DISPLAY) -> None:
    """자치법규(조례/규칙) 검색"""
    result = _fetch("lawSearch.do", {"target": "ordin", "query": query, "display": display, "page": page})
    _print_result("자치법규 검색", query, result)


def get_ordin(ordin_id: str) -> None:
    """자치법규 상세 조회"""
    result = _fetch("lawService.do", {"target": "ordin", "ID": ordin_id})
    _print_result("자치법규 상세", ordin_id, result)


def search_detc(query: str, page: int = 1, display: int = DEFAULT_DISPLAY) -> None:
    """헌법재판소 결정문 검색"""
    result = _fetch("lawSearch.do", {"target": "detc", "query": query, "display": display, "page": page})
    _print_result("헌재결정 검색", query, result)


def get_detc(detc_id: str) -> None:
    """헌법재판소 결정문 상세 조회"""
    result = _fetch("lawService.do", {"target": "detc", "ID": detc_id})
    _print_result("헌재결정 상세", detc_id, result)


# ==============================================================================
# 행정심판 재결례 (target=decc) — 원본 MCP에서 포팅
# ==============================================================================

def search_decc(query: str, page: int = 1, display: int = DEFAULT_DISPLAY) -> None:
    """행정심판 재결례 검색"""
    result = _fetch("lawSearch.do", {"target": "decc", "query": query, "display": display, "page": page})
    _print_result("행정심판 검색", query, result)


def get_decc(decc_id: str) -> None:
    """행정심판 재결례 상세 조회"""
    result = _fetch("lawService.do", {"target": "decc", "ID": decc_id})
    _print_result("행정심판 상세", decc_id, result)


# ==============================================================================
# 위원회 결정문 (11개 위원회) — 원본 MCP에서 포팅
# ==============================================================================

def search_committee(query: str, committee: str, page: int = 1, display: int = DEFAULT_DISPLAY) -> None:
    """위원회 결정문 검색

    Args:
        query: 검색어
        committee: 위원회명 (예: 노동위원회, 국가인권위원회)
            지원: 개인정보보호위원회, 금융위원회, 노동위원회, 고용보험심사위원회,
                  국민권익위원회, 방송미디어통신위원회, 산업재해보상보험재심사위원회,
                  중앙토지수용위원회, 중앙환경분쟁조정위원회, 증권선물위원회, 국가인권위원회
    """
    target = COMMITTEE_TARGET_MAP.get(committee)
    if not target:
        print(json.dumps({
            "error": f"지원하지 않는 위원회: {committee}",
            "지원_위원회_목록": list(COMMITTEE_TARGET_MAP.keys()),
        }, ensure_ascii=False, indent=2))
        return
    result = _fetch("lawSearch.do", {"target": target, "query": query, "display": display, "page": page})
    _print_result(f"위원회 결정 검색 [{committee}]", query, result)


def get_committee(committee_id: str, committee: str) -> None:
    """위원회 결정문 상세 조회"""
    target = COMMITTEE_TARGET_MAP.get(committee)
    if not target:
        print(json.dumps({
            "error": f"지원하지 않는 위원회: {committee}",
            "지원_위원회_목록": list(COMMITTEE_TARGET_MAP.keys()),
        }, ensure_ascii=False, indent=2))
        return
    result = _fetch("lawService.do", {"target": target, "ID": committee_id})
    _print_result(f"위원회 결정 상세 [{committee}]", committee_id, result)


# ==============================================================================
# 특별행정심판 재결례 (조세심판원, 해양안전심판원 등) — 원본 MCP에서 포팅
# ==============================================================================

def search_special_appeal(query: str, tribunal: str, page: int = 1, display: int = DEFAULT_DISPLAY) -> None:
    """특별행정심판 재결례 검색

    Args:
        query: 검색어
        tribunal: 심판원명 (예: 조세심판원, 해양안전심판원)
            지원: 조세심판원, 해양안전심판원, 국민권익위원회, 소청심사위원회
    """
    target = SPECIAL_APPEAL_TARGET_MAP.get(tribunal)
    if not target:
        print(json.dumps({
            "error": f"지원하지 않는 심판원: {tribunal}",
            "지원_심판원_목록": list(SPECIAL_APPEAL_TARGET_MAP.keys()),
        }, ensure_ascii=False, indent=2))
        return
    result = _fetch("lawSearch.do", {"target": target, "query": query, "display": display, "page": page})
    _print_result(f"특별행정심판 검색 [{tribunal}]", query, result)


def get_special_appeal(appeal_id: str, tribunal: str) -> None:
    """특별행정심판 재결례 상세 조회"""
    target = SPECIAL_APPEAL_TARGET_MAP.get(tribunal)
    if not target:
        print(json.dumps({
            "error": f"지원하지 않는 심판원: {tribunal}",
            "지원_심판원_목록": list(SPECIAL_APPEAL_TARGET_MAP.keys()),
        }, ensure_ascii=False, indent=2))
        return
    result = _fetch("lawService.do", {"target": target, "ID": appeal_id})
    _print_result(f"특별행정심판 상세 [{tribunal}]", appeal_id, result)


# kind 코드 → 사람이 읽기 쉬운 이름 매핑
_FORM_KIND_NAMES = {
    "1": "별표",
    "2": "서식",
    "3": "별지",
    "4": "별도",
    "5": "부록",
}


def search_form(query: str, kind: int = 2, page: int = 1, display: int = DEFAULT_DISPLAY) -> None:
    """정부 공식 서식 검색 — 국가법령 별표·서식(licbyl) API

    Args:
        query: 검색어 (서식명 또는 법령명)
        kind:  1=별표, 2=서식(기본), 3=별지, 4=별도, 5=부록
        page:  페이지 번호
        display: 결과 개수 (최대 100)
    """
    kind_name = _FORM_KIND_NAMES.get(str(kind), "서식")
    result = _fetch(
        "lawSearch.do",
        {
            "target": "licbyl",
            "query": query,
            "knd": kind,       # 별표 종류
            "search": 1,       # 1=서식명 검색 (2=법령명, 3=본문)
            "display": display,
            "page": page,
        },
    )
    _print_result(f"정부서식 검색 [{kind_name}]", query, result)


def get_form(form_id: str) -> None:
    """정부 공식 서식 상세 조회

    Args:
        form_id: 서식 일련번호 (search_form 결과의 일련번호 필드)
    """
    result = _fetch("lawService.do", {"target": "licbyl", "ID": form_id})
    _print_result("정부서식 상세", form_id, result)


def download_form(fl_seq: str, out_path: str, fmt: str = "pdf") -> None:
    """정부 공식 서식 파일 직접 다운로드 — Referer 헤더 방식

    law.go.kr 다운로드 엔드포인트는 브라우저 세션 없이도
    Referer 헤더만 있으면 파일을 반환합니다.

    Args:
        fl_seq:   파일 일련번호 — search_form 결과의
                  '별표서식파일링크' 또는 '별표서식PDF파일링크'에서
                  flSeq 파라미터 값을 복사하세요.
        out_path: 저장할 파일 경로 (예: "./영수증.pdf")
        fmt:      'pdf' 또는 'hwp' (Content-Type 확인용, 기본: pdf)
    """
    # bylClsCd=110202 는 별표·서식 파일 구분 코드 (법령 서식 고정값)
    url = f"https://www.law.go.kr/flDownload.do?flSeq={fl_seq}&bylClsCd=110202"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://www.law.go.kr/",
        "Accept": "*/*",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()

        # 에러 HTML 페이지 반환 여부 확인 (파일이 아닌 HTML이면 에러)
        if b"<html" in data[:200].lower() or "죄송" in data[:500].decode("utf-8", errors="ignore"):
            print(json.dumps({
                "error": "다운로드 실패 — 서버가 HTML 에러 페이지를 반환했습니다.",
                "cause": "flSeq가 잘못되었거나 해당 파일이 현재 법령 기준으로 만료되었을 수 있습니다.",
                "url": url,
            }, ensure_ascii=False, indent=2))
            return

        # 자동 확장자 결정
        resolved_path = out_path
        if not out_path.lower().endswith((".pdf", ".hwp", ".hwpx")):
            ext = ".hwp" if "hwp" in content_type.lower() else ".pdf"
            resolved_path = out_path + ext

        save_path = pathlib.Path(resolved_path).expanduser().resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(data)

        print(json.dumps({
            "status": "success",
            "saved_to": str(save_path),
            "file_size_bytes": len(data),
            "content_type": content_type.strip(),
            "url": url,
        }, ensure_ascii=False, indent=2))

    except urllib.error.HTTPError as e:
        print(json.dumps({"error": f"HTTP {e.code}: {e.reason}", "url": url}, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e), "url": url}, ensure_ascii=False, indent=2))


# ==============================================================================
# 확장 기능: 법령 연혁 / 관련 법령 체인 / 문서 분석
# ==============================================================================

def get_history(law_id: str) -> None:
    """법령 개정 이력 조회.

    현재 법령의 법령명을 기준으로 전체 개정 이력(구법령 포함)을 조회합니다.
    법령이 오늘 시행됐는데 링크가 깨지는 문제처럼 개정 추적에 활용 가능합니다.
    """
    # 1단계: 법령 기본 정보 조회 (법령명 획득)
    current = _fetch("lawService.do", {"target": "law", "MST": law_id})
    law_info = current.get("법령", {})
    basic = law_info.get("기본정보", {})
    law_name: str = basic.get("법령명_한글", "")
    if not law_name:
        _print_result("법령 연혁", law_id, {"error": "법령 정보를 찾을 수 없습니다. law_id를 확인하세요."})
        return

    # 2단계: 동일 법령명으로 전체 버전 검색 (display=100으로 넉넉하게)
    history_raw = _fetch("lawSearch.do", {
        "target": "law", "query": law_name, "display": 100, "page": 1,
    })
    laws = history_raw.get("LawSearch", {}).get("law", [])
    if isinstance(laws, dict):
        laws = [laws]

    # 3단계: 법령명 앞 4글자로 필터 (유사명 법령 제외)
    prefix = law_name[:4]
    history: list[dict] = []
    for law in laws:
        if not str(law.get("법령명한글", "")).startswith(prefix):
            continue
        history.append({
            "법령일련번호": law.get("법령일련번호"),
            "제개정구분":   law.get("제개정구분명"),
            "공포번호":     law.get("공포번호"),
            "공포일자":     law.get("공포일자"),
            "시행일자":     law.get("시행일자"),
            "현행여부":     "✅ 현행" if law.get("현행연혁코드") == "현행" else "📁 구법령",
        })

    history.sort(key=lambda x: x.get("공포일자") or "", reverse=True)
    _print_result("법령 연혁", law_name, {
        "법령명":         law_name,
        "조회_법령ID":    law_id,
        "총_개정_횟수":   len(history),
        "이력": history,
    })


def get_related(law_id: str, article: str = "") -> None:
    """법령 조문에서 참조하는 관련 법령을 자동으로 체인 추출.

    조문 텍스트에서 '○○법 제○조' 패턴을 파싱하고 각 법령을 API로 조회합니다.
    article 미지정 시 법령 전체를 대상으로 합니다 (응답이 클 수 있음).
    """
    params: dict = {"target": "law", "MST": law_id}
    if article:
        params["JO"] = _format_jo(article)

    result = _fetch("lawService.do", params)
    law_info = result.get("법령", {})
    law_name: str = law_info.get("기본정보", {}).get("법령명_한글", law_id)

    # 조문 텍스트 수집
    조문_data = law_info.get("조문", {})
    units = 조문_data.get("조문단위", [])
    if isinstance(units, dict):
        units = [units]

    all_text = ""
    for unit in units:
        all_text += " " + str(unit.get("조문내용", ""))
        항_list = unit.get("항", [])
        if isinstance(항_list, dict):
            항_list = [항_list]
        for 항 in 항_list:
            all_text += " " + str(항.get("항내용", ""))

    refs = _extract_law_refs(all_text)

    # 참조 법령 API 검색 (법령명만 전송, 원문 미포함)
    searched: list[dict] = []
    for ref in refs[:8]:  # 과도한 API 호출 방지 — 최대 8건
        api_res = _fetch("lawSearch.do", {"target": "law", "query": ref["법령명"], "display": 1})
        found = api_res.get("LawSearch", {}).get("law", [])
        if isinstance(found, dict):
            found = [found]
        entry: dict = {"참조": f"{ref['법령명']} 제{ref['조문']}조"}
        if found:
            entry.update({
                "매칭_법령명": found[0].get("법령명한글"),
                "법령구분":   found[0].get("법령구분명"),
                "법령ID":     found[0].get("법령일련번호"),
                "시행일자":   found[0].get("시행일자"),
            })
        else:
            entry["매칭_법령명"] = None
        searched.append(entry)

    label = f"{law_name}" + (f" 제{article}조" if article else " (전체)")
    _print_result("관련 법령 체인", label, {
        "법령명":           law_name,
        "총_참조_건수":     len(refs),
        "조회_대상_건수":   len(searched),
        "관련_법령": searched,
    })


def analyze_doc(file_path: str, mask_pii_flag: bool = False, skip_search: bool = False) -> None:
    """문서(PDF/TXT) 분석 — PII 감지 + 법령 참조 추출 + 관련 법령 조회.

    ┌─────────────────────────────────────────────────────────────┐
    │ 개인정보 처리 원칙 (배포 적용)                                │
    │ 1. 문서 원문은 이 프로세스 내에서만 처리합니다.              │
    │ 2. 외부 API 전송 데이터: 법령명·조문번호만 (원문 미전송)     │
    │ 3. --mask-pii 사용 시 주민번호·전화번호 등을 분석 전 제거   │
    │ 4. 분석 결과에 실제 PII 값은 포함하지 않습니다.             │
    └─────────────────────────────────────────────────────────────┘
    """
    result: dict[str, Any] = {
        "file": str(pathlib.Path(file_path).expanduser().resolve()),
        "pii_masking_applied": mask_pii_flag,
    }

    # ── 텍스트 추출 ──
    try:
        text, pii = _extract_text_from_file(file_path, mask=mask_pii_flag)
    except (FileNotFoundError, ValueError, NotImplementedError, RuntimeError) as e:
        result["error"] = str(e)
        _print_result("문서 분석", file_path, result)
        return

    # ── PII 감지 결과 (건수만, 실제 값 미포함) ──
    if pii:
        note = (
            "ℹ️  --mask-pii 적용: 분석 시 마스킹 처리됨"
            if mask_pii_flag
            else "⚠️  개인정보 포함 가능 — --mask-pii 옵션으로 처리 전 마스킹을 권장합니다."
        )
        result["pii_detected"] = {"items": pii, "note": note}
    else:
        result["pii_detected"] = {"items": {}, "note": "패턴 기반 개인정보 미감지"}

    # ── 법령 참조 추출 ──
    refs = _extract_law_refs(text)
    result["law_references"] = {
        "count": len(refs),
        "items": refs,
    }

    # ── 관련 법령 API 조회 (--skip-search 미사용 시 + API_KEY 필요) ──
    if not skip_search and refs and API_KEY:
        unique_laws = list({r["법령명"] for r in refs})[:5]  # 최대 5개
        searched: list[dict] = []
        for law_name in unique_laws:
            api_res = _fetch("lawSearch.do", {"target": "law", "query": law_name, "display": 2})
            found = api_res.get("LawSearch", {}).get("law", [])
            if isinstance(found, dict):
                found = [found]
            for f in found:
                searched.append({
                    "검색어":   law_name,
                    "법령명":   f.get("법령명한글"),
                    "법령구분": f.get("법령구분명"),
                    "시행일자": f.get("시행일자"),
                    "법령ID":   f.get("법령일련번호"),
                })
        result["related_laws_api"] = searched
    elif not API_KEY:
        result["related_laws_api"] = "LAW_API_KEY 미설정 — 법령 조회 건너뜀 (PII 감지 및 참조 추출은 정상 완료)"

    _print_result("문서 분석", file_path, result)


# ==============================================================================
# 계약서/약관 분석 (원본 MCP SituationGuidanceService에서 포팅)
# ==============================================================================

# 문서 타입별 시그널 (키워드, 가중치)
_DOC_TYPE_SIGNALS: dict[str, list[tuple[str, int]]] = {
    "labor": [
        ("갑", 2), ("을", 2), ("용역", 3), ("프리랜서", 4), ("위탁", 2),
        ("업무", 1), ("지시", 2), ("출퇴근", 3), ("근로", 4), ("임금", 3),
        ("사용종속", 4), ("지휘감독", 4), ("위장도급", 5), ("4대보험", 3),
        ("근로계약", 5), ("수당", 2), ("퇴직금", 3), ("해고", 3),
    ],
    "lease": [
        ("임대인", 5), ("임차인", 5), ("보증금", 4), ("전세", 5),
        ("임대차", 5), ("월세", 4), ("임차료", 4), ("명도", 4),
        ("임대보증금", 5), ("원상복구", 3), ("계약갱신", 4),
    ],
    "terms": [
        ("회원", 2), ("이용약관", 5), ("서비스", 1), ("청약철회", 3),
        ("환불", 2), ("면책", 2), ("약관", 3), ("콘텐츠", 1),
        ("서비스 이용", 3), ("약관 변경", 4),
    ],
}

# 조항별 쟁점 키워드
_CLAUSE_ISSUE_KEYWORDS: dict[str, list[str]] = {
    "즉시 해지": ["즉시 해지", "즉시 해약", "통보 없이 해지", "일방적 해지"],
    "보증금 반환 지연": ["보증금 반환", "보증금 미반환", "일자 이내 반환"],
    "일방 기준 준용": ["갑의 기준", "갑이 정한", "갑이 정하는", "일방적 결정"],
    "갱신/연장 불리": ["자동 갱신", "자동 연장", "갱신 거절", "갱신 요구"],
    "환불 불가": ["환불 불가", "반환하지 아니", "환불되지 않", "반환하지 않"],
    "면책": ["면책", "책임을 지지 아니", "책임을 지지 않", "손해의 책임"],
    "약관 일방 변경": ["약관을 변경", "약관 변경 시", "사전 통지"],
    "관할 불리": ["관할 법원", "전속관할", "합의관할"],
    "위약금": ["위약금", "위약벌", "손해배상 예정"],
    "경쟁 금지": ["경업 금지", "경쟁 금지", "겸업 금지"],
}

# 문서 타입별 추천 검색어
_DOC_TYPE_QUERIES: dict[str, list[str]] = {
    "labor": [
        "근로기준법 근로자", "근로계약 해지 요건",
        "용역계약 근로자성 판단 판례", "위장도급 근로자성",
    ],
    "lease": [
        "주택임대차보호법 보증금 반환", "임대차 계약 갱신 요건",
        "임대차보호법 대항력", "임대차 보증금 우선변제",
    ],
    "terms": [
        "약관규제법 불공정약관", "전자상거래법 청약철회",
        "약관규제법 면책조항", "약관 일방 변경 판례",
    ],
    "other": [
        "민법 계약 해지", "계약 손해배상",
    ],
}


def _infer_document_type(text: str) -> str:
    """텍스트 키워드 기반 문서 타입 추론.

    Returns:
        'labor' | 'lease' | 'terms' | 'other'
    """
    scores: dict[str, int] = {}
    for doc_type, signals in _DOC_TYPE_SIGNALS.items():
        scores[doc_type] = sum(w for kw, w in signals if kw in text)

    # 오탐 방지: 한쪽이 압도적이면 다른 쪽 점수 감쇄
    if scores.get("lease", 0) > 10:
        scores["labor"] = max(0, scores.get("labor", 0) - 5)
    if scores.get("labor", 0) > 10:
        scores["lease"] = max(0, scores.get("lease", 0) - 5)

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] >= 3 else "other"


def _extract_clause_issues(text: str) -> list[dict]:
    """텍스트에서 조항(제N조)을 추출하고 쟁점 키워드를 매핑."""
    # 조항 경계 분리
    clause_pattern = re.compile(r"(제\s*\d+\s*조[의]?\s*(?:[\d]*)?(?:\s*\([^)]+\))?)", re.MULTILINE)
    parts = clause_pattern.split(text)

    clauses: list[dict] = []
    i = 1
    while i < len(parts):
        clause_header = parts[i].strip()
        clause_body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        full_text = clause_header + " " + clause_body[:300]  # 분석 범위 제한

        # 쟁점 키워드 매칭
        issues_found: list[str] = []
        for issue_name, keywords in _CLAUSE_ISSUE_KEYWORDS.items():
            if any(kw in full_text for kw in keywords):
                issues_found.append(issue_name)

        clauses.append({
            "clause": clause_header,
            "snippet": clause_body[:200],
            "issues": issues_found,
        })
        i += 2

    return clauses


def _generate_clause_hints(clause_issues: list[dict], doc_type: str) -> list[dict]:
    """조항별 이슈에 기반한 근거 조회 힌트(추천 검색어) 생성."""
    # 이슈 → 추천 검색어 매핑
    _ISSUE_QUERY_MAP: dict[str, dict[str, list[str]]] = {
        "labor": {
            "즉시 해지": ["근로기준법 해고 제한", "부당해고 판례"],
            "일방 기준 준용": ["근로기준법 근로조건 결정", "용역계약 근로자성"],
            "위약금": ["근로기준법 위약 예정 금지", "근로계약 위약금 판례"],
            "경쟁 금지": ["경업금지약정 효력 판례", "퇴직 후 경업금지"],
        },
        "lease": {
            "즉시 해지": ["주택임대차보호법 계약 해지", "임대차 계약 해지 사유"],
            "보증금 반환 지연": ["주택임대차보호법 보증금 반환", "보증금 반환 지연 이자"],
            "갱신/연장 불리": ["주택임대차보호법 계약갱신", "임대차 갱신 거절 사유"],
        },
        "terms": {
            "환불 불가": ["전자상거래법 청약철회", "약관규제법 불공정약관 환불"],
            "면책": ["약관규제법 면책조항 금지", "약관 면책 무효 판례"],
            "약관 일방 변경": ["약관규제법 약관 변경", "약관 변경 고지 의무"],
            "관할 불리": ["약관규제법 관할 합의 불공정"],
        },
    }

    hints: list[dict] = []
    for cl in clause_issues:
        if not cl["issues"]:
            continue
        queries: list[str] = []
        for issue in cl["issues"]:
            issue_queries = _ISSUE_QUERY_MAP.get(doc_type, {}).get(issue, [])
            queries.extend(issue_queries)
        if not queries:
            # fallback: 문서 타입 기본 검색어
            queries = _DOC_TYPE_QUERIES.get(doc_type, _DOC_TYPE_QUERIES["other"])[:1]
        hints.append({
            "clause": cl["clause"],
            "issues": cl["issues"],
            "suggested_queries": list(dict.fromkeys(queries))[:3],  # 중복 제거, 최대 3개
        })
    return hints


def analyze_contract(text: str = "", file_path: str = "", auto_search: bool = False) -> None:
    """계약서/약관 분석 — 문서 타입 추론 + 조항별 쟁점 탐지 + 법적 근거 힌트.

    ┌─────────────────────────────────────────────────────────────┐
    │ 개인정보 보호 원칙                                            │
    │ 1. 텍스트는 로컬에서만 처리 (API 미전송)                       │
    │ 2. API 전송 대상: 추천 검색어(법령명/키워드)만                  │
    │ 3. 원문은 결과에 포함하지 않음                                 │
    └─────────────────────────────────────────────────────────────┘

    Args:
        text: 분석할 계약서/약관 텍스트 (직접 입력)
        file_path: 텍스트 파일 경로 (.txt/.md 지원)
        auto_search: True 시 조항별 추천 검색어로 법령/판례 자동 검색
    """
    # 텍스트 확보
    if not text and file_path:
        try:
            path = pathlib.Path(file_path).expanduser().resolve()
            if path.suffix.lower() == ".pdf":
                text = _extract_pdf_text(path)
            elif path.suffix.lower() in (".txt", ".md", ".text"):
                text = path.read_text(encoding="utf-8", errors="replace")
            else:
                _print_result("계약서 분석", file_path, {
                    "error": f"미지원 형식: {path.suffix} (지원: .pdf .txt .md)"
                })
                return
        except Exception as e:
            _print_result("계약서 분석", file_path, {"error": str(e)})
            return

    if not text or len(text.strip()) < 20:
        _print_result("계약서 분석", "(입력 없음)", {
            "error": "분석할 텍스트가 부족합니다. --text 또는 --file로 계약서 내용을 제공하세요."
        })
        return

    # 1. 문서 타입 추론
    doc_type = _infer_document_type(text)
    doc_type_labels = {"labor": "노동/용역 계약", "lease": "임대차 계약", "terms": "이용약관", "other": "기타 계약"}

    # 2. 조항별 쟁점 추출
    clause_issues = _extract_clause_issues(text)
    issues_found = [c for c in clause_issues if c["issues"]]

    # 3. 근거 조회 힌트 생성
    clause_hints = _generate_clause_hints(clause_issues, doc_type)
    global_queries = _DOC_TYPE_QUERIES.get(doc_type, _DOC_TYPE_QUERIES["other"])

    # 4. 전체 텍스트 핵심 쟁점 탐지
    global_issues: list[str] = []
    for issue_name, keywords in _CLAUSE_ISSUE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            global_issues.append(issue_name)

    # 5. PII 감지 (건수만)
    pii = _detect_pii(text)

    result: dict[str, Any] = {
        "document_type": doc_type,
        "document_type_label": doc_type_labels[doc_type],
        "total_clauses_analyzed": len(clause_issues),
        "clauses_with_issues": len(issues_found),
        "global_issues": global_issues,
        "clause_issues": issues_found[:10],  # 가장 많은 10개
        "clause_basis_hints": clause_hints[:5],  # 최대 5개 조항
        "suggested_queries": global_queries,
        "pii_detected": pii if pii else None,
    }

    # 6. 자동 검색 (옵션)
    if auto_search and clause_hints and API_KEY:
        evidence: list[dict] = []
        for hint in clause_hints[:3]:  # 최대 3개 조항
            for q in hint["suggested_queries"][:2]:  # 조항당 최대 2개 검색
                api_res = _fetch("lawSearch.do", {"target": "law", "query": q, "display": 3})
                laws_found = []
                raw_laws = api_res.get("LawSearch", {}).get("law", [])
                if isinstance(raw_laws, dict):
                    raw_laws = [raw_laws]
                for lw in raw_laws[:3]:
                    laws_found.append({
                        "법령명": lw.get("법령명한글"),
                        "법령ID": lw.get("법령일련번호"),
                        "시행일자": lw.get("시행일자"),
                    })
                evidence.append({
                    "clause": hint["clause"],
                    "query": q,
                    "laws_found": laws_found,
                    "api_url": api_res.get("api_url", ""),
                })
        result["evidence_results"] = evidence
        result["has_legal_basis"] = any(e["laws_found"] for e in evidence)
    elif auto_search and not API_KEY:
        result["evidence_results"] = "LAW_API_KEY 미설정 — 자동 검색 건너뜀"
        result["has_legal_basis"] = False

    label = file_path or "(직접 입력)"
    _print_result("계약서 분석", label, result)


# ==============================================================================
# 통합 법률 QA (원본 MCP SmartSearchService에서 포팅)
# ==============================================================================

# 의도 분석용 키워드 매핑
_INTENT_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "law": [
        ("법", 1), ("법률", 2), ("시행령", 3), ("시행규칙", 3), ("법령", 2),
        ("조문", 3), ("제\\d+조", 3), ("조항", 2),
    ],
    "precedent": [
        ("판례", 5), ("판결", 4), ("대법원", 4), ("사건", 2), ("선고", 3),
        ("결정", 1), ("판시", 4), ("하급심", 3),
    ],
    "interpretation": [
        ("해석", 2), ("법령해석", 5), ("유권해석", 5), ("질의", 3),
        ("회신", 3), ("답변", 1),
    ],
    "administrative_appeal": [
        ("행정심판", 5), ("재결", 4), ("취소심판", 4), ("처분", 2),
        ("행정소송", 3),
    ],
    "constitutional": [
        ("헌법재판", 5), ("헌재", 5), ("위헌", 4), ("합헌", 4),
        ("헌법불합치", 5), ("헌법소원", 5),
    ],
}


def _analyze_intent(query: str) -> list[str]:
    """질문 의도 분석 — 점수 기반 상위 2개 타입 반환."""
    scores: dict[str, int] = {}
    for intent, keywords in _INTENT_KEYWORDS.items():
        score = 0
        for kw, weight in keywords:
            if kw.startswith("(") or "\\" in kw:
                # 정규식 패턴
                if re.search(kw, query):
                    score += weight
            elif kw in query:
                score += weight
        if score > 0:
            scores[intent] = score

    if not scores:
        # 기본 의도: 법령 + 판례
        return ["law", "precedent"]

    sorted_intents = sorted(scores, key=lambda k: scores[k], reverse=True)
    return sorted_intents[:2]  # 최대 2개


def _parse_time_condition(query: str) -> dict | None:
    """'최근 N년', '20XX년 이후' 등 자연어 시간 표현 파싱."""
    import datetime
    now = datetime.datetime.now()

    # 최근 N년
    m = re.search(r"최근\s*(\d+)\s*년", query)
    if m:
        years = int(m.group(1))
        return {"from_year": now.year - years, "to_year": now.year, "raw": m.group(0)}

    # YYYY년 이후
    m = re.search(r"(\d{4})\s*년\s*이후", query)
    if m:
        return {"from_year": int(m.group(1)), "to_year": now.year, "raw": m.group(0)}

    # YYYY년부터 YYYY년
    m = re.search(r"(\d{4})\s*년\s*부터\s*(\d{4})\s*년", query)
    if m:
        return {"from_year": int(m.group(1)), "to_year": int(m.group(2)), "raw": m.group(0)}

    return None


def _extract_law_name_from_query(query: str) -> str | None:
    """질문에서 법령명을 추출."""
    m = re.search(r"[「『\"]?([가-힣]{2,}(?:\s[가-힣]{2,6}){0,2}(?:법|령|규칙|조례))[」』\"]?", query)
    return m.group(1).strip() if m else None


def _extract_article_from_query(query: str) -> str | None:
    """질문에서 조문 번호를 추출."""
    m = re.search(r"제\s*(\d+(?:-\d+)?)\s*조", query)
    return m.group(1) if m else None


def _build_search_keyword(query: str) -> str:
    """질의에서 핵심 키워드를 추출하여 짧은 검색어 생성."""
    # 시간/조건 표현 제거
    cleaned = re.sub(r"최근\s*\d+\s*년", "", query)
    cleaned = re.sub(r"\d{4}\s*년\s*(이후|부터|까지)", "", cleaned)
    cleaned = re.sub(r"관련|관한|대한|에서|으로|판례|법령|해석|검색", "", cleaned)
    words = cleaned.split()
    # 가장 긴 단어 상위 3개 선택
    words = sorted([w for w in words if len(w) >= 2], key=len, reverse=True)[:3]
    return " ".join(words) if words else query[:20]


def smart_qa(query: str, max_results: int = 3) -> None:
    """통합 법률 QA — 의도 분석 + 다중 타입 자동 검색.

    사용자 질문을 분석하여 적절한 검색 타입(법령/판례/법령해석/행정심판/헌재 등)을
    자동 감지하고, 최대 2개 타입에 대해 병렬 검색을 수행합니다.

    Args:
        query: 법률 관련 질문 (자연어)
        max_results: 타입별 최대 검색 결과 수
    """
    if not API_KEY:
        _print_result("통합 QA", query, {
            "error": "LAW_API_KEY 미설정 — API 검색 불가",
            "has_legal_basis": False,
            "self_knowledge_blocked": True,
            "msg": "API 키를 설정한 후 다시 시도하세요.",
        })
        return

    # 1. 의도 분석
    intents = _analyze_intent(query)

    # 2. 시간 조건 파싱
    time_cond = _parse_time_condition(query)

    # 3. 파라미터 추출
    law_name = _extract_law_name_from_query(query)
    article = _extract_article_from_query(query)

    # 4. 검색 키워드 생성
    keyword = _build_search_keyword(query)

    # 5. 다중 타입 검색 실행
    target_map = {
        "law": ("law", "lawSearch.do"),
        "precedent": ("prec", "lawSearch.do"),
        "interpretation": ("expc", "lawSearch.do"),
        "administrative_appeal": ("decc", "lawSearch.do"),
        "constitutional": ("detc", "lawSearch.do"),
    }

    results: dict[str, Any] = {}
    sources_count: dict[str, int] = {}
    search_query = law_name if law_name else keyword  # 법령명 있으면 우선 사용

    for intent in intents:
        if intent not in target_map:
            continue
        api_target, endpoint = target_map[intent]
        res = _fetch(endpoint, {
            "target": api_target, "query": search_query,
            "display": max_results, "page": 1,
        })

        # 결과 파싱
        items = []
        if isinstance(res, dict):
            # 에러 확인
            if "error" in res:
                results[intent] = res
                sources_count[intent] = 0
                continue

            # 데이터 추출 (다양한 래퍼 구조 처리)
            for wrapper_key in ["LawSearch", "PrecSearch", "ExpcSearch", "DeccSearch", "DetcSearch"]:
                if wrapper_key in res:
                    inner = res[wrapper_key]
                    if isinstance(inner, dict):
                        # 결과 키 탐색
                        for data_key in ["law", "prec", "expc", "decc", "detc"]:
                            if data_key in inner:
                                items = inner[data_key]
                                if isinstance(items, dict):
                                    items = [items]
                                break
                    break

        if not isinstance(items, list):
            items = []

        results[intent] = {
            "items": items[:max_results],
            "count": len(items),
            "api_url": res.get("api_url", "") if isinstance(res, dict) else "",
        }
        sources_count[intent] = len(items)

    # 6. Fallback: 첫 번째 검색 실패 시 키워드 축약 재시도
    total = sum(sources_count.values())
    if total == 0 and search_query != keyword:
        # 법령명 대신 키워드로 재시도
        for intent in intents[:1]:  # 첫 번째 의도만 재시도
            if intent not in target_map:
                continue
            api_target, endpoint = target_map[intent]
            res = _fetch(endpoint, {
                "target": api_target, "query": keyword,
                "display": max_results, "page": 1,
            })
            if isinstance(res, dict):
                for wrapper_key in ["LawSearch", "PrecSearch", "ExpcSearch", "DeccSearch", "DetcSearch"]:
                    if wrapper_key in res:
                        inner = res[wrapper_key]
                        if isinstance(inner, dict):
                            for data_key in ["law", "prec", "expc", "decc", "detc"]:
                                if data_key in inner:
                                    items = inner[data_key]
                                    if isinstance(items, dict):
                                        items = [items]
                                    if items:
                                        results[intent] = {
                                            "items": items[:max_results],
                                            "count": len(items),
                                            "api_url": res.get("api_url", ""),
                                            "fallback": True,
                                        }
                                        sources_count[intent] = len(items)
                                        total = sum(sources_count.values())
                                    break
                        break

    # 7. 응답 구성
    has_legal_basis = total > 0

    # missing_reason 판단
    missing_reason = None
    if not has_legal_basis:
        has_api_error = any(
            isinstance(r, dict) and "error" in r
            for r in results.values()
        )
        missing_reason = "API_ERROR" if has_api_error else "NO_MATCH"

    response: dict[str, Any] = {
        "query": query,
        "detected_intents": intents,
        "search_keyword": search_query,
        "time_condition": time_cond,
        "extracted_params": {
            "law_name": law_name,
            "article": article,
        },
        "has_legal_basis": has_legal_basis,
        "sources_count": sources_count,
        "missing_reason": missing_reason,
        "results": results,
        "self_knowledge_blocked": not has_legal_basis,
        "response_policy": {
            "if_has_legal_basis_true": "API 결과 범위 내에서만 답변",
            "if_has_legal_basis_false": "결론 금지 — '근거를 찾지 못했습니다' + 재검색 제안만",
            "when_api_error": "API 장애 안내 + 재시도 가이드만",
            "absolute_prohibition": "API 결과 없이 자체 법률 지식으로 답변 생성 금지",
        },
    }

    _print_result("통합 QA", query, response)


def verify_config() -> None:
    """현재 설정된 API 키 확인 및 공인 IP 조회"""
    if API_KEY:
        masked_key = API_KEY[:4] + "*" * (len(API_KEY) - 8) + API_KEY[-4:] if len(API_KEY) > 8 else "***"
        status = f"설정됨 ({masked_key})"
    else:
        status = "미설정 (API 키가 없거나 인식되지 않음)"

    try:
        req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "LexGuard-Skill/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            public_ip = resp.read().decode("utf-8").strip()
    except Exception as e:
        public_ip = f"확인 실패 ({str(e)})"
        
    print(json.dumps({
        "API_KEY_STATUS": status,
        "CURRENT_PUBLIC_IP": public_ip,
        "GUIDE": "https://open.law.go.kr 접속 -> 마이페이지 -> API인증값변경에서 위 CURRENT_PUBLIC_IP를 등록해야 호출 가능합니다."
    }, ensure_ascii=False, indent=2))


# ==============================================================================
# 출력 및 CLI
# ==============================================================================

def _print_result(title: str, query: str, result: Any) -> None:
    print(json.dumps({"title": title, "query": query, "data": result}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LexGuard — 국가법령정보센터 Open API 호출 CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="실행할 명령어")

    # ── 공통 인자 헬퍼 ──
    def _add_search_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--query", required=True, help="검색어")
        sp.add_argument("--page", type=int, default=1, help="페이지 번호 (기본: 1)")

    # ── search 명령어들 ──
    for name, desc in [
        ("search_law", "법령 검색"),
        ("search_prec", "판례 검색"),
        ("search_interp", "법령해석 검색"),
        ("search_admrul", "행정규칙 검색"),
        ("search_ordin", "자치법규 검색"),
        ("search_detc", "헌재결정 검색"),
        ("search_decc", "행정심판 재결례 검색"),
    ]:
        sp = subparsers.add_parser(name, help=desc)
        _add_search_args(sp)

    # ── smart_qa ──
    sp = subparsers.add_parser("smart_qa", help="통합 법률 QA — 의도 분석 + 다중 타입 자동 검색")
    sp.add_argument("--query", required=True, help="법률 관련 질문 (자연어)")
    sp.add_argument("--max-results", type=int, default=3, help="타입별 최대 결과 수 (기본: 3)")

    # ── analyze_contract ──
    sp = subparsers.add_parser("analyze_contract",
        help="계약서/약관 분석 — 조항별 쟁점 탐지 + 법적 근거 힌트")
    sp.add_argument("--text", default="", help="분석할 계약서/약관 텍스트 (직접 입력)")
    sp.add_argument("--file", default="", help="텍스트 파일 경로 (.pdf/.txt/.md)")
    sp.add_argument("--auto-search", action="store_true",
        help="조항별 추천 검색어로 법령/판례 자동 검색")

    # ── search_special_appeal ──
    sp = subparsers.add_parser("search_special_appeal", help="특별행정심판 재결례 검색 (조세심판원 등)")
    sp.add_argument("--query", required=True, help="검색어")
    sp.add_argument("--tribunal", required=True,
                    choices=list(SPECIAL_APPEAL_TARGET_MAP.keys()),
                    help="심판원명")
    sp.add_argument("--page", type=int, default=1, help="페이지 번호")

    # ── get_special_appeal ──
    sp = subparsers.add_parser("get_special_appeal", help="특별행정심판 재결례 상세 조회")
    sp.add_argument("--appeal-id", required=True, help="재결례 일련번호")
    sp.add_argument("--tribunal", required=True,
                    choices=list(SPECIAL_APPEAL_TARGET_MAP.keys()),
                    help="심판원명")

    # ── search_form ──
    sp = subparsers.add_parser("search_form", help="정부 공식 서식 검색 (법령 별표·서식)")
    sp.add_argument("--query", required=True, help="검색어 (서식명 또는 법령명)")
    sp.add_argument(
        "--kind", type=int, default=2,
        choices=[1, 2, 3, 4, 5],
        help="서식 종류: 1=별표, 2=서식(기본), 3=별지, 4=별도, 5=부록",
    )
    sp.add_argument("--page", type=int, default=1, help="페이지 번호 (기본: 1)")

    # ── get_form ──
    sp = subparsers.add_parser("get_form", help="정부 공식 서식 상세 조회")
    sp.add_argument("--form-id", required=True, help="서식 일련번호")

    # ── get_history ──
    sp = subparsers.add_parser("get_history", help="법령 개정 이력 조회 (구법령 포함)")
    sp.add_argument("--law-id", required=True, help="법령 일련번호 (MST) — get_law/search_law 결과에서 복사")

    # ── get_related ──
    sp = subparsers.add_parser("get_related", help="법령 조문 내 참조 법령 체인 자동 추출")
    sp.add_argument("--law-id", required=True, help="법령 일련번호 (MST)")
    sp.add_argument("--article", default="", help="특정 조문 번호 (예: 163, 50-2). 생략 시 전체")

    # ── analyze_doc ──
    sp = subparsers.add_parser("analyze_doc",
        help="문서(PDF/TXT) 분석 — PII 감지 + 법령 참조 추출 + 관련 법령 조회")
    sp.add_argument("--file", required=True,
        help="분석할 파일 경로 (.pdf / .txt / .md 지원)")
    sp.add_argument("--mask-pii", action="store_true",
        help="주민번호·전화번호 등 PII를 분석 전에 마스킹 처리")
    sp.add_argument("--skip-search", action="store_true",
        help="법령 API 검색을 건너뜀 (PII 감지 + 참조 추출만 수행)")

    # ── download_form ──
    sp = subparsers.add_parser("download_form", help="정부 공식 서식 파일 직접 다운로드 (HWP/PDF)")
    sp.add_argument("--fl-seq", required=True,

                    help="파일 일련번호 — search_form 결과의 별표서식파일링크/별표서식PDF파일링크 URL에서 flSeq= 값")
    sp.add_argument("--out", required=True,
                    help="저장 경로 (예: ./영수증.pdf, ~/Desktop/서식.hwp)")
    sp.add_argument("--format", default="pdf", choices=["pdf", "hwp"],
                    help="파일 형식 힌트: pdf(기본) 또는 hwp")

    # ── get_law ──
    sp = subparsers.add_parser("get_law", help="법령 상세 조회")
    sp.add_argument("--law-id", required=True, help="법령 일련번호 (MST)")
    sp.add_argument("--article", default="", help="조문 번호 (예: 1, 10-2)")

    # ── get_prec ──
    sp = subparsers.add_parser("get_prec", help="판례 상세 조회")
    sp.add_argument("--prec-id", required=True, help="판례 일련번호")

    # ── get_interp ──
    sp = subparsers.add_parser("get_interp", help="법령해석 상세 조회")
    sp.add_argument("--interp-id", required=True, help="법령해석 일련번호")

    # ── get_detc ──
    sp = subparsers.add_parser("get_detc", help="헌재결정 상세 조회")
    sp.add_argument("--detc-id", required=True, help="헌재결정 일련번호")

    # ── get_admrul ──
    sp = subparsers.add_parser("get_admrul", help="행정규칙 상세 조회")
    sp.add_argument("--admrul-id", required=True, help="행정규칙 일련번호")

    # ── get_ordin ──
    sp = subparsers.add_parser("get_ordin", help="자치법규 상세 조회")
    sp.add_argument("--ordin-id", required=True, help="자치법규 일련번호")

    # ── get_decc ──
    sp = subparsers.add_parser("get_decc", help="행정심판 재결례 상세 조회")
    sp.add_argument("--decc-id", required=True, help="행정심판 재결례 일련번호")

    # ── search_committee ──
    sp = subparsers.add_parser("search_committee", help="위원회 결정문 검색 (11개 위원회)")
    sp.add_argument("--query", required=True, help="검색어")
    sp.add_argument("--committee", required=True,
                    choices=list(COMMITTEE_TARGET_MAP.keys()),
                    help="위원회명")
    sp.add_argument("--page", type=int, default=1, help="페이지 번호")

    # ── get_committee ──
    sp = subparsers.add_parser("get_committee", help="위원회 결정문 상세 조회")
    sp.add_argument("--committee-id", required=True, help="결정문 일련번호")
    sp.add_argument("--committee", required=True,
                    choices=list(COMMITTEE_TARGET_MAP.keys()),
                    help="위원회명")

    # ── verify_config ──
    subparsers.add_parser("verify_config", help="환경 설정 확인 (API 키 및 공인 IP 조회)")

    args = parser.parse_args()

    # ── 명령어 디스패치 ──
    dispatch = {
        "search_law": lambda: search_law(args.query, args.page),
        "search_prec": lambda: search_prec(args.query, args.page),
        "search_interp": lambda: search_interp(args.query, args.page),
        "search_admrul": lambda: search_admrul(args.query, args.page),
        "search_ordin": lambda: search_ordin(args.query, args.page),
        "search_detc": lambda: search_detc(args.query, args.page),
        "search_decc": lambda: search_decc(args.query, args.page),
        "search_form": lambda: search_form(args.query, args.kind, args.page),
        "search_committee": lambda: search_committee(args.query, args.committee, args.page),
        "search_special_appeal": lambda: search_special_appeal(args.query, args.tribunal, args.page),
        "smart_qa": lambda: smart_qa(args.query, args.max_results),
        "analyze_contract": lambda: analyze_contract(args.text, args.file, args.auto_search),
        "get_law": lambda: get_law(args.law_id, args.article),
        "get_prec": lambda: get_prec(args.prec_id),
        "get_interp": lambda: get_interp(args.interp_id),
        "get_detc": lambda: get_detc(args.detc_id),
        "get_admrul": lambda: get_admrul(args.admrul_id),
        "get_ordin": lambda: get_ordin(args.ordin_id),
        "get_decc": lambda: get_decc(args.decc_id),
        "get_committee": lambda: get_committee(args.committee_id, args.committee),
        "get_special_appeal": lambda: get_special_appeal(args.appeal_id, args.tribunal),
        "get_form":      lambda: get_form(args.form_id),
        "download_form": lambda: download_form(args.fl_seq, args.out, args.format),
        "get_history":   lambda: get_history(args.law_id),
        "get_related":   lambda: get_related(args.law_id, args.article),
        "analyze_doc":   lambda: analyze_doc(args.file, args.mask_pii, args.skip_search),
        "verify_config": verify_config,
    }
    dispatch[args.command]()


if __name__ == "__main__":
    main()
