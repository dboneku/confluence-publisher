---
name: confluence-publisher-web
description: Use this skill when the user wants to "publish to Confluence", "upload a document to Confluence", "set up Confluence credentials", "list Confluence spaces", "select a space", "show the page tree", "navigate to a folder", "find a Confluence page", "audit Confluence pages", "check Confluence compliance", "remediate Confluence pages", "fix missing sections in Confluence", "set a regulation", or mentions ISO 27001 — and the user is NOT running Claude Code CLI. This skill makes Confluence API calls directly without requiring Python scripts, working in Claude.ai, Claude coworker, and Claude Projects.
version: 0.4.0
---

# Confluence Publisher Skill (Web / No-CLI)

Publish documents to Confluence Cloud and manage compliance directly via the Confluence REST API — no Python scripts required. Works in Claude.ai, Claude coworker, and Claude Projects where shell execution is unavailable.

**Capability differences from the CLI plugin:**

| Feature | Web skill | CLI plugin |
|---|---|---|
| Credential validation | ✓ (API call) | ✓ (publish.py) |
| List/navigate spaces and page tree | ✓ (API call) | ✓ (publish.py) |
| Publish `.docx` | Partial — manual ADF conversion from document content | Full — publish.py runs docx_to_adf() with doc-lint cleanup |
| Publish Google Doc, PDF, Excel | Limited — paste/upload content manually | Full — automated ingestion |
| Regulation doc ID injection | ✓ (manual fuzzy match) | ✓ (automated) |
| Audit and remediate pages | ✓ (API calls) | ✓ (API calls via publish.py) |
| Auto-fix via doc-lint | ✗ (scripts required) | ✓ (if doc-lint installed) |

For full automated conversion and cleanup, install the CLI plugin: `claude plugin install https://github.com/dboneku/confluence-publisher`

---

## Step 0 — Check for doc-converter

Check whether the `doc-converter` or `doc-converter-web` skill is available in this session.

- If available: use it for structural analysis and ADF conversion guidance (Steps 2–6).
- If not available: ask the user —
  ```
  The doc-converter skill isn't loaded. It handles formatting analysis and ADF conversion.
  Continue without it? (Built-in rules only)
  ```

---

## Step 1 — Check Regulation Context

Check the current working directory for `.confluence-config.json`:

```bash
# Look for: { "regulation": "iso27001" }
```

If found, load that regulation's document catalog into session memory as `REGULATION_DOCS`. Use the ISO 27001 catalog embedded in `references/templates.md`.

If no regulation is set, ask the user once:
```
Are you working under a specific regulatory framework? (e.g. ISO 27001)
  1. ISO 27001  2. None / skip
```

**When a regulation is active during publishing:**
- Fuzzy-match the document title against the regulation catalog (Jaccard similarity ≥ 0.35)
- If matched, prepend the doc ID to the page title: `OHH-POL-001 Information Security Policy`
- Strip the first heading from the document body if it closely matches the page title (≥ 0.5 similarity)

---

## Step 2 — Validate Credentials

Ask the user for, or load from `.env` in the working directory:

```
ATLASSIAN_URL=https://your-org.atlassian.net
ATLASSIAN_EMAIL=you@example.com
ATLASSIAN_API_TOKEN=your-token
```

Test with a credential check — make a GET request to the spaces API:
```
GET {ATLASSIAN_URL}/wiki/api/v2/spaces?limit=1
Authorization: Basic base64(EMAIL:TOKEN)
Accept: application/json
```

If 401/403: tell the user credentials are invalid and direct them to https://id.atlassian.com/manage-profile/security/api-tokens.

---

## Step 3 — Discover Spaces and Build Full Tree (SESSION_TREE)

On first use in a session, fetch all spaces:
```
GET {ATLASSIAN_URL}/wiki/api/v2/spaces?limit=250
```

For the selected space, fetch the page tree using CQL (required to find folder-type nodes):
```
GET {ATLASSIAN_URL}/wiki/rest/api/content/search?cql=space="{KEY}" AND ancestor=root&limit=50&expand=ancestors
```

Cache as `SESSION_SPACES` and `SESSION_TREE`. Do not re-fetch during the session.

**Note:** Confluence folders are type `folder` and only discoverable via CQL — never via the v2 pages API.

---

## Step 4 — Select Target Space and Parent

Ask the user to select a space (or confirm if already specified). Then ask where in the space to publish:

- Space root
- Under a named parent page or folder

