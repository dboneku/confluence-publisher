---
description: Audit all pages in a Confluence space (or folder) for template compliance, then automatically patch non-compliant pages by inserting warning-panel placeholders for every missing required section. Naming convention violations are reported but require manual renaming. Use --go to skip confirmation.
argument-hint: <space-key> [--folder "Folder Name"] [--go]
allowed-tools: Bash
---

Audit then remediate non-compliant Confluence pages by inserting missing section placeholders.

## Steps

1. Parse arguments:
   - Space key (required, e.g. `OHH`)
   - `--folder "Folder Name"` (optional — limit to a named folder and its descendants)
   - `--go` (optional — skip the confirmation prompt before making changes)

2. If no space key provided, ask for it.

3. Run the remediation:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" \
     --remediate "$SPACE_KEY" \
     [--folder "$FOLDER_NAME"] \
     [--go]
   ```

4. The script will:
   - **Audit** — scan all pages (same as `/confluence-publisher:audit`) and build the compliance report
   - **Plan** — list every page that needs section placeholders added, with section names
   - **Confirm** — wait for `y` confirmation unless `--go` is set
   - **Patch** — for each non-compliant page, fetch its ADF, insert the missing sections (as H2 heading + warning panel with `[TO BE COMPLETED — Section Name]`), and PUT the updated page back via the REST API

5. Insertion logic:
   - Missing sections are inserted **before** the `Revision History` section if present, otherwise appended at the end
   - Sections are inserted in template order (e.g. for Policy: Purpose → Scope → Definitions → ... → Revision History)
   - Existing content is never removed or reordered — only new nodes are added

6. Progress output:
   ```
   Remediation plan — 8 page(s):
   ──────────────────────────────────────────────────────────────
     ACME-POL-003 Information Security Policy
       Add: Compliance and Exceptions, Revision History
     HR Onboarding Checklist
       Add: Completion

   Proceed? [y/N]

   ──────────────────────────────────────────────────────────────
     ✓  ACME-POL-003 Information Security Policy
     ✓  HR Onboarding Checklist
     ...

   Remediation complete: 8 updated, 0 failed

   Naming violations (manual rename required — 3 page(s)):
   ──────────────────────────────────────────────────────────────
     'HR Onboarding Checklist'  →  expected: ORG-CHK-001 Document Title
     ...
   ```

7. Naming convention violations are **never auto-fixed** — they require renaming the Confluence page. They are always listed at the end of the report for manual follow-up.

8. After completion, suggest running `/confluence-publisher:audit` again to verify the space is now compliant.
