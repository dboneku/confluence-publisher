# confluence-publisher

A Claude Code plugin that converts `.docx` files and Google Docs into properly structured Confluence pages — with structural analysis, formatting cleanup, template detection, and direct publishing via the Confluence Cloud REST API.

## Features

- **Smart conversion** — preserves headings, tables, bullet/numbered lists, bold/italic/underline
- **Google Docs support** — exports as HTML (not plain text), preserving heading levels, lists, tables, and inline formatting
- **Formatting cleanup** — fixes consecutive headings, style misuse, Roman numeral lists, multiline heading paragraphs
- **Template auto-detection** — identifies Policy, Procedure, Workflow, Form, Checklist, Meeting Minutes, ISO 27001, and more
- **Template compliance checking** — validates required sections are present for the detected template before publishing
- **Naming convention validation** — flags filenames that don't match the template naming pattern (e.g. `OHH-POL-001 Title`) — prefix-first names also enable bulk document control configuration in eSign for Confluence
- **Full Confluence tree scan** — finds pages and folders at any nesting depth (including Confluence folder types)
- **Bulk publishing** — publish an entire folder or zip archive in one command
- **Upload plan** — always shows what will be published, with compliance warnings, before touching Confluence
- **doc-lint integration** — if the [doc-lint](https://github.com/dboneku/doc-lint) plugin is installed, uses its full rule set for richer analysis and pre-publish cleanup
- **Space audit** — scan existing Confluence pages for template compliance and naming convention violations
- **Auto-remediation** — patch non-compliant pages by inserting missing section placeholders without removing existing content
- **eSign-ready naming** — all naming conventions put the doc type prefix first so eSign for Confluence Space Settings can match and apply approval/review workflows per document type automatically

## Installation

```bash
claude plugin install https://github.com/dboneku/confluence-publisher
```

Then install Python dependencies in your project directory:

```bash
pip install -r ~/.claude/plugins/*/confluence-publisher/scripts/requirements.txt
```

## Setup

Run the guided setup command to configure your Confluence credentials:

```text
/confluence-publisher:setup
```

This creates a `.env` file in your project directory:

```dotenv
ATLASSIAN_URL=https://your-org.atlassian.net
ATLASSIAN_EMAIL=you@example.com
ATLASSIAN_API_TOKEN=your-token-here
```

**Generate your API token** at: <https://id.atlassian.com/manage-profile/security/api-tokens>

### ⚠️ Keep credentials out of Git

Add `.env` to your `.gitignore` immediately:

```bash
echo ".env" >> .gitignore
```

Never commit your API token. If you accidentally do, revoke it immediately at the link above and generate a new one.

## Commands

### `/confluence-publisher:setup`

Guided credential configuration. Tests the connection and confirms you can reach your Confluence instance.

### `/confluence-publisher:analyze <file>`

Analyze a document's structure and report issues without publishing anything.

```text
/confluence-publisher:analyze docs/MyPolicy.docx
```

Reports: consecutive headings, style misuse, list type issues, auto-detected template, missing required sections, and naming convention compliance.

### `/confluence-publisher:publish-file <file> [--go]`

Convert and publish a single `.docx` file or Google Doc URL to Confluence.

```text
/confluence-publisher:publish-file docs/MyPolicy.docx
/confluence-publisher:publish-file https://docs.google.com/document/d/... --go
```

Add `--go` to skip the upload plan confirmation prompt.

### `/confluence-publisher:publish-folder <folder> [--go]`

Convert and publish all `.docx` files in a folder.

```text
/confluence-publisher:publish-folder ./HR-Policies --go
```

Shows a full upload plan table for all files before publishing.

### `/confluence-publisher:publish-zip <archive.zip> [--go]`

Unzip an archive and publish all `.docx` files inside it.

```text
/confluence-publisher:publish-zip exports/Q1-Policies.zip
```

Extracts to a temp directory, publishes, then cleans up automatically.

### `/confluence-publisher:audit <space-key> [--folder "Name"]`

Scan existing Confluence pages for template compliance. Read-only — nothing is modified.

```text
/confluence-publisher:audit OHH
/confluence-publisher:audit OHH --folder "HR Policies"
```

For each page, detects the template, checks for missing required sections, and validates the naming convention. Produces a full compliance report grouped by page.

### `/confluence-publisher:remediate <space-key> [--folder "Name"] [--go]`

Audit then automatically patch non-compliant pages by inserting warning-panel placeholders for every missing required section.

```text
/confluence-publisher:remediate OHH
/confluence-publisher:remediate OHH --folder "HR Policies" --go
```

Shows a remediation plan (which pages, which sections) before making any changes. Missing sections are inserted before `Revision History` (or appended at end) as an H2 heading + yellow warning panel with `[TO BE COMPLETED — Section Name]`. Naming convention violations are reported but require manual renaming in Confluence.

### `/confluence-publisher:fixheadingnumbers [<space-key> | --all-spaces] [--folder "Name"] [--go]`

Scan existing Confluence pages for numbered heading-like blocks and normalize them.

```text
/confluence-publisher:fixheadingnumbers OHH
/confluence-publisher:fixheadingnumbers OHH --folder "Legal"
/confluence-publisher:fixheadingnumbers --all-spaces --go
```

The fixer strips numeric prefixes like `1. Purpose` or `2.1 Scope`, converts short numbered paragraphs into headings, defaults them to H1, and uses a simple heuristic when it sees an adjacent `1` then `2` pair: the `1` becomes H1 and following numbered headings remain H2 until another adjacent `1` then `2` pair starts a new major section.

## Document Control with eSign for Confluence

If you need formal document control — approvers, reviewers, e-signature workflows, retention policies — the [eSign for Confluence](https://marketplace.atlassian.com/apps/1217038/esign-for-confluence) app supports **bulk configuration by document ID prefix** through its Space Settings UI. No scripting required.

**Plugin documentation:** [eSign for Confluence docs](https://support.esign-app.com/edoc) | [Space Settings guide](https://support.esign-app.com/edoc/guide/config/space-settings)

If you want to apply the same eSign document-type policy across many spaces, use [scripts/sync_esign_space_settings.py](scripts/sync_esign_space_settings.py). The eSign docs describe webhook event payloads and space-level settings, but they do not publish a supported admin REST API for bulk updates, so the script uses Confluence REST to list spaces and Playwright to drive the eSign Space Settings UI.

### Bulk sync script

The included sync script standardizes these document types:

- `POL` — Policy
- `PRO` — Procedure / Process
- `FRM` — Form
- `REC` — Record

It configures annual review, annual approval, annual training, and sets these document admins:

- `nick@clinicaloversite.com`
- `doug@clinicaloversite.com`
- `janet@clinicaloversite.com`

Setup:

```bash
pip install -r scripts/requirements.txt
playwright install chromium
```

Save a logged-in Playwright session once, for example with:

```bash
playwright codegen https://oversite-health.atlassian.net --save-storage ~/.config/confluence/storage-state.json
```

Then run the sync in dry-run mode first:

```bash
python scripts/sync_esign_space_settings.py \
   --storage-state ~/.config/confluence/storage-state.json \
   --settings-url-template 'https://oversite-health.atlassian.net/wiki/spaces/{spaceKey}/settings/apps/{appPath}' \
   --app-path 'com.digitalrose.edoc__space-settings'
```

Apply the changes after verifying the plan:

```bash
python scripts/sync_esign_space_settings.py \
   --storage-state ~/.config/confluence/storage-state.json \
   --settings-url-template 'https://oversite-health.atlassian.net/wiki/spaces/{spaceKey}/settings/apps/{appPath}' \
   --app-path 'com.digitalrose.edoc__space-settings' \
   --apply
```

The exact `--app-path` can vary by eSign installation. Open one working eSign Space Settings page in the browser, copy its URL once, and use the matching route segment here.

### How it works

1. confluence-publisher already enforces prefix-first naming conventions for all controlled document types:

   ```text
   OHH-POL-001 Information Security Policy
   OHH-PRO-002 Onboarding Procedure
   OHH-FRM-003 Incident Report Form
   ```

2. In eSign → **Space Settings → Document Types**, create a document type for each prefix (e.g. `OHH-POL`, `OHH-PRO`, `OHH-FRM`).

3. For each document type, configure:
   - **Approvers** and approval workflow
   - **Reviewers** and review cadence
   - **e-Signature requirements**
   - **Permissions** (who can view, edit, approve)
   - **Retention and review schedule**

   Any Confluence page whose title starts with that prefix automatically inherits those settings.

4. Publish all your controlled documents with confluence-publisher. Because the prefix is always first in the title, every page is automatically picked up by the matching eSign document type — no per-page configuration needed.

### Recommended prefix structure

| Document type | Prefix | Example title |
| --- | --- | --- |
| Policy | `[Org]-POL` | `OHH-POL-001 Information Security Policy` |
| Procedure | `[Org]-PRO` | `OHH-PRO-002 Onboarding Procedure` |
| Workflow | `[Org]-WF` | `OHH-WF-003 Incident Response Workflow` |
| Form | `[Org]-FRM` | `OHH-FRM-004 Access Request Form` |
| Checklist | `[Org]-CHK` | `OHH-CHK-005 New Hire Checklist` |
| ISO 27001 | `[Org]-ISMS` | `OHH-ISMS-006 Risk Assessment Policy` |

These prefixes are the same ones confluence-publisher validates and enforces through its naming convention rules — so your eSign document types and your published page titles will always stay in sync.

---

## How It Works

1. **Analyzes** the document structure (headings, lists, tables, font sizes, style misuse)
2. **Detects** the best Confluence template (Policy, Procedure, Workflow, Form, Checklist, Meeting Minutes, ISO 27001)
3. **Checks compliance** — reports missing required sections and naming convention issues before publishing
4. **Applies cleanup rules**:
   - Consecutive same-level headings (≥ 3) → bullet lists
   - Heading-styled body text → reclassified as paragraphs
   - Multiline heading paragraphs → split into heading + body
   - Roman numeral / alphabetic lists → Arabic numbered lists
   - Single-item lists → plain paragraphs
   - Numbered headings that restart mid-document → renumbered continuously
5. **Scans** the Confluence space tree (including folders — which the v2 API silently misses)
6. **Shows** an upload plan with compliance warnings and waits for confirmation
7. **Publishes** using the Confluence Cloud REST API v2

## Requirements

- Claude Code
- Python 3.9+
- A Confluence Cloud account with API access
- Dependencies: `requests`, `python-dotenv`, `python-docx` (install via `requirements.txt`)

## Skills Included

### `confluence-publisher`

Handles credential validation, space discovery, page tree scanning, upload planning, collision detection, and publishing via the Confluence Cloud REST API.

### `doc-converter`

Handles document ingestion, structural analysis, formatting cleanup, template detection, compliance checking, and ADF conversion. Can be used independently of Confluence publishing.

## Supported Input Formats

| Format | Support |
| --- | --- |
| `.docx` (Word) | Full formatting preservation |
| Google Docs URL | Export via Google Docs HTML API |
| `.pdf` | Text extraction (formatting not preserved) |
| `.md` / `.txt` | Plain text |

## License

MIT
