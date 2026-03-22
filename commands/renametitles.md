---
description: Scan all pages in a Confluence space (or folder) and rename titles to match the standard convention [DOC_TYPE]-[DOC_NUMBER]-[ISO_BRACKET]-[ORG_CODE]-[Document Name]. Shows a rename plan before changing anything; applies fixes only after confirmation.
argument-hint: <space-key> [--org-code "ABC"] [--folder "Folder Name"] [--go]
allowed-tools: Bash
---

Audit and rename Confluence page titles to match the standard naming convention.

Title convention: `[DOC_TYPE]-[DOC_NUMBER]-[ISO_BRACKET]-[ORG_CODE]-[Document Name]`

- **DOC_TYPE**: `POL`, `PRO`, `FRM`, `REC`, `GEN`
- **DOC_NUMBER**: 4-digit zero-padded number (e.g. `1002`, `0007`)
- **ISO_BRACKET**: optional regulation bracket (e.g. `[01-ISMS]`) — omit if not applicable
- **ORG_CODE**: org/space code used in titles — provided by user via `--org-code`, or ask if not supplied
- **Document Name**: Title-cased, spaces preserved — never underscores

**DOC_TYPE classification:**
| Code | Use for |
|---|---|
| `POL` | Policies |
| `PRO` | Processes and procedures |
| `FRM` | Templates and forms |
| `REC` | Records — filled-out instances of forms/templates |
| `GEN` | Guides, how-tos, reference pages, overviews |

---

## Step R1 — Run Audit to Find Naming Violations

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --audit "$SPACE_KEY" [--folder "$FOLDER_NAME"]
```

From the output, collect only pages listed under "Naming violations". Ignore all other audit findings (missing sections, etc.).

**Always skip:**
- Pages whose titles begin with `NNNN(01)`, `NNNN(02)`, etc. — these are eSign / Document Control versioning artifacts, not real pages
- Space homepages, folder pages, and PDF attachment pages

---

## Step R2 — Categorize Violations

Split naming violations into two buckets:

**Bucket A — Formatting errors** (already have a doc number prefix, but malformed):
- Underscores in the document name portion
- Other encoding artifacts

Fix: replace underscores with spaces. Preserve the existing doc number and type prefix exactly.

**Bucket B — Missing doc prefix** (no `DOC_TYPE-NNNN` prefix at all):
- Date-stamped pages (e.g. `11-19-2025 - Access Review Record`)
- Plain-language titles (e.g. `Logging and Monitoring Process`)

For Bucket B, propose a doc type for each page based on the classification rules and present it to the user for confirmation — do not silently assume. Format:

```
These pages are missing a doc type prefix. Proposed renames — confirm or correct each:

  "Logging and Monitoring Process"  → PRO-XXXX-[ORG]-Logging and Monitoring Process  [process]
  "Production Push Checklist"       → FRM-XXXX-[ORG]-Production Push Checklist        [form/template]
  "Change Risk Assessment"          → FRM or REC? ← ask user
  "11-19-2025 - Access Review"      → REC-XXXX-[ORG]-Access Review 2025-11-19         [record]
```

For records with date stamps, move the date to the end of the title in ISO format (`YYYY-MM-DD`).

---

## Step R3 — Assign Doc Numbers

For each Bucket B page that needs a new number, query the space live:

```bash
# CQL to find all existing doc numbers in the space
GET /wiki/rest/api/content/search?cql=space="{KEY}" AND type=page&limit=200&expand=title
# Extract all NNNN numbers from titles using regex \b(\d{4})\b, take max+1
```

Assign numbers sequentially across all pages in this rename batch. Show the full proposed number sequence in the rename plan.

---

## Step R4 — Show Rename Plan and Confirm

Before touching anything, print:

```
Rename plan — {SPACE_KEY} ({N} pages):

  Current title                               New title
  ──────────────────────────────────────────  ──────────────────────────────────────────
  PRO-2035-ABC-Risk_Based_Testing_Process     PRO-2035-ABC-Risk Based Testing Process
  Logging and Monitoring Process              PRO-2042-ABC-Logging and Monitoring Process
  11-19-2025 - Access Review Record           REC-2037-ABC-Access Review Record 2025-11-19
  Change Risk Assessment                      [NEEDS INPUT — FRM or REC?]

Confirm? (yes / adjust / cancel)
```

Wait for explicit confirmation before proceeding, unless `--go` was passed (applies Bucket A fixes immediately; Bucket B items still require input unless already specified).

---

## Step R5 — Execute Renames

For each rename:

```python
# 1. Fetch current version (required for optimistic locking)
GET /wiki/rest/api/content/search?cql=space="{KEY}" AND title="{OLD_TITLE}"&expand=version&limit=1

# 2. PUT with version+1 — body omitted to preserve existing page content unchanged
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

After completion, suggest:
```
To check content compliance: /confluence-publisher:audit {SPACE_KEY}
To fix numbered headings:    /confluence-publisher:fixheadingnumbers {SPACE_KEY}
```
