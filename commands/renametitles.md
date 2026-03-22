---
description: Scan all pages in a Confluence space (or folder) and rename titles to match the standard convention [DOC_TYPE]-[ISO_CODE]-[SPACE]-[Document Name]. Shows a preview before changing anything; applies fixes only after confirmation.
argument-hint: <space-key> [--folder "Folder Name"] [--go]
allowed-tools: Bash
---

Audit and rename Confluence page titles to match the standard naming convention.

Title convention: `[DOC_TYPE]-[ISO_CODE]-[SPACE]-[Document Name]`

- **DOC_TYPE**: `POL`, `PRO`, `REC`, `GUI`, `STD`
- **ISO_CODE**: primary Annex A control or clause (e.g. `A.5.1`) — include only if known
- **SPACE**: Confluence space key
- **Document Name**: Title-cased, spaces preserved (never underscores)

## Steps

1. Parse arguments:
   - Space key (required, e.g. `OHH`)
   - `--folder "Folder Name"` (optional — limit scan to a named folder and descendants)
   - `--go` (optional — skip the confirmation prompt and apply all auto-fixes immediately)

2. If no space key provided, ask for it.

3. Fetch all pages in the space or folder (paginate using cursor if > 250 pages).

4. For each page title, classify into one of:

   | Status | Condition |
   |---|---|
   | Compliant | Already matches `[DOC_TYPE]-[ISO_CODE]-[SPACE]-[Name]` |
   | Auto-fixable | Missing DOC_TYPE prefix but type is clear from title keywords |
   | Auto-fixable | Has underscores in document name portion — replace with spaces |
   | Auto-fixable | Has old-format number prefix (e.g. `OverSite 09-IS ...`) — reformat |
   | Needs input | DOC_TYPE cannot be confidently inferred from title alone |

   **DOC_TYPE inference rules** (first match wins):
   - Contains "policy", "AUP", "acceptable use" → `POL`
   - Contains "procedure", "process", "how to" → `PRO`
   - Contains "record", "log", "register", "inventory", "tracker" → `REC`
   - Contains "guideline", "guide", "best practice" → `GUI`
   - Contains "standard", "specification", "requirement" → `STD`
   - Cannot determine → queue for user input

5. Print a preview table before making any changes:

   ```
   ══════════════════════════════════════════════════════════════
   Title Audit — OHH — 47 pages scanned
   ══════════════════════════════════════════════════════════════
     ✓  Compliant         : 31
     ~  Auto-fix proposed : 12
     ?  Needs your input  :  4
   ──────────────────────────────────────────────────────────────
   AUTO-FIX PROPOSED:

     [1]  "data handling rules v2 final FINAL"
          → POL-A.5.1-OHH-Data Handling Policy

     [2]  "Incident_Response_Procedure"
          → PRO-A.5.24-OHH-Incident Response Procedure

     ...

   NEEDS YOUR INPUT — specify type (POL/PRO/REC/GUI/STD):

     [13] "Supplier Onboarding Checklist"
     [14] "Q3 Security Review Notes"
   ──────────────────────────────────────────────────────────────
   Proceed with auto-fixes? (Y/N)
   For items needing input: e.g. "13=PRO, 14=REC"
   ```

6. Wait for user response unless `--go` was passed (in which case apply all auto-fixes immediately; skip items needing input unless already specified).

7. Apply approved fixes — for each page, fetch current version, update title only, increment version number, preserve body content unchanged.

8. Print results:

   ```
   ══════════════════════════════════════════════════════════════
   Rename complete — OHH
   ══════════════════════════════════════════════════════════════
     Updated  : 14
     Skipped  : 2  (user declined or type still ambiguous)
     Failed   : 1  (see below)
     Unchanged: 31

   Failed:
     "HR Handbook" — 409 Conflict: page locked by another user
   ```

9. After completion, suggest:
   ```
   To check remaining content compliance: /confluence-publisher:audit OHH
   To fix numbered section headings:      /confluence-publisher:fixheadingnumbers OHH
   ```
