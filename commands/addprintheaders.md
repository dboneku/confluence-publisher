---
description: Add a document control header and 'Uncontrolled when printed' footer to existing Confluence pages that are missing them.
argument-hint: [SPACE_KEY] [--folder "Folder Name"] [--go]
allowed-tools: run_in_terminal
---

Scan pages in the active (or specified) space and add a document control header table and a print warning footer to any page that does not already have them.

## What is added to each page

**Document control header** (top of page, before all content):

| Document Title | [page title] |
|---|---|
| Document ID | [extracted from title prefix, e.g. OHH-POL-001 02-ISMS] |
| Version | 1.0 |
| Status | Current |
| Classification | Internal |
| Approved Date | [today's date at time of publish] |

---

**Print warning footer** (bottom of page, after all content):

> ⚠ UNCONTROLLED WHEN PRINTED — [Doc ID]  [Title]  v1.0.  
> The print date and page numbers are supplied by your browser or PDF viewer.  
> Verify this is the current approved version before use.

## How it works

- Pages that already have a document control header (identified by the "Document Title" table row) are skipped automatically.
- The document ID is parsed from the page title prefix - for example, `OHH-POL-001 02-ISMS` is extracted from `OHH-POL-001 02-ISMS Information Security Policy`.
- All new publishes automatically include document control blocks; this command is only needed for pages already in Confluence.
- The operation is idempotent — running it twice on the same pages is safe.

## Steps

1. **Resolve the target space**

   - Use `SPACE_KEY` argument if provided.
   - Otherwise use `ACTIVE_SPACE`.
   - If neither is set, run `--list-spaces` and ask the user.

2. **Resolve the target folder (optional)**

   - Use `--folder "Name"` if provided, or `ACTIVE_FOLDER` if set.
   - Otherwise scan the entire space.

3. **Run the command**

```bash
python3 /Users/dougbonebrake/Sites/confluence-publisher/scripts/publish.py \
    --add-print-headers {SPACE_KEY} \
    [--folder "{FOLDER_NAME}"] \
    [--go]
```

Pass `--go` automatically only if the user explicitly included it or has confirmed in conversation.

4. **Report results**

   Print the terminal output verbatim. Summarise how many pages were updated and note any failures.

## Flags

| Flag | Description |
|---|---|
| `--add-print-headers SPACE_KEY` | Required — the space to scan |
| `--folder "Name"` | Scope to a specific folder and its descendants |
| `--go` | Skip interactive confirmation and apply all changes immediately |

## Notes

- For print **page numbers**: Confluence's built-in PDF export and all browsers natively add page numbers in their print headers/footers.
- For **printed-on date**: browsers and Confluence PDF export always show the current date in the print dialog header. It is intentionally not hardcoded into the page content because it would go stale.
- To update an existing header (e.g. change Approved Date or Version): re-publish the page — the wrap function replaces any existing blocks before inserting fresh ones.
