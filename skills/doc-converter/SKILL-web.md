---
name: doc-converter-web
description: Use this skill when the user asks to "convert a document", "upload a document", "publish a document to Confluence", "convert a Word doc", "convert a Google Doc", "process a .docx file", "upload a spreadsheet", "upload an Excel file", "upload a Google Sheet", "upload a PDF", or mentions converting documents to ADF, markdown, or HTML — and the user is NOT running Claude Code CLI. This skill applies document conversion rules directly from uploaded or pasted content without requiring Python scripts, working in Claude.ai, Claude coworker, and Claude Projects.
version: 0.3.0
---

# Document Converter Skill (Web / No-CLI)

Convert `.docx` files, Google Docs, Excel/Google Sheets, and PDFs into Confluence pages or other formats by analyzing document content directly — no Python scripts required. Works in Claude.ai, Claude coworker, and Claude Projects where shell execution is unavailable.

**Capability differences from the CLI plugin:**

| Feature | Web skill | CLI plugin |
|---|---|---|
| Structural analysis (headings, lists, tables) | ✓ (from uploaded content) | ✓ (python-docx) |
| Template auto-detection | ✓ | ✓ |
| Cleanup rules (heading, list, font) | Partial — visible structure only | Full — includes font/style metadata |
| ADF conversion | ✓ (manual) | ✓ (automated via docx_to_adf()) |
| Markdown / HTML output | ✓ | ✓ |
| Excel / Google Sheets (embed viewer) | ✗ (requires script upload) | ✓ |
| PDF text extraction | Partial — if Claude can read content | ✓ (pdfplumber) |
| doc-lint enhanced cleanup | ✗ (scripts required) | ✓ (if doc-lint installed) |

For full automated conversion with metadata-level cleanup, install the CLI plugin: `claude plugin install https://github.com/dboneku/confluence-publisher`

---

## Step 0 — Detect File Type and Route

Check the file type and branch:

| File type | Route |
|---|---|
| `.docx` (uploaded) | Continue to Step 1 |
| Google Doc URL | Continue to Step 1 |
| `.xlsx` / `.xls` / Google Sheets URL | See **Spreadsheet Path** below |
| `.pdf` (uploaded) | See **PDF Path** below |
| `.md` / `.txt` / `.wiki` | Continue to Step 1 (read directly) |

---

### Spreadsheet Path — Excel / Google Sheets

Ask the user:
```
Spreadsheet handling options:
1. Attach + embed viewer  — uploads the file as an attachment and embeds it inline on a
                            Confluence page using the view-file macro. Preserves all tabs,
                            formulas, and formatting. (recommended)
                            Note: requires the CLI plugin to upload the file automatically.
2. Convert to ADF table   — extract data to a plain Confluence table from pasted content.
                            Loses formulas, charts, and multi-tab structure.
```

**Option 1:** Requires CLI plugin (`claude plugin install https://github.com/dboneku/confluence-publisher`). Cannot be automated here.

**Option 2:** Ask the user to paste the spreadsheet data as plain text or CSV. Convert rows to ADF `tableRow` nodes (first row as `tableHeader`). Continue to Step 7.

**For Google Sheets:** Ask user to share sheet data by copying cells and pasting, or export as CSV.

---

### PDF Path

Ask the user:
```
PDF handling options:
1. Static record  — upload the PDF as an attachment and create a Confluence page with an
                    embedded viewer. Note: automated upload requires the CLI plugin.
2. Convert content — extract text from the PDF by having Claude read it, then publish as
                     a structured Confluence page. Best for text-heavy PDFs.
```

**Option 1:** Automated upload requires the CLI plugin. Manual steps: upload via Confluence UI, then create the page with embedded viewer macro.

**Option 2:** Ask user to upload the PDF. Claude will read the text content, then continue to Step 1.

---

## Step 1 — Confirm Output Format

Ask the user what the desired output is (skip if already stated):

```
Output options:
1. Confluence ADF  — publish directly to a Confluence space (default)
2. Markdown        — output a .md file
3. HTML            — output an .html file
```

---

## Step 2 — Ingest the Source

**For `.docx` (uploaded):**
Read the document content. Note: without python-docx, font metadata and exact style properties are not available. Structural elements (headings, paragraphs, lists, tables) are analyzed from visible content.

**For Google Docs:**
Export as HTML (preserves heading levels and inline formatting):
```
https://docs.google.com/feeds/download/documents/export/Export?id={DOC_ID}&exportFormat=html
```
Parse HTML to extract heading levels (h1–h6), paragraphs, lists (ul/ol), and tables. See `references/style-mapping.md` for the HTML → ADF mapping.

**For Markdown / plain text:**
Read directly. Map heading syntax (`#` → H1, etc.) to ADF heading nodes.

---

## Step 3 — Structural Analysis

Run analysis before converting. Report findings to the user before proceeding.

### Checks to perform