Resolve parent using `SESSION_TREE` first. If not found: run a CQL search:
```
GET {ATLASSIAN_URL}/wiki/rest/api/content/search?cql=space="{KEY}" AND title="{TITLE}" AND type in (page, folder)
```

---

## Step 5 — Convert Document to ADF

**For uploaded or pasted `.docx` content:**

Apply conversion manually using the doc-converter-web skill if available, or built-in rules:

1. Build a document outline: identify headings (H1–H6), body paragraphs, lists, and tables
2. Apply cleanup rules (same as `references/cleanup-rules.md`):
   - Normalize consecutive headings, style misuse, list numbering, single-item lists
   - Detect template type (Policy, Procedure, Form, Checklist, Meeting Minutes, ISO 27001)
   - Check required sections against template
3. Convert to ADF node structure manually

**For Google Doc URLs:**
Export as HTML:
```
https://docs.google.com/feeds/download/documents/export/Export?id={DOC_ID}&exportFormat=html
```
Parse HTML → ADF using `references/style-mapping.md` mappings.

**For Markdown/text:**
Map headings (`#` → H1, etc.), paragraphs, and lists to ADF nodes directly.

---

## Step 6 — Build Upload Plan

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

Wait for explicit confirmation before proceeding.

---

## Step 7 — Collision Detection

Before creating each page:
```
GET {ATLASSIAN_URL}/wiki/rest/api/content/search?cql=space="{KEY}" AND title="{TITLE}"&limit=1
```

If collision found: ask the user — Overwrite, Skip, or Cancel.

---

## Step 8 — Publish

**Create page:**
```
POST {ATLASSIAN_URL}/wiki/api/v2/pages
Authorization: Basic base64(EMAIL:TOKEN)
Content-Type: application/json

{
  "spaceId": "{SPACE_ID}",
  "status": "current",
  "title": "{TITLE}",
  "parentId": "{PARENT_ID}",
  "body": {
    "representation": "atlas_doc_format",
    "value": "{ADF_JSON_STRING}"
  }
}
```

**Update (overwrite):**
```
GET {ATLASSIAN_URL}/wiki/api/v2/pages/{id}   # get current version number
PUT {ATLASSIAN_URL}/wiki/api/v2/pages/{id}
{ "id": "{id}", "status": "current", "title": "{TITLE}", "version": { "number": current+1 }, "body": { ... } }
```

Always `json.dumps()` the ADF dict — the `value` field must be a JSON string.

---

## Step 9 — Report Results

```
Published: "Title"
  URL: https://org.atlassian.net/wiki/spaces/OHH/pages/12345/Title
  Space: OHH | Parent: Hiring | Nodes: 36
```

---

## Error Handling

| Error | Action |
|---|---|
| 401/403 | Credentials invalid — direct to https://id.atlassian.com/manage-profile/security/api-tokens |
| 404 space | Space key wrong — list available spaces from SESSION_TREE |
| 404 parent | Title not found — show tree search results, ask user to confirm |
| ADF invalid | Log failing section, attempt auto-repair, re-validate before retry |
| Network timeout | Retry up to 3 times with 2s backoff |

---

## Audit and Remediation

Use these steps when the user asks to audit or fix existing Confluence pages.

### Resolve Scope

Determine what to scan:
- If folder specified: resolve via CQL `ancestor={id}` for all descendant pages
- If no folder: scan entire space with `space="{KEY}" AND type=page`

### Audit Each Page

For each page:
1. `GET {ATLASSIAN_URL}/wiki/api/v2/pages/{id}?body-format=atlas_doc_format` — fetch ADF body
2. Extract plain text from ADF — walk `content` nodes, collect `text` leaf values
3. Infer template type from keywords (see `references/templates.md`)
4. Check for missing required sections against the template
5. Validate title naming convention

### Report

Print a structured compliance report showing total pages, compliant vs issues, and details for each non-compliant page (template, missing sections, naming violations).

### Remediate (if requested)

For each page with missing sections:
1. Insert new heading + warning panel nodes before `Revision History` (or at end if not present)
2. `PUT /wiki/api/v2/pages/{id}` with version+1 and patched ADF

**Never auto-fix naming violations** — report and ask user to rename in Confluence.

Always show a remediation plan and wait for confirmation before making changes.

---

## Additional Resources

- **`references/api-reference.md`** — full Confluence API reference, endpoint details, known gotchas
- **`references/templates.md`** — template structures (Policy, Procedure, Form, Checklist, ISO 27001, etc.)
