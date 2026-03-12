---
description: Unzip an archive and publish all .docx files inside it to Confluence. Extracts to a temp directory, runs the same analysis and cleanup as publish-folder, shows an upload plan, and publishes after confirmation. Use --go to skip confirmation.
argument-hint: path/to/archive.zip [--go]
allowed-tools: Read, Write, Bash, Glob
---

# Confluence Publisher Zip Upload

Unzip an archive and publish all .docx files inside it to Confluence.

## Steps

1. Parse arguments:
   - Zip file path (required)
   - `--go` flag (optional)

2. If no zip path provided, ask for it. Verify the file exists and ends in `.zip`.

3. Validate the archive before extraction:

   ```bash
   MAX_MB=512
   ZIP_BYTES=$(stat -f%z "$ZIP_PATH")
   if [ "$ZIP_BYTES" -gt $((MAX_MB * 1024 * 1024)) ]; then
     echo "Archive is larger than ${MAX_MB}MB; inspect it before publishing."
     exit 1
   fi
   unzip -Z1 "$ZIP_PATH" | while IFS= read -r entry; do
     case "$entry" in
       /*|../*|*/../* )
         echo "Unsafe archive entry: $entry"
         exit 1
         ;;
     esac
   done
   ```

4. Extract to a temp directory:

   ```bash
   TMPDIR=$(mktemp -d)
   unzip -q "$ZIP_PATH" -d "$TMPDIR"
   ```

5. Discover all `.docx` files in the extracted directory:

   ```bash
   find "$TMPDIR" -name "*.docx" | sort
   ```

   Report: "Found X .docx files in archive."

6. Follow the same workflow as `/confluence-publisher:publish-folder` from Step 4 onward, using the extracted temp directory as the folder path.

7. After publishing completes (success or failure), clean up the temp directory:

   ```bash
   rm -rf "$TMPDIR"
   ```

8. Show final results table with URLs and totals.
