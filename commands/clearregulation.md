---
description: Remove the active regulation framework from this project. After clearing, document IDs will not be injected into page titles, and titles will not be matched against any regulation's document catalog.
argument-hint: (no arguments)
allowed-tools: Bash
---

Clear the active regulation framework for this project.

## Steps

1. Run:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --clear-regulation
   ```

2. Confirm to the user:
   ```
   ✓ Regulation cleared. No active regulation is set.

   Document IDs will no longer be injected into page titles.
   To set a new regulation: /confluence-publisher:setregulation
   ```

3. Update session memory:
   - ACTIVE_REGULATION = null
   - ACTIVE_REGULATION_NAME = null
