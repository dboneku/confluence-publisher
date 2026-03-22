---
name: confluence-publisher
description: This skill should be used when the user asks to "publish to Confluence", "upload a document to Confluence", "publish a folder to Confluence", "set up Confluence credentials", "list Confluence spaces", "select a space", "show the page tree", "navigate to a folder", "find a Confluence page", "audit Confluence pages", "check Confluence compliance", "remediate Confluence pages", "fix missing sections in Confluence", "set a regulation", "ISO 27001", "regulatory framework", or mentions publishing, auditing, remediating, or navigating documents in a Confluence wiki. Handles credential validation, space discovery, space/folder navigation (selectspace, cd), page tree visualization, regulation context (ISO 27001 document catalog, title doc-ID injection), upload planning, collision detection, publishing, compliance auditing, and ADF remediation via the Confluence Cloud REST API.
---

# Confluence Publisher Skill

Publish converted documents to Confluence Cloud using the REST API. Always pairs with the `doc-converter` skill for document ingestion and formatting.

---

## Step 0 — Check for doc-lint and doc-converter

**doc-lint (automatic):** `publish.py` automatically searches the Claude plugin cache for a `doc-lint` installation at runtime. No action needed — it will print one of:
- `[doc-lint] Found — using enhanced cleanup rules` → doc-lint's `fix.py` runs on every `.docx` before conversion, applying its full rule set (font normalization, list normalization, style misuse, etc.)
- `[doc-lint] Not found — using built-in cleanup rules` → the built-in cleanup logic inside `docx_to_adf()` handles conversion instead

To get enhanced rules, the user can install doc-lint alongside this plugin:

```
claude plugin install https://github.com/dboneku/doc-lint
```

**doc-converter skill (this session):** Check whether the `doc-converter` skill is available in this session.

- If available: use it for structural analysis and ADF conversion guidance (Steps 2–6).
- If not available: ask the user —

  ```
  The doc-converter skill isn't loaded. It handles formatting analysis and ADF conversion.
  Install it? (Recommended — it's included in this plugin)
  Or continue without it? (Built-in rules only)
  ```
  If user declines: proceed with built-in rules, no analysis step.

---

## Step 1 — Check Regulation Context

Before doing anything else, check `.confluence-config.json` in the working directory:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --list-regulation-docs iso27001
```

If a `regulation` key is present, load that regulation's document catalog into session memory as `REGULATION_DOCS`.

If no regulation is set, ask the user once:

```
Are you working under a specific regulatory framework? (e.g. ISO 27001)
  1. ISO 27001  2. None / skip
```
If they choose a regulation, run `/confluence-publisher:setregulation iso27001` to save it.

**Title naming convention (applies to all publishes, regulation or not):**

```
[DOC_TYPE]-[DOC_NUMBER]-[ISO_BRACKET]-[ORG_CODE]-[Document Name]
```

- **DOC_TYPE**: `POL`, `PRO`, `FRM`, `REC`, `GEN`
- **DOC_NUMBER**: 4-digit zero-padded number assigned per document (e.g. `1002`, `0007`)
- **ISO_BRACKET**: optional — regulation bracket if applicable (e.g. `[01-ISMS]`) — omit entirely if not used
- **ORG_CODE**: the organization/space code used in titles — provided by the user, not necessarily the Confluence space key
- **Document Name**: Title-cased, spaces preserved — never underscores

**DOC_TYPE classification:**
| Code | Use for |
|---|---|
| `POL` | Policies |
| `PRO` | Processes and procedures |
| `FRM` | Templates and forms |
| `REC` | Records — filled-out instances of forms/templates |
| `GEN` | Guides, how-tos, reference pages, overviews |

Examples (illustrative — substitute your own org code and numbers):
- `POL-1002-[01-ISMS]-ABC-Scope of the ISMS`
- `PRO-1068-ABC-Vulnerability Management Procedure`
- `FRM-0007-ABC-Production Push Checklist`
- `REC-2036-ABC-Access Review Record 2025-11-19`
- `GEN-2037-ABC-Engineering Development Guide`

**Doc number assignment:** Do not use any local spreadsheet or tracker file. Query the target space live to find the highest existing 4-digit number across all page titles and assign next available.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --next-doc-id {SPACE_KEY}
```

