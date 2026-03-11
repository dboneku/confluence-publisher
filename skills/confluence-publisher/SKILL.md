---
name: confluence-publisher
description: This skill should be used when the user asks to "publish to Confluence", "upload a document to Confluence", "publish a folder to Confluence", "set up Confluence credentials", "list Confluence spaces", "select a space", "show the page tree", "navigate to a folder", "find a Confluence page", "audit Confluence pages", "check Confluence compliance", "remediate Confluence pages", "fix missing sections in Confluence", or mentions publishing, auditing, remediating, or navigating documents in a Confluence wiki. Handles credential validation, space discovery, space/folder navigation (selectspace, cd), page tree visualization, upload planning, collision detection, publishing, compliance auditing, and ADF remediation via the Confluence Cloud REST API.
version: 0.3.0
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

## Step 1 — Validate Credentials

Load credentials from `.env` in the working directory:

```
ATLASSIAN_URL=https://your-org.atlassian.net
ATLASSIAN_EMAIL=you@example.com
ATLASSIAN_API_TOKEN=your-token
```

If any key is missing, stop and tell the user exactly which ones are missing. Direct them to run `/confluence-publisher:setup` or visit https://id.atlassian.com/manage-profile/security/api-tokens.

Test credentials with a quick spaces API call before proceeding.

---

## Step 2 — Discover Spaces and Build Full Tree (SESSION_TREE)

On first use in a session, fetch all spaces and their complete page/folder hierarchy. Cache as `SESSION_TREE` — do not re-fetch during the session.

```python
# All spaces (no type filter — captures knowledge_base, collaboration, global, personal)
GET /wiki/api/v2/spaces?limit=250

# Full tree via CQL — MUST use CQL, not v2 pages API (v2 silently omits folders)
GET /wiki/rest/api/content/search?cql=space="{key}"&limit=200
GET /wiki/rest/api/content/search?cql=parent={id}&limit=200  # per node
```

Present summary:
```
Spaces loaded (9 total):
  OHH   — Oversite Health - HR           (312 pages, 4 folders)
  OHAL  — Oversite Health - Legal        (47 pages)
  ...
```

See `references/api-reference.md` for full API details and known gotchas (folder detection, type filters).

---

## Step 3 — Select Target Space and Parent

Ask the user to select a space (or confirm if already specified). Then ask where in the space to publish:

- Space root
- Under a named parent page or folder

Resolve parent using `SESSION_TREE` first (no API call needed). If not found in tree, use CQL:
```python
GET /wiki/rest/api/content/search?cql=space="{key}" AND title="{title}"&limit=5
```

If still not found: report and ask user to confirm exact title.

**Important:** Confluence folders are type `folder` and only discoverable via CQL — never via the v2 pages API.

---

## Step 4 — Build Upload Plan

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

Wait for explicit confirmation ("yes", "go", "confirm") or `--go` flag before proceeding. Compliance warnings are informational — they do not block publishing, but should be reviewed.

---

## Step 5 — Collision Detection

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

If `--go` flag: default to overwrite silently.

---

## Step 6 — Publish

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

## Step 7 — Report Results

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

For each page:
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

For each page with missing sections:

1. Fetch ADF (already available from Step A2)
2. Insert new nodes before `Revision History` heading (or at end if not present):
   ```json
   { "type": "heading", "attrs": { "level": 2 }, "content": [{ "type": "text", "text": "Section Name" }] }
   { "type": "panel", "attrs": { "panelType": "warning" }, "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "[TO BE COMPLETED — Section Name]" }] }] }
   ```
3. Preserve insertion order from the template's required section list
4. `PUT /wiki/api/v2/pages/{id}` with version+1 and the patched ADF

**Never auto-fix naming violations** — report them and ask the user to rename in Confluence.

Always show a remediation plan and wait for confirmation before making any changes (unless `--go` is set).

