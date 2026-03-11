---
description: Display the full hierarchical page and folder tree for a Confluence space (or a specific folder subtree). If a space has been selected with /selectspace, uses that space by default.
argument-hint: [SPACE_KEY] [--folder "Folder Name"]
allowed-tools: Bash
---

Display the full page and folder tree for a Confluence space.

## Steps

1. Determine the space key:
   - If provided as an argument, use it.
   - Else if ACTIVE_SPACE_KEY is set in session memory, use it.
   - Else run `--list-spaces`, display the list, and ask the user to pick one.

2. Determine the folder scope:
   - If `--folder "Name"` is provided as an argument, scope to that subtree.
   - Else if ACTIVE_FOLDER is set in session memory, ask:
     ```
     Active folder is set to: "Employee Management"
     Show tree for that folder only, or the full space?
       1. Folder subtree (Employee Management)
       2. Full space (OHH)
     ```
   - Else show the full space tree.

3. Run:
   ```bash
   # Full space
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --tree "$SPACE_KEY"

   # Folder subtree
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --tree "$SPACE_KEY" --folder "$FOLDER_NAME"
   ```

4. The script outputs a tree like:
   ```
   Space OHH  —  47 page(s), 3 folder(s)

   📁 Employee Management
     📄 Overview
     📁 Hiring
       📄 Job Posting Template
       📄 Interview Process
     📁 Onboarding
       📄 New Hire Checklist
   📄 Company Policies
     📄 PTO Policy
     📄 Remote Work Policy
   ```

5. After displaying the tree, suggest:
   ```
   To navigate into a folder: /confluence-publisher:cd "Folder Name"
   To audit this space:        /confluence-publisher:audit
   ```

6. Update session memory:
   - ACTIVE_SPACE_KEY = space key used (if not already set)
   - ACTIVE_SPACE_NAME = space name (if resolvable)