**When a regulation is active during publishing:**
- The first heading in the document body is stripped if it closely matches the page title (≥ 0.5 similarity), since Confluence shows the title separately in the page header

---

## Step 2 — Validate Credentials

Load credentials from `.env` in the working directory:

```
ATLASSIAN_URL=https://your-org.atlassian.net
ATLASSIAN_EMAIL=you@example.com
ATLASSIAN_API_TOKEN=your-token
```

If any key is missing, stop and tell the user exactly which ones are missing. Direct them to run `/confluence-publisher:setup` or visit https://id.atlassian.com/manage-profile/security/api-tokens.

Test credentials with a quick spaces API call before proceeding.

---

## Step 3 — Discover Spaces and Build Full Tree (SESSION_TREE)

On first use in a session, fetch all spaces and their complete page/folder hierarchy using the CLI (never call the Confluence API directly):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --list-spaces
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --tree {SPACE_KEY}
```

Cache as `SESSION_SPACES` and `SESSION_TREE`. Do not re-fetch during the session.

---

## Step 4 — Select Target Space and Parent

Ask the user to select a space (or confirm if already specified). Then ask where in the space to publish:

- Space root
- Under a named parent page or folder

Resolve parent using `SESSION_TREE` first (no API call needed). If not found in tree, re-run `--tree` to refresh. If still not found: report and ask user to confirm exact title.

**Important:** Confluence folders are type `folder` and only discoverable via CQL — never via the v2 pages API.

---

## Step 5 — Build Upload Plan

Before touching Confluence, always print the full plan:

```
Upload plan:
┌─────────────────────────────────────────────┬──────────────────┬───────┬──────────────┬──────────┐
│ File                                        │ Title            │ Space │ Parent       │ Template │
├─────────────────────────────────────────────┼──────────────────┼───────┼──────────────┼──────────┤
│ 1090-OHH-POL-Applicant Screening Policy.docx│ 1090-OHH-POL-... │ OHH   │ Hiring       │ Policy   │
└─────────────────────────────────────────────┴──────────────────┴───────┴──────────────┴──────────┘

Compliance warnings:
  ⚠ 1090-OHH-POL-Applicant Screening Policy.docx: missing required sections — Compliance, Revision History

Collision handling: [ ] Overwrite  [ ] Skip  [ ] Ask per file
```

Wait for explicit confirmation ("yes", "go", "confirm") or a documented command-level `--go` shortcut before proceeding. Compliance warnings are informational — they do not block publishing, but should be reviewed.

---

## Step 6 — Collision Detection

Before creating each page:
```python
GET /wiki/rest/api/content/search?cql=space="{key}" AND title="{title}"&limit=1
```

If collision found and no `--go` flag:
```
COLLISION: "Title" already exists under "Parent"
  1. Overwrite (version bump)
  2. Skip
  3. Cancel all
Apply to all remaining? [y/n]
```

If `--go` is supported by the calling command: default to overwrite silently.

---

## Step 7 — Publish

**No numbered headings:** Never prefix section headings with numbers in published ADF (e.g. use `"Purpose"` not `"1. Purpose"`). Confluence renders numbered headings as duplicate numbering artifacts. Strip any numeric prefixes from headings found in source documents before building ADF.

Create page:
```python
POST /wiki/api/v2/pages
{ spaceId, status: "current", title, parentId, body: { representation: "atlas_doc_format", value: json.dumps(adf) } }
```

Update (overwrite):
```python
GET /wiki/api/v2/pages/{id}          # get current version number
PUT /wiki/api/v2/pages/{id}
{ id, status, title, version: { number: current+1 }, body: ... }
```

Always `json.dumps()` the ADF dict — the `value` field must be a JSON string.

---

## Step 8 — Report Results

Single file:
```
Published: "Title"
  URL: https://org.atlassian.net/wiki/spaces/OHH/pages/12345/Title
  Space: OHH | Parent: Hiring | Nodes: 36
