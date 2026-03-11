---
description: Scan existing Confluence pages for headings with numbered prefixes (e.g. "1. Purpose") and strip the numbers, leaving plain heading text.
argument-hint: [SPACE_KEY] [--folder "Folder Name"] [--go]
allowed-tools: run_in_terminal
---

Scan pages in the active (or specified) space for headings that begin with a number prefix — for example: "1. Purpose", "2. Scope", "3. Policy Statements" — and strip the prefix entirely, leaving plain heading text.

## How it works

A numbered heading is one whose text begins with `N. ` (digit, period, space).  The fixer walks all heading nodes in each page's ADF body and removes any such prefix.  Non-numbered headings are left untouched.

A page is included in the fix plan only when at least one numbered heading is found.  Unchanged pages are never updated.

## Steps

1. **Resolve the target space**

   - If `SPACE_KEY` argument is provided, use it.
   - Otherwise use `ACTIVE_SPACE`.
   - If neither is set, run `--list-spaces` to show available spaces and ask the user.

2. **Resolve the target folder (optional)**

   - If `--folder "Name"` is provided, scope the scan to that folder's descendants.
   - Otherwise use `ACTIVE_FOLDER` if set.
   - If neither is set, scan the entire space.

3. **Run the fixer**

```bash
python3 /Users/dougbonebrake/Sites/confluence-publisher/scripts/publish.py \
    --fix-heading-numbers {SPACE_KEY} \
    [--folder "{FOLDER_NAME}"] \
    [--go]
```

Pass `--go` automatically if the user included `--go` in their command, or if they have already confirmed in conversation.

4. **Report results**

   Print the terminal output verbatim, then summarise how many pages were updated and whether any failures occurred.

## Flags

| Flag | Description |
|---|---|
| `--fix-heading-numbers SPACE_KEY` | Required — the space to scan |
| `--folder "Name"` | Scope scan to a specific folder and its descendants |
| `--go` | Skip interactive confirmation and apply all fixes immediately |

## Notes

- This command only modifies heading *number prefixes* — no other content is changed.
- If a heading does not begin with a digit it is left untouched.
- Newly published pages have number prefixes stripped automatically during the publish step; this command is for fixing pages that were already in Confluence.