| Check | Flag if... | Web detection |
|---|---|---|
| Consecutive headings | More than 2 headings in a row with no body content | ✓ |
| Empty sections | Heading followed immediately by next heading | ✓ |
| Heading level skips | e.g. H1 → H3 with no H2 | ✓ |
| Style misuse | "Heading 1" style used at body-text size | Partial (requires font metadata) |
| Single-item lists | A list with only one item | ✓ |
| Roman numeral lists | Ordered lists using I/II/III or a/b/c | ✓ |
| Non-standard font sizes | Outside standard scale | Partial (requires font metadata) |
| Mixed fonts | More than one font family for body text | Partial (requires font metadata) |
| Orphaned bold/italic | Entire paragraphs in bold or italic | ✓ |
| Numbered heading restart | Manual numbers (e.g. "1. Purpose") resetting mid-doc | ✓ |

### Output format

```
Analysis complete — 3 issues found:
  ⚠ Consecutive headings: lines 12–14 (3 headings, no body text between them)
  ⚠ Style misuse: "Heading 1" used at 11pt on 6 paragraphs — reclassified as body text
  ℹ Roman numeral list detected on lines 34–38 — will normalize to 1/2/3
Proceed with cleanup and conversion? [y/n]
```

Wait for confirmation before continuing.

---

## Step 4 — Auto-Detect Template

Scan the document content for keywords to determine the Confluence template:

| Template | Signal keywords / patterns |
|---|---|
| Policy | "purpose", "scope", "policy statement", "compliance", "shall" |
| Procedure | "steps", "procedure", "prerequisites", "how to", numbered step list |
| Workflow | "trigger", "flow steps", "decision points", "outcomes", "approval" |
| Form | Checkbox characters (☐ ✓), fill-in blanks (`___`), "signature", "date:" |
| Checklist | Majority of content is checkbox items (☐), short lines |
| Meeting Minutes | "attendees", "agenda", "action items", "decisions", date in title |
| ISO 27001 | "ISO", "annex A", "27001", "ISMS", control identifiers (A.x.x) |
| General | No clear match |

If two templates score equally or the match is weak, ask:

```
Best guess: Policy — does that look right, or should I use a different template?
1. Policy  2. Procedure  3. Form  4. Checklist  5. Meeting Minutes  6. ISO 27001  7. General
```

---

## Step 5 — Apply Cleanup Rules

Apply cleanup rules before building output. Full rules in `references/cleanup-rules.md`. Summary:

- **Consecutive headings** — insert placeholder paragraph `[Section content pending]` between 3+ headings with nothing between them
- **Style misuse** — reclassify `Heading 1` paragraphs at ≤12pt as body paragraphs (if visible from content)
- **List numbering** — convert Roman numerals (I/II/III) and alphabetic lists (a/b/c) to Arabic numerals (1/2/3)
- **Single-item lists** — convert to plain paragraph
- **Orphaned bold paragraphs** — if an entire paragraph is bold and follows a heading pattern, offer to promote to heading
- **Numbered heading continuity** — if headings have manual numbers (e.g. "1. Purpose"), flag any level where the sequence restarts and strip number prefixes
- **Template compliance** — compare document headings against required sections list. Report any missing required sections
- **Naming convention** — check the source filename against the expected pattern for the detected template. Report if it doesn't match (see `references/templates.md`)
- **Title heading stripping** — after the final page title is determined, remove the first heading node from the ADF if it closely matches the title (Jaccard similarity ≥ 0.5). Apply this manually during ADF construction

---

## Step 6 — Convert to Target Format

Use the style → ADF/Markdown/HTML mappings in `references/style-mapping.md`.

**For ADF output:** Build the ADF node tree manually, applying cleanup on each node as it's constructed. Validate that the final structure is valid JSON before returning.

**For Markdown output:** Map headings, paragraphs, lists, and tables to standard Markdown syntax. Write output with `.md` extension.

**For HTML output:** Map to semantic HTML (`<h1>`–`<h6>`, `<p>`, `<ul>`, `<ol>`, `<table>`). Write output with `.html` extension.

---

## Step 7 — Report

After conversion, always report:

```
Conversion complete
  Source:    1090-OHH-POL-Applicant Screening Policy.docx
  Output:    Confluence ADF → ready to publish
  Template:  Policy (auto-detected)
  Cleanup:   3 issues fixed, 0 flagged for review
  Nodes:     52 (8 headings, 31 paragraphs, 6 list items, 2 tables)
```

If publishing to Confluence, hand off to the `confluence-publisher-web` skill (or `confluence-publisher` if CLI is available).

---

## Additional Resources

- **`references/cleanup-rules.md`** — full cleanup rules with decision tables and examples
- **`references/style-mapping.md`** — Word style / Google Docs HTML → ADF / Markdown / HTML mapping tables
- **`references/adf-reference.md`** — ADF node type reference for building and validating output