```

Bulk:
```
Results: 5 published, 0 skipped, 0 failed
┌──────────────────────┬────────┬─────────────────────────────────────────────────┐
│ Title                │ Status │ URL                                             │
├──────────────────────┼────────┼─────────────────────────────────────────────────┤
│ 1090-OHH-POL-...     │ OK     │ https://...                                     │
│ 1034-OHH-PRO-...     │ SKIP   │ (collision, skipped)                            │
└──────────────────────┴────────┴─────────────────────────────────────────────────┘
```

---

## Error Handling

| Error | Action |
|---|---|
| 401/403 | Credentials invalid — direct to token refresh at https://id.atlassian.com/manage-profile/security/api-tokens |
| 404 space | Space key wrong — list available spaces from SESSION_TREE |
| 404 parent | Title not found — show tree search results, ask user to confirm |
| ADF invalid | Log failing section, attempt auto-repair, re-validate before retry |
| Network timeout | Retry up to 3 times with 2s backoff |

---

## Additional Resources

- **`references/api-reference.md`** — full Confluence API reference, endpoint details, known gotchas
- **`references/templates.md`** — template structures (Policy, Procedure, Form, Checklist, ISO 27001, etc.)

---

## Audit and Remediation (Steps A1–A4)

Use these steps when the user asks to audit or fix existing Confluence pages, not when publishing new content.

### Step A1 — Resolve Scope

Determine what to scan:
- If `--folder` is set: resolve the folder/page ID via CQL, then use `ancestor={id}` to find all descendant pages
- If no folder: scan the entire space using `space="{key}" AND type=page`

Use CQL (`/wiki/rest/api/content/search`) — the v2 pages API silently omits folder-type nodes.

### Step A2 — Audit Each Page

**Skip eSign versioning pages:** Pages whose titles begin with a pattern like `NNNN(01)`, `NNNN(02)`, etc. (e.g. `0007(01) FRM-0007-...`) are document control versioning artifacts automatically created by the eSign / Document Control plugin. Do not flag, rename, or include these in any audit or title cleanup output — ignore them entirely.

For each remaining page:
1. `GET /wiki/api/v2/pages/{id}?body-format=atlas_doc_format` — fetch ADF body
2. Extract plain text from ADF using `_extract_text_from_adf()`
3. `detect_template_from_text(text)` — infer template type
4. `check_template_sections(adf_content, template)` — find missing required sections
5. `validate_naming_convention(title, template)` — check the page title against naming pattern

Collect all results before printing anything.

### Step A3 — Report

Print a structured compliance report:

```
══════════════════════════════════════════════════════════════════════
Audit report — OHH
══════════════════════════════════════════════════════════════════════
  Total pages   : 47
  ✓  Compliant  : 31
  ✗  Issues     : 16
──────────────────────────────────────────────────────────────────────
Non-compliant pages:

  ACME-POL-003 Information Security Policy
    Template : policy
    Missing  : Compliance and Exceptions, Revision History

  HR Onboarding Checklist
    Template : checklist
    Missing  : Completion
    Naming   : expected — ORG-CHK-001 Document Title
