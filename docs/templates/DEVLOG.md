# LexGuard Development Log

> **Purpose:** Records full context so other AI agents can install and deploy
> this skill in new environments without missing steps.
> Last updated: 2026-04-02

---

## 1. Project Overview

| Item | Details |
|---|---|
| Project Name | LexGuard — Korean Legal Information Retrieval Skill |
| Data Source | Korea National Law Information Center Open API (law.go.kr DRF) |
| Language | Python 3.10+ (stdlib-centric, minimal external dependencies) |
| Skill Format | Gemini/Claude compatible Skill folder structure |
| Invocation | CLI subprocess (`python3 lexguard_api.py <command> [args]`) |

## 2. Directory Structure

```
.agents/skills/lexguard/
├── SKILL.md                 # Skill usage guide (read by AI agents)
├── DEVLOG.md                # ← This file (development log)
├── scripts/
│   └── lexguard_api.py      # Core script (all commands included)
└── resources/
    └── domain_keywords.json  # Domain classification keywords (labor/real estate/criminal etc.)
```

## 3. Environment Setup Checklist

### 3-1. Required Environment Variable

```bash
# Key issued from Korea National Law Information Center (apply at https://open.law.go.kr)
export LAW_API_KEY=YOUR_ISSUED_KEY_HERE

# Verify
python3 lexguard_api.py verify_config
```

### 3-2. IP Registration (Required)

The Korea National Law Information Center API **only works from registered public IPs**.

```bash
# Check current PC's public IP
curl -s https://api.ipify.org

# Registration path
# https://open.law.go.kr → Login → My Page → API Authentication Value Change
# → Add the IP confirmed above
```

> **Note:** In cloud/CI environments, register the NAT gateway's public IP.

### 3-3. Dependency Installation

```bash
# [Required] Python 3.10+ (uses only built-in stdlib, no additional install needed)

# [Recommended] PDF text extraction — needed for analyze_doc command
pip install pdfplumber

# [Alternative] Can use poppler instead of pdfplumber
# Mac:
brew install poppler
# Ubuntu:
sudo apt install poppler-utils
```

### 3-4. Commands That Work Without API Key

These commands run without `LAW_API_KEY`:

| Command | Description |
|---|---|
| `verify_config` | Check settings + query public IP |
| `download_form` | Direct form file download (Referer header only) |
| `analyze_doc --skip-search` | PII detection + statute reference extraction (without API lookup) |

## 4. Full Command List

### 4-1. Basic Search/Lookup (API Key Required)

| Command | Purpose | Key Parameters |
|---|---|---|
| `search_law` | Statute list search | `--query`, `--page` |
| `get_law` | Statute article detail | `--law-id`, `--article` |
| `search_prec` | Precedent search | `--query`, `--page` |
| `get_prec` | Precedent detail | `--prec-id` |
| `search_interp` | Legal interpretation search | `--query` |
| `get_interp` | Legal interpretation detail | `--interp-id` |
| `search_admrul` | Administrative rules (directives/notices) search | `--query` |
| `search_ordin` | Local ordinances search | `--query` |
| `search_detc` | Constitutional Court decision search | `--query` |
| `get_detc` | Constitutional Court decision detail | `--detc-id` |
| `search_form` | Government official form search | `--query`, `--kind` |
| `get_form` | Form detail | `--form-id` |

### 4-2. Extended Features

| Command | Purpose | API Key | Key Parameters |
|---|---|---|---|
| `get_history` | Statute amendment history (including old versions) | Required | `--law-id` |
| `get_related` | Auto-extract referenced statute chain from articles | Required | `--law-id`, `--article` |
| `analyze_doc` | Document PII detection + statute references | Optional | `--file`, `--mask-pii`, `--skip-search` |
| `download_form` | Direct form file download | Not needed | `--fl-seq`, `--out`, `--format` |
| `verify_config` | Environment settings check | Not needed | (none) |

> ⚠️ `analyze_doc` supported formats: `.pdf`, `.txt`, `.md` (HWP: convert to PDF/TXT first)

## 5. API Endpoint Details

### 5-1. Base API (DRF)

```
Base URL: https://www.law.go.kr/DRF
Auth method: OC={API_KEY} parameter
Response format: JSON (some XML responses — auto-parsed)
```

| Endpoint | target | Purpose |
|---|---|---|
| `lawSearch.do` | `law` | Statute list search |
| `lawService.do` | `law` | Statute detail (MST=statute_ID) |
| `lawSearch.do` | `prec` | Precedent search |
| `lawService.do` | `prec` | Precedent detail (ID=precedent_ID) |
| `lawSearch.do` | `expc` | Legal interpretation search |
| `lawService.do` | `expc` | Legal interpretation detail |
| `lawSearch.do` | `admrul` | Administrative rules search |
| `lawSearch.do` | `ordin` | Local ordinances search |
| `lawSearch.do` | `detc` | Constitutional Court decision search |
| `lawService.do` | `detc` | Constitutional Court decision detail |
| `lawSearch.do` | `licbyl` | Form search (knd=2) |
| `lawService.do` | `licbyl` | Form detail |

