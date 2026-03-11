---
description: Analyze a document's structure and report formatting issues without publishing anything. Checks for consecutive headings, style misuse, list type problems, font inconsistencies, and auto-detects the best Confluence template.
argument-hint: path/to/file.docx
allowed-tools: Read, Bash
---

Run structural analysis on the specified document and report findings to the terminal. Do not publish anything.

## Steps

1. Get the file path from the user's argument. If not provided, ask for it.

2. Invoke the doc-converter skill to run the analysis phase (Steps 2–4 of that skill).

3. Run the analysis script:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --analyze "$FILE_PATH"
   ```

4. Report findings in this format:
   ```
   Analysis: path/to/file.docx
   ─────────────────────────────────────────────
   Template (auto-detected): Policy
   Structure: 38 headings, 14 paragraphs, 0 lists, 0 tables

   Issues (3):
     ⚠  Consecutive headings: "Contractors" is heading #3 in a row (lines 7–9)
     ⚠  Style misuse: 14 "Heading 1" paragraphs at ≤12pt — will reclassify as body text
     ℹ  No lists detected — possible Roman numeral or alpha lists embedded in paragraphs

   Cleanup actions that would be applied on publish:
     ✓  14 misused headings → reclassified as paragraphs
     ✓  Consecutive heading runs → bullet lists
     ✓  Multiline heading paragraphs → split at line breaks
   ─────────────────────────────────────────────
   To publish with these fixes applied: /confluence-publisher:publish-file path/to/file.docx
   ```

5. Do not modify the source file. Analysis is read-only.
