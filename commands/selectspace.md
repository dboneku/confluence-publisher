---
description: Select a Confluence space to work in for this session. All subsequent commands (publish, audit, remediate, gettree, cd) will default to this space until changed. Optionally accepts the space key directly as an argument.
argument-hint: [SPACE_KEY]
allowed-tools: Bash
---

Select an active Confluence space for this session.

## Steps

1. If a space key argument was provided (e.g. `/confluence-publisher:selectspace OHH`):
   - Skip to step 4.

2. If AVAILABLE_SPACES is not yet loaded in session memory, fetch them first:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --list-spaces
   ```

3. Display the numbered list and ask the user to enter a number or space key:
   ```
   Select a space:

     1.  OHH    — Oversite Health - HR
     2.  OHAL   — Oversite Health - Legal
     3.  OHO    — Oversite Health - Operations
     ...

   Enter number or space key:
   ```

4. Confirm the selection:
   ```
   ✓ Active space set to: OHH — Oversite Health - HR

   Current working location: OHH / (root)

   Commands that will now use this space by default:
     /confluence-publisher:gettree
     /confluence-publisher:cd
     /confluence-publisher:audit
     /confluence-publisher:remediate
     /confluence-publisher:publish-file
   ```

5. Store in session memory:
   - ACTIVE_SPACE_KEY = selected space key (e.g. "OHH")
   - ACTIVE_SPACE_NAME = selected space name (e.g. "Oversite Health - HR")
   - ACTIVE_FOLDER = null  (reset folder whenever space changes)

6. Suggest a next step:
   ```
   To browse the space tree: /confluence-publisher:gettree
   To navigate to a folder:  /confluence-publisher:cd "Folder Name"
   ```

## Session State

ACTIVE_SPACE_KEY and ACTIVE_SPACE_NAME persist for the duration of this conversation.
All commands that accept a space key will use ACTIVE_SPACE_KEY if none is specified.
Switching spaces with this command resets ACTIVE_FOLDER to null.