### 5-2. Form File Download (Non-DRF)

```
URL: https://www.law.go.kr/flDownload.do?flSeq={file_serial_number}
Auth: Not required (only needs Referer: https://www.law.go.kr/ header)
Response: Binary file (HWP/PDF)
```

### 5-3. Precedent API Notes

The Public Data Portal's "Ministry of Government Legislation Precedent Full Text Lookup" links to
`https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=precInfoGuide`,
with the actual endpoint being the same:

```
https://www.law.go.kr/DRF/lawService.do?OC={key}&target=prec&ID={precedent_ID}&type=JSON
```

→ Already supported by existing `get_prec` command. No additional integration needed.

## 6. Personal Information Processing Principles (Required for Deployment)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Document originals processed only within local process.  │
│ 2. External API transmission: statute names/article numbers │
│    only (no document content sent)                          │
│ 3. --mask-pii option: masks resident numbers, phone numbers │
│    etc. before analysis                                     │
│ 4. Analysis results do not include actual PII values.       │
│ 5. PII detection patterns: resident registration number,    │
│    passport, driver's license, phone, email, bank account   │
└─────────────────────────────────────────────────────────────┘
```

## 7. External Package Reference

### korea-law-mcp (Reference only)

- **Purpose:** Wraps Korea National Law Information Center API as 87+ MCP tools
- **GitHub:** https://github.com/chrisryugj/korean-law-mcp
- **Status:** Not adopted since LexGuard uses its own Python wrapper
- **Note:** Can be used instead of LexGuard in MCP-based environments

## 8. Development History (Reverse Chronological)

### v2.1 — 2026-04-02
- ❌ HWP kordoc support attempted then rolled back (removed due to Markdown table structure limitations)

### v2.0 — 2026-04-02
- ✅ `get_history`: Statute amendment history lookup (including old versions)
- ✅ `get_related`: Auto-extract referenced statute chain from articles
- ✅ `analyze_doc`: Document PII detection + statute reference extraction + related statute lookup
- ✅ PII detection/masking utilities (`_detect_pii`, `_mask_pii`)
- ✅ Statute reference extraction (`_extract_law_refs`) — with particle filtering
- ✅ PDF text extraction (`pdfplumber` primary, `poppler` fallback)
- ✅ Added `analyze_doc` to `_NO_KEY_COMMANDS` (partial exec without API key)

### v1.1 — 2026-04-02
- ✅ `search_form` / `get_form`: Government official form search
- ✅ `download_form`: Direct form file download (Referer header bypass)
- ✅ flSeq-based download + Content-Type based auto extension detection
- ✅ HTML error page detection logic

### v1.0 — 2026-04-01
- ✅ Initial implementation: statute/precedent/interpretation/admin rules/ordinances/constitutional decisions search & detail
- ✅ Claude Skill folder structure (SKILL.md + scripts/ + resources/)
- ✅ XML/JSON auto-parsing (mixed content, attribute preservation)
- ✅ Article number conversion (`_format_jo`) — "10-2" → "001002"
- ✅ `verify_config`: API key check + public IP query

## 9. New Environment Installation Quickstart

```bash
# 1. Copy skill folder
cp -r .agents/skills/lexguard /target/project/.agents/skills/

# 2. Set environment variable
export LAW_API_KEY=YOUR_ISSUED_KEY

# 3. Verify public IP registration
python3 .agents/skills/lexguard/scripts/lexguard_api.py verify_config

# 4. [Recommended] Install PDF extraction dependency
pip install pdfplumber

# 5. Test — statute search
LAW_API_KEY=key python3 .agents/skills/lexguard/scripts/lexguard_api.py \
    search_law --query "Labor Standards Act"

# 6. Test — document analysis (without API key)
python3 .agents/skills/lexguard/scripts/lexguard_api.py \
    analyze_doc --file "test.pdf" --skip-search
```

## 10. Known Limitations & Future Tasks

| Category | Details | Status |
|---|---|---|
| IP Registration | Dynamic IP issues in cloud environments | Unresolved — VPN/static IP needed |
| API Rate Limit | May be blocked on excessive calls to KLIS | `get_related` limited to max 8 calls |
| HWP Parsing | Markdown tables don't support merged cells — HWP structure loss | Excluded (use PDF conversion) |
| PII Detection | Pattern-based, may miss modified formats | Room for improvement |
| flSeq Changes | Form download links break on statute amendments | Recommend `search_form` for latest |
| OCR | Cannot extract text from image-based PDFs | Future consideration |
