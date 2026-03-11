---
description: Convert and publish all .docx files in a local folder to Confluence. Analyzes each file, applies cleanup, shows a full upload plan for all files, and publishes after confirmation. Use --go to skip confirmation.
argument-hint: path/to/folder [--go]
allowed-tools: Read, Write, Bash, Glob
---

Convert and publish all .docx files in a folder to Confluence. Follow the confluence-publisher skill workflow in bulk mode.

## Steps

1. Parse arguments:
   - Folder path (required)
   - `--go` flag (optional — skips upload plan confirmation)

2. If no folder provided, ask for it.

3. Discover all `.docx` files in the folder:
   ```bash
   find "$FOLDER_PATH" -name "*.docx" | sort
   ```

4. Follow **confluence-publisher skill** Steps 0–3 (credentials, spaces, parent selection).

5. For each file, run analysis via the doc-converter skill and collect:
   - Proposed title (normalized from filename)
   - Auto-detected template
   - Issues count

6. Show the full upload plan as a table (all files):
   ```
   Upload plan — 5 files
   ┌──────────────────────────────────────┬──────────────┬───────┬─────────────┐
   │ File                                 │ Template     │Issues │ Title       │
   ├──────────────────────────────────────┼──────────────┼───────┼─────────────┤
   │ 1090-OHH-POL-Screening Policy.docx  │ Policy       │ 23⚠  │ 1090-OHH-.. │
   │ 1036-OHH-FRM-Applicant Consent.docx │ Form         │  3⚠  │ 1036-OHH-.. │
   └──────────────────────────────────────┴──────────────┴───────┴─────────────┘
   Space: OHH | Parent: Hiring
   ```
   Wait for confirmation unless `--go` is set.

7. Publish each file in order, applying cleanup rules. Show live progress:
   ```
   [1/5] Publishing: 1090-OHH-POL-Applicant Screening Policy...  OK
   [2/5] Publishing: 1036-OHH-FRM-Applicant Consent...           OK
   ```

8. Show final results table with URLs and totals.
