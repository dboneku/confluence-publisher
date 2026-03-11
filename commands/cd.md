---
description: Navigate to a folder within the active Confluence space, similar to a filesystem "cd" command. Sets the active folder for this session — subsequent publish, audit, and remediate commands will target this folder by default. Use "cd .." to go up one level, "cd /" or "cd root" to return to the space root.
argument-hint: "Folder Name" | .. | / | root
allowed-tools: Bash
---

Set the active working folder within the current Confluence space.

## Steps

1. Ensure a space is selected:
   - If ACTIVE_SPACE_KEY is not set, run `/confluence-publisher:selectspace` first.

2. Parse the argument:
   - `"Folder Name"` — navigate into that folder
   - `..` — go up one level (to the parent of ACTIVE_FOLDER, or to root if already at top)
   - `/` or `root` — return to the space root (ACTIVE_FOLDER = null)

3. **For a named folder:**
   - If AVAILABLE_TREE is cached in session memory, search it for the folder title first.
   - Otherwise, verify the folder exists via the tree command output or a quick API check:
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" \
       --tree "$ACTIVE_SPACE_KEY" --folder "$FOLDER_NAME"
     ```
   - If the folder is not found, report the error and list the top-level pages/folders:
     ```
     ✗ Folder "Hirring" not found in OHH.
     Did you mean one of these?
       📁 Employee Management
       📁 Hiring
       📁 Onboarding
     ```

4. **For `..`:**
   - If ACTIVE_FOLDER is null (already at root), report: "Already at space root."
   - Otherwise set ACTIVE_FOLDER to the parent of the current folder. If the parent is unknown (first level under root), set to null.

5. **For `/` or `root`:**
   - Set ACTIVE_FOLDER = null.

6. Confirm the new location:
   ```
   ✓ Working location:  OHH / Employee Management / Hiring

   Commands that will now target this folder by default:
     /confluence-publisher:gettree
     /confluence-publisher:audit
     /confluence-publisher:remediate
     /confluence-publisher:publish-file  (pages will be created under this folder)
   ```
   Or, if at root:
   ```
   ✓ Working location:  OHH / (root)
   ```

7. Update session memory:
   - ACTIVE_FOLDER = folder name entered (null if at root)
   - ACTIVE_FOLDER_PATH = full breadcrumb string, e.g. "Employee Management / Hiring"

## Session State

ACTIVE_FOLDER persists for the duration of this conversation.
All commands that accept --folder will use ACTIVE_FOLDER if none is explicitly specified.
Switching spaces resets ACTIVE_FOLDER to null.
