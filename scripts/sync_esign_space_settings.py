#!/usr/bin/env python3
"""
Synchronize eSign space settings across Confluence spaces.

The public eSign documentation describes space-level settings and webhook event
payloads, but it does not describe a supported REST API for bulk administration.
This script therefore uses two mechanisms:

1. Confluence REST API to enumerate spaces.
2. Playwright browser automation to open each space's eSign settings page and
   apply the same document-type policy.

The automation is intentionally conservative:
- `--dry-run` is the default.
- A logged-in Playwright storage state is required for UI access.
- A settings URL template is required because the exact app route can vary by
  installation.

Example:
    python scripts/sync_esign_space_settings.py \
      --storage-state ~/.config/confluence/storage-state.json \
      --settings-url-template 'https://oversite-health.atlassian.net/wiki/spaces/{spaceKey}/settings/apps/{appPath}' \
      --app-path 'com.digitalrose.edoc__space-settings' \
      --apply
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False


load_dotenv(Path(os.getcwd()) / ".env")


ATLASSIAN_URL = os.environ.get("ATLASSIAN_URL", "").rstrip("/")
ATLASSIAN_EMAIL = os.environ.get("ATLASSIAN_EMAIL", "")
ATLASSIAN_TOKEN = os.environ.get("ATLASSIAN_API_TOKEN", "")

DEFAULT_ADMINS = [
    "nick@clinicaloversite.com",
    "doug@clinicaloversite.com",
    "janet@clinicaloversite.com",
]


@dataclass(frozen=True)
class DocumentTypePolicy:
    code: str
    name: str
    review_months: int = 12
    approval_months: int = 12
    training_months: int = 12


DEFAULT_DOCUMENT_TYPES = [
    DocumentTypePolicy(code="POL", name="Policy"),
    DocumentTypePolicy(code="PRO", name="Procedure / Process"),
    DocumentTypePolicy(code="FRM", name="Form"),
    DocumentTypePolicy(code="REC", name="Record"),
]


FIELD_PATTERNS = {
    "document_admins": [r"document admins?", r"admins?"],
    "prefix": [r"document id prefix", r"id prefix", r"prefix"],
    "doc_type_name": [r"document type", r"type name", r"name"],
    "review_months": [r"review.*months", r"review cadence", r"review.*interval"],
    "approval_months": [r"approval.*months", r"approve.*interval", r"approval cadence"],
    "training_months": [r"training.*months", r"training cadence", r"training.*interval"],
}


def build_headers(email: str, token: str) -> dict[str, str]:
    auth = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def list_spaces(base_url: str, headers: dict[str, str]) -> list[dict]:
    if requests is None:
        raise SystemExit(
            "The requests package is required for this script. Install dependencies with\n"
            "  pip install -r scripts/requirements.txt"
        )

    url = f"{base_url}/wiki/api/v2/spaces"
    params: dict[str, str | int] = {"limit": 250}
    results: list[dict] = []

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        results.extend(data.get("results", []))
        next_link = data.get("_links", {}).get("next")
        url = urllib.parse.urljoin(base_url, next_link) if next_link else ""
        params = {}

    return results


def filter_spaces(
    spaces: list[dict],
    include_keys: set[str] | None = None,
    exclude_keys: set[str] | None = None,
) -> list[dict]:
    include_keys = include_keys or set()
    exclude_keys = exclude_keys or set()
    filtered: list[dict] = []

    for space in spaces:
        key = str(space.get("key", "")).strip()
        status = str(space.get("status", "current")).lower()
        space_type = str(space.get("type", "global")).lower()
        if not key or key.startswith("~"):
            continue
        if status != "current":
            continue
        if space_type != "global":
            continue
        if include_keys and key not in include_keys:
            continue
        if key in exclude_keys:
            continue
        filtered.append(space)

    return sorted(filtered, key=lambda item: item.get("key", ""))


def build_settings_url(template: str, base_url: str, space_key: str, app_path: str) -> str:
    return template.format(
        baseUrl=base_url.rstrip("/"),
        spaceKey=space_key,
        appPath=app_path,
    )


def render_plan(spaces: list[dict], document_types: list[DocumentTypePolicy], admins: list[str]) -> str:
    lines = [
        f"Spaces: {len(spaces)}",
        "Document types:",
    ]
    for policy in document_types:
        lines.append(
            f"  - {policy.code}: {policy.name} | review={policy.review_months}mo | "
            f"approval={policy.approval_months}mo | training={policy.training_months}mo"
        )
    lines.append("Document admins:")
    for admin in admins:
        lines.append(f"  - {admin}")
    lines.append("Space keys:")
    for space in spaces:
        lines.append(f"  - {space.get('key')} :: {space.get('name', '')}")
    return "\n".join(lines)


def _import_playwright():
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required for this script. Install dependencies with\n"
            "  pip install -r scripts/requirements.txt\n"
            "and then install a browser with\n"
            "  playwright install chromium"
        ) from exc
    return sync_playwright, PlaywrightTimeoutError


def _locator_by_patterns(scope, patterns: list[str]):
    for pattern in patterns:
        locator = scope.get_by_label(re.compile(pattern, re.I))
        if locator.count():
            return locator.first
    for pattern in patterns:
        locator = scope.get_by_placeholder(re.compile(pattern, re.I))
        if locator.count():
            return locator.first
    return None


def _clear_and_type(locator, value: str) -> None:
    locator.click()
    locator.fill("")
    locator.fill(value)


def _set_chip_field(scope, patterns: list[str], values: list[str]) -> None:
    locator = _locator_by_patterns(scope, patterns)
    if locator is None:
        raise RuntimeError(f"Could not find a field matching: {patterns}")
    locator.click()
    locator.press("Meta+A")
    locator.press("Backspace")
    for value in values:
        locator.fill(value)
        locator.press("Enter")


def _set_text_field(scope, patterns: list[str], value: str) -> None:
    locator = _locator_by_patterns(scope, patterns)
    if locator is None:
        raise RuntimeError(f"Could not find a field matching: {patterns}")
    _clear_and_type(locator, value)


def _open_doc_type_editor(page, policy: DocumentTypePolicy) -> None:
    row = page.get_by_text(re.compile(rf"\b{re.escape(policy.code)}\b", re.I))
    if row.count():
        row.first.click()
        return

    add_button = page.get_by_role("button", name=re.compile(r"add.*document type", re.I))
    if not add_button.count():
        add_button = page.get_by_role("button", name=re.compile(r"add", re.I))
    if not add_button.count():
        raise RuntimeError("Could not find the 'Add document type' button")
    add_button.first.click()


def _save_dialog(page) -> None:
    save_button = page.get_by_role("button", name=re.compile(r"save|update", re.I))
    if not save_button.count():
        raise RuntimeError("Could not find a Save/Update button on the eSign settings page")
    save_button.first.click()


def apply_space_settings(
    page,
    space_key: str,
    document_types: list[DocumentTypePolicy],
    admins: list[str],
    dry_run: bool,
) -> None:
    page.wait_for_load_state("networkidle")
    page.get_by_text(re.compile(r"document types", re.I)).first.wait_for(timeout=15000)

    if dry_run:
        return

    _set_chip_field(page, FIELD_PATTERNS["document_admins"], admins)

    for policy in document_types:
        _open_doc_type_editor(page, policy)
        _set_text_field(page, FIELD_PATTERNS["prefix"], policy.code)
        _set_text_field(page, FIELD_PATTERNS["doc_type_name"], policy.name)
        _set_text_field(page, FIELD_PATTERNS["review_months"], str(policy.review_months))
        _set_text_field(page, FIELD_PATTERNS["approval_months"], str(policy.approval_months))
        _set_text_field(page, FIELD_PATTERNS["training_months"], str(policy.training_months))
        _save_dialog(page)
        page.wait_for_load_state("networkidle")

    _save_dialog(page)
    page.wait_for_load_state("networkidle")
    print(f"Applied eSign policy to {space_key}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync eSign settings across Confluence spaces")
    parser.add_argument(
        "--storage-state",
        required=True,
        help="Path to a Playwright storage state JSON file for a logged-in Confluence session",
    )
    parser.add_argument(
        "--settings-url-template",
        required=True,
        help=(
            "URL template for the eSign space settings page. "
            "Available placeholders: {baseUrl}, {spaceKey}, {appPath}"
        ),
    )
    parser.add_argument(
        "--app-path",
        default=os.environ.get("ESIGN_SPACE_SETTINGS_APP_PATH", ""),
        help="App route segment used by your eSign installation",
    )
    parser.add_argument(
        "--space-key",
        action="append",
        dest="space_keys",
        default=[],
        help="Limit the run to one or more specific Confluence space keys",
    )
    parser.add_argument(
        "--exclude-space-key",
        action="append",
        dest="excluded_space_keys",
        default=[],
        help="Exclude one or more Confluence space keys",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually update spaces. Without this flag the script prints the plan only.",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run the browser headless or visible",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    missing = [
        name
        for name, value in [
            ("ATLASSIAN_URL", ATLASSIAN_URL),
            ("ATLASSIAN_EMAIL", ATLASSIAN_EMAIL),
            ("ATLASSIAN_API_TOKEN", ATLASSIAN_TOKEN),
        ]
        if not value
    ]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

    headers = build_headers(ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)
    all_spaces = list_spaces(ATLASSIAN_URL, headers)
    spaces = filter_spaces(
        all_spaces,
        include_keys=set(args.space_keys),
        exclude_keys=set(args.excluded_space_keys),
    )
    if not spaces:
        raise SystemExit("No matching Confluence spaces found")

    document_types = DEFAULT_DOCUMENT_TYPES
    admins = DEFAULT_ADMINS

    print(render_plan(spaces, document_types, admins))
    if not args.apply:
        print("\nDry run complete. Re-run with --apply to update space settings.")
        return 0

    storage_state = Path(args.storage_state)
    if not storage_state.exists():
        raise SystemExit(f"Playwright storage state file not found: {storage_state}")

    sync_playwright, PlaywrightTimeoutError = _import_playwright()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=args.headless)
        context = browser.new_context(storage_state=str(storage_state))
        try:
            for space in spaces:
                space_key = str(space["key"])
                url = build_settings_url(
                    args.settings_url_template,
                    ATLASSIAN_URL,
                    space_key,
                    args.app_path,
                )
                print(f"Opening {space_key}: {url}")
                page = context.new_page()
                try:
                    page.goto(url, wait_until="networkidle")
                    apply_space_settings(
                        page=page,
                        space_key=space_key,
                        document_types=document_types,
                        admins=admins,
                        dry_run=False,
                    )
                except PlaywrightTimeoutError as exc:
                    raise RuntimeError(
                        f"Timed out while opening eSign settings for {space_key}. "
                        "Confirm the URL template and that the saved login session still works."
                    ) from exc
                finally:
                    page.close()
        finally:
            context.close()
            browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())