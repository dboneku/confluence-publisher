---
name: doc-converter
description: This skill should be used when the user asks to "convert a document", "upload a document", "publish a document to Confluence", "convert a Word doc", "convert a Google Doc", "process a .docx file", "upload a spreadsheet", "upload an Excel file", "upload a Google Sheet", "upload a PDF", or mentions converting documents to ADF, markdown, or HTML. Handles structural analysis, formatting cleanup, template detection, and conversion of .docx, Google Docs, Excel, Google Sheets, and PDFs to Confluence pages.
version: 0.2.0
---

# Document Converter Skill

Convert `.docx` files, Google Docs, Excel/Google Sheets, and PDFs into Confluence pages with a consistent analysis-first workflow, formatting cleanup, and template auto-detection.

---

## Step 0 — Detect File Type and Route

Before anything else, check the file type and branch:

| File type | Route |
|---|---|
| `.docx` | Continue to Step 1 |
| Google Doc URL | Continue to Step 1 |
| `.xlsx` / `.xls` / Google Sheets URL | Go to **Spreadsheet Path** below |
| `.pdf` | Go to **PDF Path** below |
| `.md` / `.txt` / `.wiki` | Continue to Step 1 (read directly) |

---

### Spreadsheet Path — Excel / Google Sheets

Ask the user:
```
Spreadsheet handling options:
1. Attach + embed viewer  — uploads the file as an attachment and embeds it inline on a
                            Confluence page using the view-file macro. Preserves all tabs,
                            formulas, and formatting. (recommended)
2. Convert to ADF table   — extracts data to a plain Confluence table. Loses formulas,
                            charts, and multi-tab structure.
```

**Option 1 — Attach + embed viewer (preferred):**
1. Create the Confluence page using the **v1 storage format API** (not v2/ADF) with the `view-file` macro:
   ```xml
   <ac:structured-macro ac:name="view-file" ac:schema-version="1">
     <ac:parameter ac:name="name"><ri:attachment ri:filename="FILENAME.xlsx" /></ac:parameter>
   </ac:structured-macro>
   ```
   Use `POST /wiki/rest/api/content` with `body.storage`. The v2/ADF API rejects extension nodes.
2. Upload the file as an attachment: `POST /wiki/rest/api/content/{pageId}/child/attachment` with header `X-Atlassian-Token: no-check`.
3. Report the page URL. Skip Steps 1–7.

**Option 2 — Convert to ADF table:**
Use `pandas` to read the first sheet, convert rows to ADF `tableRow` nodes (first row as `tableHeader`). Continue to Step 7.

**For Google Sheets:** Export as CSV for Option 2. For Option 1, ask the user to download as `.xlsx` first.

---

### PDF Path

Ask the user:
```
PDF handling options:
1. Static record  — upload the PDF as an attachment and create a Confluence page with an
                    embedded viewer. Content is not extracted. Best for signed documents,
                    certificates, or any PDF that must be preserved exactly as-is.
2. Convert content — extract text and publish as a structured Confluence page (uses
                     pdfplumber). Best for text-heavy PDFs like policies or procedures
                     that need to be searchable and editable in Confluence.
```

**Option 1 — Static record:** Same attach + view-file macro pattern as spreadsheets. Skip Steps 1–7.

**Option 2 — Convert content:** Use `pdfplumber` to extract text, then continue to Step 1.

---

## Step 1 — Confirm Output Format

Before doing anything else, ask the user what the desired output is:

```
Output options:
1. Confluence ADF  — publish directly to a Confluence space (default)
2. Markdown        — output a .md file
3. HTML            — output an .html file
```

If the user has already stated the target (e.g. "publish to Confluence"), skip this step.

---

## Step 2 — Ingest the Source

**For `.docx`:**
`publish.py` automatically detects whether `doc-lint` is installed. If it is, `doc-lint`'s `fix.py` runs on the file first (applying its full rule set), then `docx_to_adf()` converts the pre-cleaned file. If `doc-lint` is not installed, `docx_to_adf()` applies its built-in cleanup rules directly during conversion. Either way, no manual action needed — the best available rules are used automatically.

**For Google Docs:**
Export as HTML (not plain text) to preserve heading levels and inline formatting:
```
https://docs.google.com/feeds/download/documents/export/Export?id={DOC_ID}&exportFormat=html
```
Parse the HTML to extract heading levels (`h1`–`h6`), paragraphs, lists (`ul`/`ol`), and tables. See `references/style-mapping.md` for the HTML → ADF mapping.

