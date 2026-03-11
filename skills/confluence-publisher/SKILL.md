---
name: confluence-publisher
description: This skill should be used when the user asks to "publish to Confluence", "upload a document to Confluence", "publish a folder to Confluence", "set up Confluence credentials", "list Confluence spaces", "find a Confluence page", or mentions publishing documents to a Confluence wiki. Handles credential validation, space discovery, page tree scanning, upload planning, collision detection, and publishing via the Confluence Cloud REST API.
version: 0.1.0
---

# Confluence Publisher Skill

Publish converted documents to Confluence Cloud using the REST API. Always pairs with the `doc-converter` skill for document ingestion and formatting.

---

## Step 0 — Check doc-converter

Before any publish operation, check whether the `doc-converter` skill is available in this session.

- If available: use it for all document conversion (Step 2 of every publish flow).
- If not available: ask the user —
  ```
  The doc-converter skill isn't loaded. It handles formatting cleanup and proper ADF conversion.
  Install it? (Recommended — run: claude plugin install https://github.com/dboneku/confluence-publisher)
  Or continue without it? (Raw text extraction only, no formatting cleanup)
  ```
  If user declines: use plain-text extraction via `python-docx` and skip all cleanup rules.

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

Collision handling: [ ] Overwrite  [ ] Skip  [ ] Ask per file
```

Wait for explicit confirmation ("yes", "go", "confirm") or `--go` flag before proceeding.

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
