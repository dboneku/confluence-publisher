---
description: Load formatting and style rules from a local file or Confluence page (or a named section within one) and save them as the project style policy. Every subsequent publish and lint run will enforce these rules.
argument-hint: <source-file-or-url> [--section "Appendix A"]
allowed-tools: run_in_terminal
---

Load formatting rules from a source document and save them as `.style-policy.md` in the project directory. Once saved, every document published through confluence-publisher and every `.docx` linted through doc-lint will be checked against these rules automatically.

## Sources supported

| Source type | Example |
|---|---|
| Local file (`.docx`, `.md`, `.txt`, `.pdf`) | `./standards/doc-standards.docx` |
| Local file with section extraction | `./policies/OHH-POL-001.docx` + `--section "Appendix A"` |
| Confluence page URL | `https://oversite-health.atlassian.net/wiki/spaces/OHH/pages/123456/Document+Standards` |
| Confluence page URL with section | same URL + `--section "Formatting Requirements"` |
| Confluence page ID | `123456` |

## Steps

1. **Resolve the source**

   - If the argument is a local path, use it directly.
   - If the argument is a Confluence URL, extract the page ID and use `--set-policy` with it.
   - If `--section` is provided, only that section of the source is saved.

2. **Run the command**

```bash
python3 /Users/dougbonebrake/Sites/confluence-publisher/scripts/publish.py \
    --set-policy "{SOURCE}" \
    [--policy-section "{SECTION}"]
```

3. **Preview and confirm**

   The CLI will:
   - Print the first 20 lines of the extracted policy content
   - Show any required section names it detected automatically
   - Ask for confirmation before saving

4. **Confirm the result**

   If the user confirms, the CLI saves:
   - `.style-policy.md` in the project directory (full policy text with YAML frontmatter)
   - `.confluence-config.json` updated with `style_policy` metadata (source, section, date)

5. **Report to user**

   Tell the user:
   - The policy is now active
   - Required sections detected (if any)
   - Any document that is missing those sections will get a `⚠ Style policy:` warning at publish time
   - doc-lint will report `[W015]` for any `.docx` missing those sections

## How enforcement works

**At publish time (confluence-publisher):**
- After ADF conversion, `check_adf_against_style_policy()` compares document headings against required sections extracted from the policy
- Any missing required section prints: `⚠  Style policy: missing required section "Purpose"`
- Publishing is not blocked — this is a warning, not an error

**At lint time (doc-lint):**
- `[W015]` is a new warning code that checks docx files against `.style-policy.md` in cwd
- Works alongside all existing W001–W014 rules

**Claude Code enforcement:**
- The CLAUDE.md in this project references `.style-policy.md`
- Claude reads the policy on startup and applies it as contextual guidance when reviewing or building documents — this covers semantic/stylistic rules that can't be machine-checked (e.g., "use active voice", "avoid jargon")

## Notes

- Run `/setpolicy` again with a new source to replace the current policy
- To disable: delete `.style-policy.md` from the project directory
- The section extraction uses heading-level matching, so partial names work: `"Appendix A"` matches `"# Appendix A — Document Standards"`
- If no structured required-section list is found in the policy, the text is still saved and Claude enforces it contextually
