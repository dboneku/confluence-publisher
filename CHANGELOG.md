# Changelog

## Unreleased

### Added

- Added `clod.md` repository notes for maintainers and future agent context.
- Added regression tests for publish helper behavior and configuration handling under `tests/`.
- Started splitting `scripts/publish.py` into reusable helper modules under `scripts/publisherlib/`.

### Changed

- Cleaned up README, command markdown, and skill formatting so the public docs pass workspace diagnostics.
- Bounded Python dependency ranges in `scripts/requirements.txt`.
- Standardized `--go` documentation and behavior around publish confirmation.

### Fixed

- Made `doc-lint` pre-publish cleanup failures visible and added a safe fallback to built-in cleanup.
- Fixed parent resolution in single-file and bulk publish flows to use the documented space-key contract.
- Added schema versioning to `.confluence-config.json` handling.
- Hardened the archive upload command with pre-extraction validation guidance.
