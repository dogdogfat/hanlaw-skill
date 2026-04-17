---
name: hanlaw-skill
description: "한국 법령·판례·법령해석 조회 Skill (Windows 버전). Use when the user asks about Korean law, court precedents, or legal interpretations, or requests contract/terms analysis. Calls the Korea National Law Information Center Open API."
---

# hanlaw-skill — 한국 법률 정보 조회 Skill (Windows)

> Helps find threads of legal information.
> Does NOT replace legal counsel. Provides information based on official statute/precedent data.

## Overview

This skill uses the Korea National Law Information Center (law.go.kr) Open API to provide:
1. **Statute Search** — Search statute lists and view article details
2. **Precedent Search** — Search Supreme/lower court precedents and details
3. **Legal Interpretation** — Search and view legal interpretation cases
4. **Administrative Rules** — Search directives/notices/guidelines and details
5. **Local Ordinances** — Search municipal ordinances/rules and details
6. **Constitutional Court Decisions** — Search and view decisions
7. **Administrative Appeals** — Search and view appeal rulings
8. **Committee Decisions** — Search decisions from 11 committees (Labor Relations, Human Rights, etc.)
9. **Special Administrative Appeals** — Search rulings from Tax Tribunal, Maritime Safety Tribunal, etc.
10. **Integrated Legal QA** — Auto-analyze query intent + multi-type simultaneous search
11. **Contract/Terms Analysis** — Infer document type + detect per-clause issues + legal basis hints
12. **Government Official Forms** — Search and download statutory appendix forms (applications, contracts, etc.)

##  Response Policy (Absolute Compliance — Block AI Self-Knowledge)

> **This section contains the highest-priority rules that any AI using this skill MUST follow.**

### Principle: No Legal Answers Without API Results

| Condition | AI Behavior |
|---|---|
| `has_legal_basis: true` | Answer only within API result scope. Do NOT cite articles/precedents absent from results. |
| `has_legal_basis: false` + `missing_reason: NO_MATCH` | Return "Could not find relevant legal basis" + suggest re-search only. **No conclusions.** |
| `has_legal_basis: false` + `missing_reason: API_ERROR` | Return "API connection issue" + retry guidance only. |
| `self_knowledge_blocked: true` | **Absolutely NO answers generated from AI's own legal knowledge.** |

### Absolutely Prohibited Actions

1. **Generating legal answers without calling the API** — Always call API first
2. **Substituting with self-knowledge on API failure** — Return only "Unable to retrieve information"
3. **Citing precedents/articles not in API results** — Prevent hallucination
4. **Definitive legal conclusions** — Do not use definitive expressions like "it is", "you must"

### AI Response Format — MANDATORY (No exceptions)

> ⚠️ **This is not a suggestion. This is a strict rule. You MUST use the exact template below.**
> - Section order, header names, and output language (**Korean**) cannot be changed or omitted.
> - Do NOT add preambles, summaries, titles, or any text outside the template.
> - All text from API results (조문내용, 판시사항, 판결요지, 질의요지, 회답, 재결요지, 주문) MUST be quoted verbatim — do not paraphrase or summarize.

**Output language: Korean at all times. No exceptions.**

#### Data type → Section mapping

| API result type | Field to quote verbatim | Goes into section |
|---|---|---|
| `get_law` (법령 조문) | `조문내용` | **법령 인용** block |
| `get_prec` (판례) | `판시사항`, `판결요지` | **판례** section |
| `get_interp` (법령해석례) | `질의요지`, `회답` | **사례** section |
| `get_decc` (행정심판 재결례) | `재결요지` | **사례** section |
| `get_detc` (헌재결정) | `주문`, `이유` | **판례** section |
| `search_committee` / `get_committee` (위원회 결정) | 결정 요지 | **사례** section |

#### Output template

Render exactly as shown. Fill `(내용작성)` placeholders. Omit entire sections marked "← 없으면 생략".

---

