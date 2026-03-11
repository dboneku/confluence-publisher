---
description: Show all available confluence-publisher slash commands with descriptions and usage examples.
argument-hint: (no arguments)
allowed-tools: (none)
---

Display the full command reference for the Confluence Publisher plugin.

## Output

Print the following exactly:

```
╔══════════════════════════════════════════════════════════════════════╗
║           Confluence Publisher — Command Reference                   ║
╚══════════════════════════════════════════════════════════════════════╝

NAVIGATION
──────────────────────────────────────────────────────────────────────
  /confluence-publisher:getspaces
    List all spaces in your Confluence instance.

  /confluence-publisher:selectspace [SPACE_KEY]
    Set the active space for this session. All commands will default
    to this space until you change it.
    Example: /confluence-publisher:selectspace OHH

  /confluence-publisher:gettree [SPACE_KEY] [--folder "Name"]
    Print the full page and folder tree for a space.
    Defaults to the active space if one is selected.
    Example: /confluence-publisher:gettree
    Example: /confluence-publisher:gettree OHH --folder "HR Policies"

  /confluence-publisher:cd "Folder Name" | .. | /
    Navigate into a folder within the active space (like a filesystem cd).
    Sets the active folder — subsequent commands will target it by default.
    Example: /confluence-publisher:cd "Employee Management"
    Example: /confluence-publisher:cd "Hiring"       (into a subfolder)
    Example: /confluence-publisher:cd ..             (up one level)
    Example: /confluence-publisher:cd /              (back to space root)

PUBLISHING
──────────────────────────────────────────────────────────────────────
  /confluence-publisher:setup
    Set up or update Confluence credentials (.env) and test the connection.

  /confluence-publisher:publish-file <file-or-url>
    Publish a single file (docx, pdf, md, txt, Google Doc URL) to Confluence.
    Example: /confluence-publisher:publish-file report.docx

  /confluence-publisher:publish-folder <folder-path>
    Publish all documents in a local folder to Confluence.
    Example: /confluence-publisher:publish-folder ./docs

  /confluence-publisher:publish-zip <zip-path>
    Publish all documents from a zip archive to Confluence.
    Example: /confluence-publisher:publish-zip export.zip

COMPLIANCE & CLEANUP
──────────────────────────────────────────────────────────────────────
  /confluence-publisher:setregulation [REGULATION]
    Set the active regulation framework (e.g. iso27001). Saves to
    .confluence-config.json and persists across sessions.
    When set, document IDs are auto-injected into page titles when
    the title closely matches a required regulation document name.
    Example: /confluence-publisher:setregulation iso27001

  /confluence-publisher:clearregulation
    Remove the active regulation. Document IDs will no longer be
    injected into titles.

  /confluence-publisher:setpolicy <source> [--section "Appendix A"]
    Load formatting and style rules from a local file or Confluence page
    (or a named section within one) and save them as the project style policy.
    Once saved, every publish and doc-lint run will enforce these rules.
    Supported sources: .docx, .md, .txt, .pdf, Confluence page URL or page ID.
    Example: /confluence-publisher:setpolicy ./standards/doc-standards.docx
    Example: /confluence-publisher:setpolicy https://...atlassian.net/.../pages/123456/Title --section "Appendix A"
    Example: /confluence-publisher:setpolicy 123456 --section "Formatting Rules"

  /confluence-publisher:audit [SPACE_KEY] [--folder "Name"]
    Scan pages in a space (or folder) for template compliance.
    Read-only — nothing is modified.
    Example: /confluence-publisher:audit
    Example: /confluence-publisher:audit OHH --folder "HR Policies"

  /confluence-publisher:remediate [SPACE_KEY] [--folder "Name"] [--go]
    Audit then auto-patch non-compliant pages with placeholder sections.
    Shows a plan and asks for confirmation unless --go is passed.
    Example: /confluence-publisher:remediate
    Example: /confluence-publisher:remediate OHH --go

  /confluence-publisher:fixheadingnumbers [SPACE_KEY] [--folder "Name"] [--go]
    Scan existing pages for numbered headings that restart mid-document
    (e.g. "1. Purpose" … "2. Scope" … "1. Policy Statements") and renumber
    them so each level is sequential within its parent heading.
    Shows a plan and asks for confirmation unless --go is passed.
    Example: /confluence-publisher:fixheadingnumbers
    Example: /confluence-publisher:fixheadingnumbers OHH --folder "Policies" --go

  /confluence-publisher:addprintheaders [SPACE_KEY] [--folder "Name"] [--go]
    Add a document control header table (Title, Doc ID, Version, Status,
    Classification, Approved Date) and an "UNCONTROLLED WHEN PRINTED" footer
    to pages that are missing them. All new publishes include these blocks
    automatically; this command patches pages already in Confluence.
    Print date and page numbers are supplied by the browser / PDF export.
    Example: /confluence-publisher:addprintheaders
    Example: /confluence-publisher:addprintheaders OHH --folder "Policies" --go

  /confluence-publisher:analyze <file>
    Analyze a local file's structure, detected template, and compliance
    before publishing. Does not connect to Confluence.
    Example: /confluence-publisher:analyze policy-draft.docx

HELP
──────────────────────────────────────────────────────────────────────
  /confluence-publisher:help
    Show this command reference.

SESSION STATE
──────────────────────────────────────────────────────────────────────
  ACTIVE_SPACE    Set by /selectspace — used as default for all commands
  ACTIVE_FOLDER   Set by /cd — used as default --folder for all commands
  ACTIVE_REGULATION  Set by /setregulation — applied to all publish operations
  
  ACTIVE_SPACE and ACTIVE_FOLDER reset when you start a new conversation.
  ACTIVE_REGULATION persists via .confluence-config.json across sessions.
```

After printing, ask: "What would you like to do?"