---

## Step 3 — Structural Analysis

Run analysis before converting. Report findings to the user before proceeding.

### Checks to perform

| Check | Flag if... |
|---|---|
| Consecutive headings | More than 2 headings in a row with no body content between them |
| Empty sections | A heading is followed immediately by the next heading (no content at all) |
| Heading level skips | e.g. H1 → H3 with no H2 in between |
| Style misuse | Word "Heading 1" style used at body-text size (≤12pt) |
| Single-item lists | A list with only one item (should be a paragraph) |
| Roman numeral lists | Ordered lists using I/II/III or a/b/c instead of 1/2/3 |
| Non-standard font sizes | Any size outside the standardized scale (see `references/cleanup-rules.md`) |
| Mixed fonts | More than one font family used for body text |
| Orphaned bold/italic | Entire paragraphs in bold or italic (usually means they should be headings) |
| Numbered heading restart | Headings with manual numbers (e.g. "1. Purpose") that reset to 1 mid-document at the same level |

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

Scan the document content for keywords to determine the Confluence template. Apply the first match:

| Template | Signal keywords / patterns |
|---|---|
| Policy | "purpose", "scope", "policy statement", "compliance", "shall" |
| Procedure | "steps", "procedure", "prerequisites", "how to", numbered step list |
| Form | Checkbox characters (☐ ✓), fill-in blanks (`___`), "signature", "date:" |
| Checklist | Majority of content is checkbox items (☐), short lines |
| Meeting Minutes | "attendees", "agenda", "action items", "decisions", date in title |
| ISO 27001 | "ISO", "annex A", "27001", "ISMS", control identifiers (A.x.x) |
| General | No clear match |

If two templates score equally, or if the match is weak, ask:

```
Best guess: Policy — does that look right, or should I use a different template?
1. Policy  2. Procedure  3. Form  4. Checklist  5. Meeting Minutes  6. ISO 27001  7. General
```

---

## Step 5 — Apply Cleanup Rules

Apply all cleanup rules before building the output. Full rules in `references/cleanup-rules.md`. Summary:

- **Consecutive headings** — insert a placeholder paragraph `[Section content pending]` between headings if there are 3+ in a row with nothing between them. Flag for user review.
- **Style misuse** — reclassify `Heading 1` paragraphs at ≤12pt as body paragraphs.
- **Font sizes** — normalize to the standard scale (H1=20pt, H2=16pt, H3=14pt, H4=12pt, body=11pt). Do not change heading *level*, only the rendered size mapping.
- **Fonts** — standardize body text font to the document's declared default. Flag mixed fonts in headers.
- **List numbering** — convert Roman numerals (I/II/III) and alphabetic lists (a/b/c) to Arabic numerals (1/2/3).
- **Single-item lists** — convert to a plain paragraph.
- **Orphaned bold paragraphs** — if an entire paragraph is bold and follows a heading pattern, offer to promote it to a heading.
- **Numbered heading continuity** — if headings include manual Arabic numbers (e.g. "1. Purpose"), detect any level where the sequence restarts mid-document and renumber to be continuous. Hierarchical sub-numbering that resets per parent (1.1, 1.2 → 2.1, 2.2) is correct and must not be changed.

---

## Step 6 — Convert to Target Format

Use the style → ADF/Markdown/HTML mappings in `references/style-mapping.md`.

For ADF output, use `docx_to_adf()` in `publish.py` as the base, then apply cleanup on top of the returned ADF node tree. Validate ADF as parseable JSON before publishing.

For Markdown or HTML output, follow the mappings in `references/style-mapping.md` and write the output file to the same directory as the source with the appropriate extension.

---

## Step 7 — Report

After conversion, always report:

```
Conversion complete
  Source:    1090-OHH-POL-Applicant Screening Policy.docx
  Output:    Confluence ADF → published to OHH / Hiring
  Template:  Policy (auto-detected)
  Cleanup:   3 issues fixed, 0 flagged for review
  Nodes:     52 (8 headings, 31 paragraphs, 6 list items, 2 tables)
  URL:       https://oversite-health.atlassian.net/wiki/...
```

---

## Additional Resources

- **`references/cleanup-rules.md`** — full cleanup rules with decision tables and examples
- **`references/style-mapping.md`** — Word style / Google Docs HTML → ADF / Markdown / HTML mapping tables
- **`references/adf-reference.md`** — ADF node type reference for building and validating output