```
> 대한민국 법령·공개 판례 기준 일반 정보입니다. 개별 사건의 법률자문이 아닙니다.

**핵심 답변**
(내용작성 — 관련 법령·판례 검색 결과 요약. 1~2문장. 확정 표현 금지.)

**[법령명 제N조]**
> (내용작성 — get_law로 조회한 조문내용 원문 그대로. 요약 금지.)

**해석**
(내용작성 — 위 조문이 이 사안에 어떻게 적용되는지.)

↑ 관련 조문 수만큼 [법령명 제N조] + 해석 블록 반복

**사례** ← 법령해석례·행정심판·위원회 결정 결과가 없으면 섹션 전체 생략
> (내용작성 — get_interp의 질의요지+회답, 또는 get_decc의 재결요지, 또는 위원회 결정 요지 원문.)

(내용작성 — 위 사례가 이 사안에 갖는 의미.)

**판례** ← 판례·헌재결정 결과가 없으면 섹션 전체 생략
> (내용작성 — get_prec의 판시사항·판결요지, 또는 get_detc의 주문·이유 원문.)

(내용작성 — 위 판례가 이 사안에 갖는 의미.)

**주의사항**
위 내용은 국가법령정보센터 Open API로 검색한 공개 법령·판례 정보이며, 개별 사건에 대한 법률자문이 아닙니다.
소멸시효·형사고소·해고·부동산·가족법 관련 사안은 실제 자료를 가지고 변호사 상담을 권장합니다.
API 결과에서 확인되지 않은 내용은 이 답변에 포함되어 있지 않습니다.

**판례 검색 결과** ← search_prec 또는 smart_qa의 results.precedent.count == 0 이면 섹션 전체 생략
검색어 "[내용작성]" — 결과 없음 / N건 검색됨 (해당하는 것으로 작성)

**출처**
- [법령명 제N조](https://www.law.go.kr/법령/[법령명]) — API 결과의 `법령명한글` 값으로 URL 생성
- [사건번호](https://www.law.go.kr/판례/[사건번호]) — API 결과의 `사건번호` 값으로 URL 생성. 판례가 없으면 생략.
- [해석번호](https://www.law.go.kr/법령해석례/[해석번호]) — API 결과의 해석번호 값으로 URL 생성. 해석례가 없으면 생략.
- (그 외 재결번호, 결정번호 등 API 결과에 있는 식별자만 나열. URL 구성 불가 시 번호만 표기.)
```

---

**Strictly prohibited:**
- Any text before the disclaimer line (`> 대한민국 법령·공개 판례 기준...`)
- Paraphrasing API result text — always quote the exact field value verbatim
- Citing laws, cases, or rulings not present in API results
- Definitive conclusions ("~입니다", "~해야 합니다", "위법입니다")
- Fact-application + conclusion + action instruction combined — e.g.:
  - "당신 사건에서는 해고가 무효입니다"
  - "이 고소장 그대로 제출해도 됩니다"
  - "이건 사기죄 성립합니다"
  - "상대방에게 이렇게 보내면 법적으로 유리합니다"
- Adding sections not in the template
- Titles like "법률 상담 결과", "검토 결과", "분석 결과", "맞춤 법률상담", "소송 전략"
- Excessive emoji
- Any output in English
- Exposing `api_url` values (contains API key — internal only)

#### Precedent search existence check

Before writing the **판례** and **판례 검색 결과** sections, explicitly verify:
- For `smart_qa`: check `results.precedent.count > 0`
- For `search_prec`: check that the result list is non-empty

If count == 0 or the list is empty, omit both sections entirely. Do NOT write "판례 없음" or any placeholder — just skip the section.

## Prerequisites

>  The Korea National Law Information Center Open API only works when the **calling PC's public IP is registered**.
> 1. Log in at https://open.law.go.kr
> 2. Go to [My Page] → [API Authentication Value Change] and add your current PC's public IP
> 3. Check public IP (PowerShell):
>    ```powershell
>    (Invoke-WebRequest -Uri https://api.ipify.org).Content
>    ```

### API Key Setup

