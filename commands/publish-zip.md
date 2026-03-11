---
description: Unzip an archive and publish all .docx files inside it to Confluence. Extracts to a temp directory, runs the same analysis and cleanup as publish-folder, shows an upload plan, and publishes after confirmation. Use --go to skip confirmation.
argument-hint: path/to/archive.zip [--go]
allowed-tools: Read, Write, Bash, Glob
---

Unzip an archive and publish all .docx files inside it to Confluence.

## Steps

1. Parse arguments:
   - Zip file path (required)
   - `--go` flag (optional)

2. If no zip path provided, ask for it. Verify the file exists and ends in `.zip`.

3. Extract to a temp directory:
   ```bash
   TMPDIR=$(mktemp -d)
   unzip -q "$ZIP_PATH" -d "$TMPDIR"
   ```

4. Discover all `.docx` files in the extracted directory:
   ```bash
   find "$TMPDIR" -name "*.docx" | sort
   ```
   Report: "Found X .docx files in archive."

5. Follow the same workflow as `/confluence-publisher:publish-folder` from Step 4 onward, using the extracted temp directory as the folder path.

6. After publishing completes (success or failure), clean up the temp directory:
   ```bash
   rm -rf "$TMPDIR"
   ```

7. Show final results table with URLs and totals.
