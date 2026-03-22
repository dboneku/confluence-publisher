---
description: Scan existing Confluence pages for numbered heading-like blocks (e.g. "1. Purpose") and normalize them by stripping the numbers and applying heading levels. Supports one space or all spaces.
argument-hint: [SPACE_KEY | --all-spaces] [--folder "Folder Name"] [--go]
allowed-tools: run_in_terminal
---

Scan pages in the active (or specified) space for numbered heading-like blocks — for example: "1. Purpose", "2. Scope", "3. Policy Statements" — and normalize them.

## How it works

A numbered heading-like block is a short heading or paragraph whose text begins with a numeric prefix such as `1. `, `2) `, or `3.1 `. The fixer:

- strips the numeric prefix
- converts short numbered paragraphs into headings
- defaults the heading level to H1
- uses a simple heuristic when it sees an adjacent `1` then `2` pair: the `1` becomes H1 and following numbered headings stay H2 until another adjacent `1` then `2` pair starts a new major section

A page is included in the fix plan only when at least one numbered heading is found.  Unchanged pages are never updated.

## Steps

1. **Resolve the target space**

   - If `SPACE_KEY` argument is provided, use it.
   - If `--all-spaces` is provided, scan every current global Confluence space and ignore `ACTIVE_SPACE`.
   - Otherwise use `ACTIVE_SPACE`.
   - If neither is set, run `--list-spaces` to show available spaces and ask the user.

2. **Resolve the target folder (optional)**

   - If `--folder "Name"` is provided, scope the scan to that folder's descendants.
   - Otherwise use `ACTIVE_FOLDER` if set.
   - If neither is set, scan the entire space.
   - Do not use `--folder` together with `--all-spaces`.

3. **Run the fixer**

```bash
python3 /Users/dougbonebrake/Sites/confluence-publisher/scripts/publish.py \
    --fix-heading-numbers {SPACE_KEY} \
   [--all-spaces] \
    [--folder "{FOLDER_NAME}"] \
    [--go]
```

Pass `--go` automatically if the user included `--go` in their command, or if they have already confirmed in conversation.

4. **Report results**

   Print the terminal output verbatim, then summarise how many pages were updated and whether any failures occurred.

## Flags

| Flag | Description |
|---|---|
| `--fix-heading-numbers SPACE_KEY` | Optional when `--all-spaces` is used; otherwise the space to scan |
| `--all-spaces` | Scan every current global space instead of a single space |
| `--folder "Name"` | Scope scan to a specific folder and its descendants |
| `--go` | Skip interactive confirmation and apply all fixes immediately |

## Notes

- This command only touches numbered heading-like blocks.
- If no useful level can be inferred, the block is converted to H1.
- Newly published pages have number prefixes stripped automatically during the publish step; this command is for fixing pages that were already in Confluence.
