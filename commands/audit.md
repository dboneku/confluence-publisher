---
description: Scan all pages in a Confluence space (or a specific folder) and audit each page for template compliance — missing required sections and naming convention violations. Read-only, nothing is modified.
argument-hint: <space-key> [--folder "Folder Name"]
allowed-tools: Bash
---

Audit Confluence pages for template compliance. Read-only — no pages are modified.

## Steps

1. Parse arguments:
   - Space key (required, e.g. `OHH`)
   - `--folder "Folder Name"` (optional — limit scan to a named folder/page and all its descendants)

2. If no space key provided, ask for it.

3. Run the audit:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" \
     --audit "$SPACE_KEY" \
     [--folder "$FOLDER_NAME"]
   ```

4. The script will:
   - Discover all pages in the space (or folder subtree) using CQL
   - Fetch each page's ADF body
   - Detect the template from content (Policy, Procedure, Workflow, Form, Checklist, Meeting Minutes, ISO 27001, General)
   - Check required sections against the template's section list
   - Check the page title against the template naming convention
   - Print a full compliance report

5. Report format:
   ```
   ══════════════════════════════════════════════════════════════
   Audit report — OHH
   ══════════════════════════════════════════════════════════════
     Total pages   : 47
     ✓  Compliant  : 31
     ✗  Issues     : 16
   ──────────────────────────────────────────────────────────────
   Non-compliant pages:

     ACME-POL-003 Information Security Policy
       Template : policy
       Missing  : Compliance and Exceptions, Revision History

     HR Onboarding Checklist
       Template : checklist
       Missing  : Completion
       Naming   : expected — ORG-CHK-001 Document Title

     ...
   ```

6. After the report, suggest:
   ```
   To auto-remediate missing sections: /confluence-publisher:remediate OHH [--folder "..."]
   Naming convention violations require manual page renames in Confluence.
   ```

7. Do not modify any pages.