```

### Step A4 — Remediate (if requested)

**Missing sections:** Do NOT auto-add missing sections. Report them to the user (they appear in the audit output from Step A3) and let the user decide whether to add them. Only insert a section when the user explicitly confirms it for a specific page.

When a section addition is confirmed:
1. Fetch ADF (already available from Step A2)
2. Insert new nodes before `Revision History` heading (or at end if not present):
   ```json
   { "type": "heading", "attrs": { "level": 2 }, "content": [{ "type": "text", "text": "Section Name" }] }
   { "type": "panel", "attrs": { "panelType": "warning" }, "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "[TO BE COMPLETED — Section Name]" }] }] }
   ```
3. Preserve insertion order from the template's required section list
4. `PUT /wiki/api/v2/pages/{id}` with version+1 and the patched ADF

**Naming violations:** Do not attempt to fix naming violations here. Direct the user to run the Bulk Title Rename workflow (Steps R1–R5 below).

Always show a remediation plan and wait for confirmation before making any changes (unless `--go` is set).

---

## Bulk Title Rename (Steps R1–R5)

Use when the user asks to "clean up titles", "fix page names", "rename pages", or "bulk rename" in a space.

### Step R1 — Run Audit to Find Naming Violations

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --audit {SPACE_KEY}
```

From the output, collect only pages listed under "Naming violations". Ignore all other audit findings (missing sections, etc.).

### Step R2 — Categorize Violations

Split naming violations into two buckets:

**Bucket A — Formatting errors** (already have a doc number prefix, but malformed):
- Underscores in title (e.g. `PRO-2035-ABC-Risk_Based_Testing_Process`)
- Other character encoding issues

Fix: replace underscores with spaces. Preserve the existing doc number.

**Bucket B — Missing doc prefix** (no `DOC_TYPE-NNNN` prefix at all):
- Date-stamped pages (e.g. `11-19-2025 - Access Review Record`)
- Plain-language titles (e.g. `Logging and Monitoring Process`)

For Bucket B, propose a doc type for each page based on the classification rules and ask the user to confirm — do not silently assume. Present it like:

```
These pages are missing a doc type prefix. Proposed renames — confirm or correct each:

  "Logging and Monitoring Process"  → PRO-XXXX-[ORG]-Logging and Monitoring Process  [process]
  "Creating JIRAs"                  → PRO-XXXX-[ORG]-Creating JIRAs                  [process — confirm?]
  "Change Risk Assessment"          → FRM or REC? ← ask user
  "11-19-2025 - Access Review"      → REC-XXXX-[ORG]-Access Review 2025-11-19        [record]
```

For records with date stamps, move the date to the end of the title in ISO format (`YYYY-MM-DD`).

Always skip: eSign versioning pages (`NNNN(01)` prefix), space homepages, folder pages, and PDF attachment pages.

### Step R3 — Assign Doc Numbers

For each Bucket B page that needs a new number, query the space live — do not use any local spreadsheet:

```python
# CQL to find all existing doc numbers in the space
GET /wiki/rest/api/content/search?cql=space="{KEY}" AND type=page&limit=200&expand=title
# Extract all NNNN numbers from titles using regex \b(\d{4})\b, take max+1
```

Assign numbers sequentially across all pages in this rename batch. Show the full proposed number sequence in the rename plan.

### Step R4 — Show Rename Plan and Confirm

Before touching anything, print:

```
Rename plan — {SPACE_KEY} ({N} pages):

  Current title                               New title
  ──────────────────────────────────────────  ──────────────────────────────────────────
  PRO-2035-ABC-Risk_Based_Testing_Process     PRO-2035-ABC-Risk Based Testing Process
  Logging and Monitoring Process              PRO-2042-ABC-Logging and Monitoring Process
  11-19-2025 - Access Review Record           REC-2037-ABC-Access Review Record 2025-11-19
  Incident Response Plan                      [NEEDS INPUT — doc type?]

Confirm? (yes / adjust / cancel)
```

Wait for explicit confirmation before proceeding.

### Step R5 — Execute Renames

For each rename:

```python
# 1. Fetch current version (required for optimistic locking)
GET /wiki/rest/api/content/search?cql=space="{KEY}" AND title="{OLD_TITLE}"&expand=version&limit=1

# 2. PUT with version+1 — body omitted to preserve existing content
PUT /wiki/api/v2/pages/{id}
{ "id": id, "status": "current", "title": new_title, "version": { "number": current_version + 1 } }
```

**409 conflict handling:** Re-fetch the page to get the latest version and retry once. If it fails again, report as FAIL and continue.

Print results as each rename completes:
```
OK   "Logging and Monitoring Process" → "PRO-2042-ABC-Logging and Monitoring Process"
FAIL "On-Call Process" → 409 conflict (retried, failed)
```

Print totals at the end: X renamed, Y failed.

