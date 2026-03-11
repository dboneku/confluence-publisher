---
description: List all Confluence spaces available in the connected instance, including their space keys, names, and types (global, personal, knowledge_base, collaboration).
argument-hint: (no arguments)
allowed-tools: Bash
---

List all Confluence spaces.

## Steps

1. Run:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --list-spaces
   ```

2. The script prints all spaces in this format:
   ```
   Spaces (9 total):

     OHH          — Oversite Health - HR                      [global]
     OHAL         — Oversite Health - Legal                   [global]
     ~jsmith      — John Smith                                [personal]
     ...
   ```

3. After displaying the list, suggest:
   ```
   To select a space to work in: /confluence-publisher:selectspace
   To view the page tree:        /confluence-publisher:gettree <SPACE_KEY>
   ```

4. Store the space list in session memory as AVAILABLE_SPACES for use by other commands this session.
