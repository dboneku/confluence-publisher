import json
import os
import re
import sys
from pathlib import Path

REGULATION_CONFIG_FILE = ".confluence-config.json"
CONFIG_SCHEMA_VERSION = 1
STYLE_POLICY_FILE = ".style-policy.md"


def warn(message: str):
    print(f"WARNING: {message}", file=sys.stderr)


def normalize_title(stem: str) -> str:
    """Collapse stray spaces around hyphens: 'OHH- POL-Foo' -> 'OHH-POL-Foo'."""
    return re.sub(r"\s*-\s*", "-", stem).strip()


def load_regulation_config() -> dict:
    """Load regulation config from .confluence-config.json in cwd."""
    cfg_path = Path(os.getcwd()) / REGULATION_CONFIG_FILE
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(cfg, dict):
                cfg.setdefault("schema_version", CONFIG_SCHEMA_VERSION)
                return cfg
        except Exception:
            warn(f"Could not parse {REGULATION_CONFIG_FILE}; using defaults")
    return {"schema_version": CONFIG_SCHEMA_VERSION}


def save_regulation_config(cfg: dict):
    """Write regulation config to .confluence-config.json in cwd."""
    cfg_path = Path(os.getcwd()) / REGULATION_CONFIG_FILE
    payload = dict(cfg)
    payload["schema_version"] = CONFIG_SCHEMA_VERSION
    cfg_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_style_policy() -> tuple[str | None, dict]:
    """Return (policy_text, metadata) from .style-policy.md in cwd, or (None, {})."""
    path = Path(os.getcwd()) / STYLE_POLICY_FILE
    if not path.exists():
        return None, {}
    raw = path.read_text(encoding="utf-8")
    meta: dict = {}
    body = raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            for line in raw[3:end].splitlines():
                match = re.match(r"^\s*(\w+)\s*:\s*(.+)", line)
                if match:
                    meta[match.group(1)] = match.group(2).strip().strip('"\'')
            body = raw[end + 4 :].lstrip("\n")
    return body, meta


def save_style_policy(policy_text: str, source: str, section: str | None = None):
    """Write .style-policy.md with YAML frontmatter and record metadata in .confluence-config.json."""
    from datetime import date as current_date

    frontmatter_lines = [f'source: "{source}"', f'set_date: "{current_date.today().isoformat()}"']
    if section:
        frontmatter_lines.append(f'section: "{section}"')
    content = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + policy_text
    path = Path(os.getcwd()) / STYLE_POLICY_FILE
    path.write_text(content, encoding="utf-8")
    cfg = load_regulation_config()
    cfg["style_policy"] = {
        "file": STYLE_POLICY_FILE,
        "source": source,
        "section": section,
        "set_date": current_date.today().isoformat(),
    }
    save_regulation_config(cfg)
    print(f"\nStyle policy saved to {STYLE_POLICY_FILE}")
    print(f"  Source:  {source}" + (f'  ->  section "{section}"' if section else ""))
