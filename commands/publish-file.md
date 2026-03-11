---
description: Convert and publish a single .docx file or Google Doc URL to Confluence. Runs structural analysis, applies formatting cleanup, auto-detects the template, shows an upload plan, and publishes after confirmation. Use --go to skip confirmation.
argument-hint: path/to/file.docx [--go]
allowed-tools: Read, Write, Bash
---

Convert and publish a single document to Confluence. Follow the confluence-publisher skill workflow exactly.

## Steps

1. Parse arguments:
   - File path or Google Doc URL (required)
   - `--go` flag (optional — skips upload plan confirmation)

2. If no file provided, ask for it.

3. Follow the **confluence-publisher skill** (all steps):
   - Step 0: Check doc-converter availability
   - Step 1: Validate credentials
   - Step 2: Discover spaces + build SESSION_TREE (skip if already done this session)
   - Step 3: Ask which space and parent page/folder to publish under
   - Step 4: Show upload plan with compliance warnings — wait for confirmation unless `--go` is set
   - Step 5: Collision detection
   - Step 6: Convert via doc-converter skill (including compliance checks), then publish
   - Step 7: Report result with URL

4. Run the publish script:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" \
     --file "$FILE_PATH" \
     --space "$SPACE_KEY" \
     --parent "$PARENT_TITLE" \
     --template "$TEMPLATE"
   ```

5. Print the published page URL on success.
