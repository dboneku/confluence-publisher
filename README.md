# confluence-publisher

A Claude Code plugin that converts `.docx` files and Google Docs into properly structured Confluence pages — with structural analysis, formatting cleanup, template detection, and direct publishing via the Confluence Cloud REST API.

## Features

- **Smart conversion** — preserves headings, tables, bullet/numbered lists, bold/italic/underline
- **Google Docs support** — exports as HTML (not plain text), preserving heading levels, lists, tables, and inline formatting
- **Formatting cleanup** — fixes consecutive headings, style misuse, Roman numeral lists, multiline heading paragraphs
- **Template auto-detection** — identifies Policy, Procedure, Workflow, Form, Checklist, Meeting Minutes, ISO 27001, and more
- **Template compliance checking** — validates required sections are present for the detected template before publishing
- **Naming convention validation** — flags filenames that don't match the template naming pattern (e.g. `ACME-POL-001 Title`)
- **Full Confluence tree scan** — finds pages and folders at any nesting depth (including Confluence folder types)
- **Bulk publishing** — publish an entire folder or zip archive in one command
- **Upload plan** — always shows what will be published, with compliance warnings, before touching Confluence
- **doc-lint integration** — if the [doc-lint](https://github.com/dboneku/doc-lint) plugin is installed, uses its full rule set for richer analysis and pre-publish cleanup

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

```
/confluence-publisher:setup
```

This creates a `.env` file in your project directory:

```
ATLASSIAN_URL=https://your-org.atlassian.net
ATLASSIAN_EMAIL=you@example.com
ATLASSIAN_API_TOKEN=your-token-here
```

**Generate your API token** at: https://id.atlassian.com/manage-profile/security/api-tokens

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

```
/confluence-publisher:analyze docs/MyPolicy.docx
```

Reports: consecutive headings, style misuse, list type issues, auto-detected template, missing required sections, and naming convention compliance.

### `/confluence-publisher:publish-file <file> [--go]`
Convert and publish a single `.docx` file or Google Doc URL to Confluence.

```
/confluence-publisher:publish-file docs/MyPolicy.docx
/confluence-publisher:publish-file https://docs.google.com/document/d/... --go
```

Add `--go` to skip the upload plan confirmation prompt.

### `/confluence-publisher:publish-folder <folder> [--go]`
Convert and publish all `.docx` files in a folder.

```
/confluence-publisher:publish-folder ./HR-Policies --go
```

Shows a full upload plan table for all files before publishing.

### `/confluence-publisher:publish-zip <archive.zip> [--go]`
Unzip an archive and publish all `.docx` files inside it.

```
/confluence-publisher:publish-zip exports/Q1-Policies.zip
```

Extracts to a temp directory, publishes, then cleans up automatically.

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

### `confluence-publisher`
Handles the full Confluence workflow: credential validation, space/tree discovery, upload planning, collision detection, and publishing.

## Supported Input Formats

| Format | Support |
|---|---|
| `.docx` (Word) | Full formatting preservation |
| Google Docs URL | Export via Google Docs HTML API |
| `.pdf` | Text extraction (formatting not preserved) |
| `.md` / `.txt` | Plain text |

## License

MIT
