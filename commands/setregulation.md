---
description: Set the active regulation framework for this project (e.g. ISO 27001). Once set, publish.py will automatically match document titles against the regulation's required document catalog and insert the corresponding document ID into the Confluence page title. The selection is saved to .confluence-config.json and persists across Claude Code sessions.
argument-hint: [iso27001]
allowed-tools: Bash
---

Set the active regulation framework for this project.

## Steps

1. If no argument provided, show the available regulations:
   ```
   Available regulations:
     iso27001  —  ISO/IEC 27001:2022
   ```
   Ask: "Which regulation are you working under?"

2. Run:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --set-regulation "$REGULATION"
   ```

3. The script saves the selection to `.confluence-config.json` in the working directory:
   ```json
   {
     "regulation": "iso27001",
     "set_date": "YYYY-MM-DD"
   }
   ```

4. Confirm to the user:
   ```
   ✓ Active regulation: ISO/IEC 27001:2022

   Effect on publishing:
   • Page titles will be checked against the ISO 27001 document catalog.
   • If a document title closely matches a required document name, its
     document ID (e.g. "02-ISMS") will be inserted into the title:
       Before: OHH-POL-001 Information Security Policy
       After:  OHH-POL-001 02-ISMS Information Security Policy
   • The first heading in a document body will be stripped if it closely
     matches the Confluence page title (to avoid duplication).

   To view the full document catalog:
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --list-regulation-docs iso27001

   To clear: /confluence-publisher:clearregulation
   ```

5. Update session memory:
   - ACTIVE_REGULATION = "iso27001"
   - ACTIVE_REGULATION_NAME = "ISO/IEC 27001:2022"