The web builder (https://dogdogfat.github.io/hanlaw-skill/) injects your issued key into `scripts/lexguard_api.py` automatically.
For manual installation, either edit `_BUILTIN_API_KEY` in that file or set the `LAW_API_KEY` environment variable:

```powershell
$env:LAW_API_KEY = "YOUR_ISSUED_KEY_HERE"
```

Or set persistently via System Environment Variables:

```powershell
[System.Environment]::SetEnvironmentVariable("LAW_API_KEY", "YOUR_ISSUED_KEY_HERE", "User")
```

## Execution Policy

>  **Important: Do NOT call the API just by reading this skill.**
> - Call the API **only when the user explicitly asks a legal question**.
> - The code blocks below are **reference examples**, not commands to execute upon reading.
> - After reading the skill, wait for the user's question.

## Usage

When a legal question is received, follow the workflow below.

>  **Top Priority Step**: ALWAYS run Step 0 to load the API key **before** calling any API.
> Skipping Step 0 will cause API calls to fail. **Never skip it.**

### Step 0: API Key Verification ( Required — Must verify before all API calls)

>  **The script auto-loads the .env file.** If the API key exists in the skill root's `.env` file, it's auto-recognized.
> Only use the method below if the `.env` file is missing or the key is absent.

**API key location:** Write in `%SKILL_DIR%\.env` file in the following format:

```
LAW_API_KEY=YOUR_ISSUED_KEY
```

**Verify (optional):**

```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" verify_config
```

### Step 1: Analyze Question and Classify Domain

Analyze the user's question and classify into one of these domains:
- **Labor/Employment** — Employment contracts, dismissal, wages, Labor Standards Act
- **Real Estate/Lease** — Lease, jeonse, sales, registration
- **Personal Information** — Personal Information Protection Act, IT Network Act
- **Consumer** — Consumer protection, e-commerce, refunds
- **Tax** — Income tax, VAT, inheritance tax
- **Finance** — Banking, insurance, securities, loans
- **Criminal** — Criminal law, criminal procedure, crimes
- **Civil** — Civil law, damages, contracts
- **Family** — Marriage, divorce, inheritance, parental rights
- **Administrative** — Administrative law, permits, administrative litigation

Domain keyword reference: `resources\domain_keywords.json`

### Step 2: Perform Appropriate Search

> Always run scripts relative to `%SKILL_DIR%\scripts\` path.

>  **Below is a command reference. Execute ONLY the command matching the user's question.**
> **NEVER execute all commands sequentially.**

#### 2-0. Integrated Legal QA (Recommended — Auto-analyzes query intent)

For complex legal questions, use `smart_qa` first. Auto-analyzes intent (statute/precedent/interpretation) and searches up to 2 types simultaneously.

```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" smart_qa --query "freelancer worker status criteria" --max-results 3
```

**Response field descriptions:**
- `detected_intents`: Auto-detected search intents (e.g., ["precedent", "law"])
- `has_legal_basis`: Whether legal basis was found via API
- `self_knowledge_blocked`: If true, AI self-knowledge answers are blocked
- `response_policy`: Response rules the AI must follow

>  When `has_legal_basis: false` and `self_knowledge_blocked: true`, **AI must NOT answer using its own legal knowledge.** Return only "Could not find basis" + re-search suggestions.

#### 2-1. Statute Search (Find acts/enforcement decrees/rules)

```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" search_law --query "search_term" --page 1
```

Statute detail (view article content by statute ID):
```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" get_law --law-id "statuteMST" --article "article_number"
```

#### 2-2. Precedent Search

```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" search_prec --query "search_term" --page 1
```

Precedent detail:
```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" get_prec --prec-id "precedent_serial"
```

#### 2-3. Legal Interpretation Search

```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" search_interp --query "search_term" --page 1
```

Interpretation detail:
```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" get_interp --interp-id "interpretation_ID"
```

#### 2-4. Administrative Rules Search (Directives/notices/guidelines)

```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" search_admrul --query "search_term" --page 1
```

Administrative rule detail:
```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" get_admrul --admrul-id "admin_rule_ID"
```

#### 2-5. Local Ordinance Search (Ordinances/rules)

```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" search_ordin --query "search_term" --page 1
```

Ordinance detail:
```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" get_ordin --ordin-id "ordinance_ID"
```

#### 2-6. Constitutional Court Decision Search

```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" search_detc --query "search_term" --page 1
```

Decision detail:
```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" get_detc --detc-id "decision_ID"
```

#### 2-7. Administrative Appeal Ruling Search

```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" search_decc --query "search_term" --page 1
```

Appeal ruling detail:
```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" get_decc --decc-id "ruling_ID"
```

#### 2-8. Committee Decision Search

Search and view decisions from 11 committees. Specify with `--committee`.

```cmd
:: Labor Relations Commission unfair dismissal decision search
python "%SKILL_DIR%\scripts\lexguard_api.py" search_committee --query "unfair_dismissal" --committee "노동위원회"

:: Decision detail
python "%SKILL_DIR%\scripts\lexguard_api.py" get_committee --committee-id "decision_ID" --committee "노동위원회"
```

**Supported committees:**
| Committee Name (Korean) | API target |
|---|---|
| 노동위원회 | nlrc |
| 국가인권위원회 | nhrck |
| 국민권익위원회 | acr |
| 공정거래위원회(금융위원회) | fsc |
| 개인정보보호위원회 | ppc |
| 고용보험심사위원회 | eiac |
| 방송미디어통신위원회 | kcc |
| 산업재해보상보험재심사위원회 | iaciac |
| 중앙토지수용위원회 | oclt |
| 중앙환경분쟁조정위원회 | ecc |
| 증권선물위원회 | sfc |

#### 2-9. Special Administrative Appeal Ruling Search

Search rulings from Tax Tribunal, Maritime Safety Tribunal, Anti-Corruption & Civil Rights Commission, Appeals Commission, etc.

```cmd
:: Tax Tribunal taxation ruling search
python "%SKILL_DIR%\scripts\lexguard_api.py" search_special_appeal --query "taxation_disposition" --tribunal "조세심판원"

:: Detail
python "%SKILL_DIR%\scripts\lexguard_api.py" get_special_appeal --appeal-id "ruling_ID" --tribunal "조세심판원"
```

**Supported tribunals:**
| Tribunal Name (Korean) | API target |
|---|---|
| 조세심판원 | ttSpecialDecc |
| 해양안전심판원 | kmstSpecialDecc |
| 국민권익위원회 | acrSpecialDecc |
| 소청심사위원회 | adapSpecialDecc |

#### 2-10. Government Official Form Search (Statutory appendix forms)

```cmd
:: Search by form name (kind default: 2=forms)
python "%SKILL_DIR%\scripts\lexguard_api.py" search_form --query "search_term" --kind 2
```

**kind parameter:**
| Value | Type |
|---|---|
| 1 | Appendix Table |
| 2 | **Form** (default — applications, contracts, etc.) |
| 3 | Separate Sheet |
| 4 | Separate |
| 5 | Supplement |

#### 2-11. Direct Form File Download

> From `search_form` results, copy the number after `flSeq=` from the form file link URL.

```cmd
:: PDF download (No API key required — direct law.go.kr download)
python "%SKILL_DIR%\scripts\lexguard_api.py" download_form --fl-seq "162953437" --out ".\form_name.pdf"

:: HWP download
python "%SKILL_DIR%\scripts\lexguard_api.py" download_form --fl-seq "162953435" --format hwp --out ".\form_name.hwp"
```

>  `download_form` runs without `LAW_API_KEY`.

#### 2-12. Statute Amendment History

```cmd
python "%SKILL_DIR%\scripts\lexguard_api.py" get_history --law-id "281875"
```

#### 2-13. Related Statute Chain Extraction

```cmd
:: Specific article only
python "%SKILL_DIR%\scripts\lexguard_api.py" get_related --law-id "281875" --article "163"

:: Entire statute (response may be large)
python "%SKILL_DIR%\scripts\lexguard_api.py" get_related --law-id "281875"
```

#### 2-14. Document Analysis (PII Detection + Statute Reference Extraction)

Detect personal information in PDF/TXT/MD documents and extract statute references.

```cmd
:: Basic analysis (API key required — includes statute lookup)
python "%SKILL_DIR%\scripts\lexguard_api.py" analyze_doc --file "contract.pdf"

:: With PII masking
python "%SKILL_DIR%\scripts\lexguard_api.py" analyze_doc --file "contract.pdf" --mask-pii
```

**PII detection targets:** Resident registration number, passport number, driver's license number, phone number, email, bank account number

### Step 3: Organize Results and Respond

When providing search results to users, follow these formats:

#### Statute Search Result Format
```
 **Statute Search Results: "search_term"**

1. **Statute Name** (Type: Act/Enforcement Decree/Enforcement Rule)
   - Effective date: YYYY-MM-DD
   - Statute ID: XXXXX
   - [View on KLIS](https://www.law.go.kr/법령/statute_name)
```

#### Precedent Search Result Format
```
 **Precedent Search Results: "search_term"**

1. **Case Name** (Case Number)
   - Judgment date: YYYY-MM-DD
   - Court: Supreme Court/High Court etc.
   - Judgment type: Judgment/Decision/Order
   - **Holding**: ...
   - **Summary**: ...
```

#### Contract Analysis Result Format
```
 **Contract Analysis Results**

 **Risk Clauses (Total: N)**

1. **[Clause No.] Clause content summary**
   -  Risk level: High/Medium/Low
   -  Related statute: Statute Name Art. X
   -  Recommendation: ...
```

### Step 4: Contract/Terms Analysis (Document Analysis Mode)

When user provides contract or terms text, use the `analyze_contract` command.

```cmd
:: Direct text input
python "%SKILL_DIR%\scripts\lexguard_api.py" analyze_contract --text "Article 1: Party A entrusts work to Party B. Article 2: Contract period is 1 year..."

:: Read from file
python "%SKILL_DIR%\scripts\lexguard_api.py" analyze_contract --file "contract.txt"

:: With auto statute search (API key required)
python "%SKILL_DIR%\scripts\lexguard_api.py" analyze_contract --file "contract.txt" --auto-search
```

**Analysis process:**

1. **Auto document type inference**: Keyword signal based
   - `labor`: Party A (갑), Party B (을), service, freelancer, outsourcing, instruction, commute, wage, etc.
   - `lease`: Lessor (임대인), Lessee (임차인), deposit, jeonse, monthly rent, etc.
   - `terms`: Member, terms of service, service, withdrawal, refund, etc.

2. **Per-clause issue detection**: Extract `Article N` patterns and match keywords
   - Immediate termination, deposit return delay, unilateral standards, unfavorable renewal
   - No refund, indemnity, unilateral terms change, unfavorable jurisdiction, penalties, non-compete

3. **Basis lookup hints**: Auto-generate recommended search terms per document type and issue

4. **Auto statute search** (`--auto-search`): Call statute API with recommended search terms

**Key checkpoints by contract type:**

**Employment Contract Checklist:**
- Labor Standards Act Art. 2 (Worker definition) — Disguised subcontracting/freelancer issues
- Labor Standards Act Art. 17 (Working conditions disclosure) — Required items missing
- Labor Standards Act Art. 23 (Dismissal restrictions) — Unfair dismissal clauses
- Labor Standards Act Art. 36 (Settlement of claims) — Severance pay
- Labor Standards Act Art. 43 (Wage payment) — Wage arrears potential
- Labor Standards Act Art. 50 (Working hours) — Overtime issues

**Lease Contract Checklist:**
- Housing Lease Protection Act Art. 3 (Right of defense) — Move-in registration/fixed date
- Housing Lease Protection Act Art. 4 (Lease period) — Minimum 2-year guarantee
- Housing Lease Protection Act Art. 6-3 (Deposit increase cap) — 5% limit
- Housing Lease Protection Act Art. 8 (Deposit priority repayment) — Small deposits

**Terms of Service Checklist:**
- Regulation of Standardized Contracts Act Art. 6 (General principle) — Unfair terms void
- Regulation of Standardized Contracts Act Art. 7 (Prohibition of indemnity clauses) — Excessive indemnity
- Regulation of Standardized Contracts Act Art. 9 (Contract termination) — Unilateral termination
- E-Commerce Act Art. 17 (Withdrawal) — Refund policy

## Personal Information Processing Principles

>  Must comply when deploying

1. **Document originals processed locally only** — Not transmitted to external servers.
2. **API transmission scope** — Statute names, article numbers, search keywords only (no document content or personal info)
3. **PII detection** — Pattern-based detection of resident registration numbers, phone numbers, emails, account numbers, etc.
4. **`--mask-pii` option** — Replaces PII with `[resident_registration_number]` tokens before analysis.
5. **No actual PII in results** — Returns only detection counts, not actual values.

## Verification Principles (Double Verification Support)

>  Designed so users can directly verify the accuracy of AI-generated legal answers.

1. **API URL provided**: All API results include an `api_url` field. Users can open this URL in a browser to verify source data.
2. **Source citation required**: When citing precedents, always specify `case number` (e.g., 2023Da12345); for legal interpretations, specify the `interpretation number`.
3. **Hallucination prevention**: AI answers must be written only within the scope of actual data returned by the API. Do not cite precedents or statutes not in API results.
4. **Built-in retry**: Auto-retries up to 2 times on network errors (Exponential Backoff). Reduced need to ask users to retry.
5. **Cross-check recommended**: For important legal judgments, perform both statute search + precedent search for cross-verification.

## Important Notices

>  This skill does NOT replace legal counsel.
> The information provided is reference information based on publicly available data from the Korea National Law Information Center.
> For specific legal judgments, please consult a licensed attorney.

## API Information

- **Data source**: Korea National Law Information Center (law.go.kr) Open API
- **API key**: Read from `LAW_API_KEY` environment variable. Some features work without it.
- **API docs**: https://open.law.go.kr/LSO/openApi/guideList.do
- **IP registration required**: https://open.law.go.kr → My Page → API Authentication Value Change

## External Dependencies

| Tool | Purpose | Required | Install |
|---|---|---|---|
| Python 3.10+ | Script execution | **Required** | [python.org](https://python.org) or `winget install Python` |
| `pdfplumber` | PDF text extraction | Recommended | `pip install pdfplumber` |
| `poppler` | PDF fallback extraction | Alternative | `choco install poppler` |

## File Locations

- Script: `%SKILL_DIR%\scripts\lexguard_api.py`
- Domain keywords: `resources\domain_keywords.json`
- Development log: `%SKILL_DIR%\DEVLOG.md`
