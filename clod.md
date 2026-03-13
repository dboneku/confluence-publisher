# confluence-publisher Repository Notes

## Purpose

`confluence-publisher` is a Claude-oriented wrapper around document ingestion and cleanup that publishes normalized content into Confluence Cloud using the REST API.

## Main Components

- `commands/` contains the user-facing Claude command contracts.
- `scripts/publish.py` is the main operational entry point for analysis, publishing, auditing, remediation, and configuration.
- `scripts/publisherlib/` now holds reusable helper modules extracted from `publish.py`.
- `skills/confluence-publisher/` documents Confluence-specific workflows.
- `skills/doc-converter/` documents ingestion, structure analysis, and conversion behavior.
- `tests/` contains regression coverage for publish helper behavior and configuration handling.

## Important Behaviors

- The script supports both read-only analysis and write paths to Confluence.
- It can optionally integrate with `doc-lint` when that plugin is installed.
- The script uses both Confluence v2 APIs and CQL search where folders or tree traversal require it.
- The public contract is spread across README examples, command markdown, and skill steps, so drift between those layers creates user-facing confusion quickly.

## Current Maintenance Focus

- Keep command docs aligned with implemented CLI behavior.
- Surface `doc-lint` integration failures instead of quietly continuing as if enhanced cleanup succeeded.
- Harden archive/config handling around publish workflows.
- Continue moving pure helper logic out of `publish.py` while keeping the CLI entry point stable.
- Keep the extracted `publisherlib` modules as the unit-test target and leave `publish.py` as orchestration glue.
- Maintain GitHub Actions coverage for both Python regression tests and markdown contract files.
- Keep ADF rendering and document-control helpers in `scripts/publisherlib/adf_tools.py`, and keep template/naming rules in `scripts/publisherlib/templates.py`.
