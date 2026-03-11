#!/usr/bin/env python3
"""
Confluence Publisher
Usage: python publish.py [--mapping mapping.csv] [--file path/or/url] [--dry-run]
"""

import os
import re
import sys
import json
import base64
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ATLASSIAN_URL  = os.environ.get("ATLASSIAN_URL", "").rstrip("/")
ATLASSIAN_EMAIL = os.environ.get("ATLASSIAN_EMAIL", "")
ATLASSIAN_TOKEN = os.environ.get("ATLASSIAN_API_TOKEN", "")

def normalize_title(stem: str) -> str:
    """Collapse stray spaces around hyphens: 'OHH- POL-Foo' → 'OHH-POL-Foo'"""
    return re.sub(r'\s*-\s*', '-', stem).strip()


def get_headers():
    if not ATLASSIAN_EMAIL or not ATLASSIAN_TOKEN:
        print("ERROR: Missing ATLASSIAN_EMAIL or ATLASSIAN_API_TOKEN in .env")
        sys.exit(1)
    auth = base64.b64encode(f"{ATLASSIAN_EMAIL}:{ATLASSIAN_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

# ---------------------------------------------------------------------------
# Space helpers
# ---------------------------------------------------------------------------

def list_spaces():
    r = requests.get(
        f"{ATLASSIAN_URL}/wiki/api/v2/spaces",
        params={"limit": 250},
        headers=get_headers(),
    )
    r.raise_for_status()
    return r.json().get("results", [])


def resolve_space_id(space_key: str) -> str:
    r = requests.get(
        f"{ATLASSIAN_URL}/wiki/api/v2/spaces",
        params={"keys": space_key, "limit": 1},
        headers=get_headers(),
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise ValueError(f"Space '{space_key}' not found")
    return results[0]["id"]


def resolve_parent_id(space_key: str, parent_title: str) -> str | None:
    """Resolve a parent page or folder ID using CQL (v2 API silently omits folders)."""
    if not parent_title or not parent_title.strip():
        return None
    r = requests.get(
        f"{ATLASSIAN_URL}/wiki/rest/api/content/search",
        params={"cql": f'space="{space_key}" AND title="{parent_title.strip()}"', "limit": 5},
        headers=get_headers(),
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise ValueError(f"Parent page or folder '{parent_title}' not found in space {space_key}")
    return results[0]["id"]


def find_existing_page(space_id: str, title: str) -> dict | None:
    r = requests.get(
        f"{ATLASSIAN_URL}/wiki/api/v2/pages",
        params={"spaceId": space_id, "title": title, "limit": 1},
        headers=get_headers(),
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    return results[0] if results else None


def get_page_version(page_id: str) -> int:
    r = requests.get(
        f"{ATLASSIAN_URL}/wiki/api/v2/pages/{page_id}",
        headers=get_headers(),
    )
    r.raise_for_status()
    return r.json()["version"]["number"]


def list_child_pages(parent_id: str) -> list[dict]:
    r = requests.get(
        f"{ATLASSIAN_URL}/wiki/api/v2/pages/{parent_id}/children",
        params={"limit": 50},
        headers=get_headers(),
    )
    r.raise_for_status()
    return r.json().get("results", [])


def delete_page(page_id: str):
    r = requests.delete(
        f"{ATLASSIAN_URL}/wiki/api/v2/pages/{page_id}",
        headers=get_headers(),
    )
    r.raise_for_status()

# ---------------------------------------------------------------------------
# Source ingestion
# ---------------------------------------------------------------------------

def ingest_google_doc(url: str) -> str:
    """Export Google Doc as plain text."""
    import re
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Cannot extract doc ID from URL: {url}")
    doc_id = match.group(1)
    export_url = f"https://docs.google.com/feeds/download/documents/export/Export?id={doc_id}&exportFormat=txt"
    r = requests.get(export_url)
    if r.status_code == 403:
        raise PermissionError(
            f"Google Doc is not publicly accessible.\n"
            f"Share it as 'Anyone with the link can view' and retry.\n"
            f"URL: {url}"
        )
    r.raise_for_status()
    return r.text


def ingest_docx(path: str) -> str:
    """Plain-text fallback — used only by non-docx paths. docx uses docx_to_adf directly."""
    try:
        from docx import Document
    except ImportError:
        os.system("pip install python-docx -q")
        from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def docx_to_adf(path: str) -> dict:
    """Convert a .docx file directly to ADF, preserving headings, lists, tables, and inline formatting."""
    try:
        from docx import Document
        from docx.oxml.ns import qn as _qn
        from docx.text.paragraph import Paragraph
        from docx.table import Table as DTable
    except ImportError:
        os.system("pip install python-docx -q")
        from docx import Document
        from docx.oxml.ns import qn as _qn
        from docx.text.paragraph import Paragraph
        from docx.table import Table as DTable

    doc = Document(path)

    # ── numbering map ──────────────────────────────────────────────────────────
    def _num_type_map():
        try:
            numbering_el = doc.part.numbering_part._element
        except Exception:
            return {}
        abstract_nums = {}
        for an in numbering_el.findall(_qn('w:abstractNum')):
            an_id = an.get(_qn('w:abstractNumId'))
            for lvl in an.findall(_qn('w:lvl')):
                if lvl.get(_qn('w:ilvl')) == '0':
                    el = lvl.find(_qn('w:numFmt'))
                    if el is not None:
                        fmt = el.get(_qn('w:val'), '')
                        abstract_nums[an_id] = 'ordered' if fmt in (
                            'decimal', 'lowerLetter', 'upperLetter',
                            'lowerRoman', 'upperRoman') else 'bullet'
                    break
        num_map = {}
        for num in numbering_el.findall(_qn('w:num')):
            nid = num.get(_qn('w:numId'))
            ref = num.find(_qn('w:abstractNumId'))
            if ref is not None:
                num_map[nid] = abstract_nums.get(ref.get(_qn('w:val')), 'bullet')
        return num_map

    num_map = _num_type_map()

    def _get_numpr(pPr):
        if pPr is None:
            return None, None
        numPr = pPr.find(_qn('w:numPr'))
        if numPr is None:
            return None, None
        ilvl_el  = numPr.find(_qn('w:ilvl'))
        numid_el = numPr.find(_qn('w:numId'))
        ilvl  = ilvl_el.get(_qn('w:val'))  if ilvl_el  is not None else '0'
        numid = numid_el.get(_qn('w:val')) if numid_el is not None else None
        return numid, int(ilvl)

    def _para_size(para):
        for run in para.runs:
            if run.font.size:
                return run.font.size.pt
        try:
            sz = para.style.font.size
            if sz:
                return sz.pt
        except Exception:
            pass
        return None

    def _heading_level(para):
        style = para.style.name
        size  = _para_size(para)
        if style == 'Title':
            return 1
        if 'Heading 1' in style:
            return 2 if (size is None or size >= 13) else None
        if 'Heading 2' in style:
            return 3
        if 'Heading 3' in style:
            return 4
        if 'Heading 4' in style:
            return 5
        if style in ('Normal', 'Normal (Web)', 'Default Paragraph Style'):
            if size and size >= 18:
                return 1
            if size and size >= 13:
                return 2
        return None

    def _build_inline_with_breaks(para_el):
        """Walk paragraph XML, splitting into segments at <w:br> line-break elements."""
        current = []
        segments = [current]
        for child in para_el:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag == 'r':
                rPr = child.find(_qn('w:rPr'))
                marks = []
                if rPr is not None:
                    if rPr.find(_qn('w:b'))      is not None: marks.append({'type': 'strong'})
                    if rPr.find(_qn('w:i'))      is not None: marks.append({'type': 'em'})
                    if rPr.find(_qn('w:u'))      is not None: marks.append({'type': 'underline'})
                    if rPr.find(_qn('w:strike')) is not None: marks.append({'type': 'strike'})
                for rchild in child:
                    rtag = rchild.tag.split('}')[-1] if '}' in rchild.tag else rchild.tag
                    if rtag == 't':
                        text = rchild.text or ''
                        if text:
                            node = {'type': 'text', 'text': text}
                            if marks: node['marks'] = marks[:]
                            current.append(node)
                    elif rtag == 'br':
                        current = []
                        segments.append(current)
        return [s for s in segments if s]

    def _build_inline(para):
        nodes = []
        for run in para.runs:
            if not run.text:
                continue
            marks = []
            if run.bold:      marks.append({'type': 'strong'})
            if run.italic:    marks.append({'type': 'em'})
            if run.underline: marks.append({'type': 'underline'})
            node = {'type': 'text', 'text': run.text}
            if marks:
                node['marks'] = marks
            nodes.append(node)
        if not nodes and para.text.strip():
            nodes.append({'type': 'text', 'text': para.text})
        return nodes

    def _consecutive_headings_to_lists(nodes):
        """Convert runs of 2+ consecutive same-level headings (level >= 3) to bullet lists."""
        result = []
        i = 0
        while i < len(nodes):
            node = nodes[i]
            if node['type'] != 'heading' or node['attrs']['level'] < 3:
                result.append(node)
                i += 1
                continue
            level = node['attrs']['level']
            run = [node]
            j = i + 1
            while j < len(nodes) and nodes[j]['type'] == 'heading' and nodes[j]['attrs']['level'] == level:
                run.append(nodes[j])
                j += 1
            if len(run) >= 2:
                items = [{'type': 'listItem', 'content': [{'type': 'paragraph', 'content': h['content']}]}
                         for h in run]
                result.append({'type': 'bulletList', 'content': items})
                i = j
            else:
                result.append(node)
                i += 1
        return result

    def _convert_table(tbl_el):
        table = DTable(tbl_el, doc)
        rows = []
        for ri, row in enumerate(table.rows):
            cells = []
            seen = set()
            for cell in row.cells:
                cid = id(cell)
                if cid in seen:
                    continue
                seen.add(cid)
                cell_content = []
                for p in cell.paragraphs:
                    inline = _build_inline(p)
                    if inline:
                        cell_content.append({'type': 'paragraph', 'content': inline})
                if not cell_content:
                    cell_content = [{'type': 'paragraph', 'content': [{'type': 'text', 'text': ''}]}]
                ctype = 'tableHeader' if ri == 0 else 'tableCell'
                cells.append({'type': ctype, 'attrs': {}, 'content': cell_content})
            if cells:
                rows.append({'type': 'tableRow', 'content': cells})
        return {'type': 'table', 'attrs': {'isNumberColumnEnabled': False, 'layout': 'default'}, 'content': rows}

    # ── main pass ──────────────────────────────────────────────────────────────
    nodes = []
    pending_list = None  # {'type': 'bullet'|'ordered', 'items': [...]}

    def _flush():
        nonlocal pending_list
        if pending_list:
            lnode = 'orderedList' if pending_list['type'] == 'ordered' else 'bulletList'
            nodes.append({'type': lnode, 'content': pending_list['items']})
            pending_list = None

    for element in doc.element.body:
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

        if tag == 'tbl':
            _flush()
            nodes.append(_convert_table(element))

        elif tag == 'p':
            para   = Paragraph(element, doc)
            pPr    = element.find(_qn('w:pPr'))
            numid, ilvl = _get_numpr(pPr)

            if numid and numid != '0':
                ltype  = num_map.get(numid, 'bullet')
                inline = _build_inline(para)
                if not inline:
                    continue
                item = {'type': 'listItem', 'content': [{'type': 'paragraph', 'content': inline}]}
                if pending_list and pending_list['type'] == ltype:
                    pending_list['items'].append(item)
                else:
                    _flush()
                    pending_list = {'type': ltype, 'items': [item]}
            else:
                _flush()
                if not para.text.strip():
                    continue
                lvl      = _heading_level(para)
                segments = _build_inline_with_breaks(element)
                if lvl and len(segments) > 1:
                    # Multiline heading paragraph — split at line breaks
                    nodes.append({'type': 'heading', 'attrs': {'level': lvl}, 'content': segments[0]})
                    for seg in segments[1:]:
                        nodes.append({'type': 'paragraph', 'content': seg})
                elif lvl:
                    inline = segments[0] if segments else _build_inline(para)
                    nodes.append({'type': 'heading', 'attrs': {'level': lvl}, 'content': inline})
                else:
                    # Flatten segments (soft returns in body text become spaces)
                    inline = []
                    for si, seg in enumerate(segments):
                        inline.extend(seg)
                        if si < len(segments) - 1:
                            inline.append({'type': 'text', 'text': ' '})
                    if not inline:
                        inline = [{'type': 'text', 'text': para.text}]
                    nodes.append({'type': 'paragraph', 'content': inline})

    _flush()
    nodes = _consecutive_headings_to_lists(nodes)
    return {'version': 1, 'type': 'doc', 'content': nodes}


def ingest_pdf(path: str) -> str:
    try:
        import pdfplumber
    except ImportError:
        os.system("pip install pdfplumber -q")   
        import pdfplumber
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def ingest_file(source: str):
    """Return ADF dict for .docx, or plain text str for all other sources."""
    if source.startswith("https://docs.google.com"):
        return ingest_google_doc(source)
    p = Path(source)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {source}")
    ext = p.suffix.lower()
    if ext == ".docx":
        return docx_to_adf(str(p))   # returns ADF dict directly
    elif ext == ".pdf":
        return ingest_pdf(str(p))
    else:
        return p.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# ADF builder
# ---------------------------------------------------------------------------

def text_node(text: str, marks: list = None) -> dict:
    node = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def paragraph(*texts) -> dict:
    return {"type": "paragraph", "content": [text_node(t) for t in texts]}


def heading(level: int, text: str) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [text_node(text)],
    }


def bullet_list(items: list[str]) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [paragraph(item)]}
            for item in items
        ],
    }


def info_panel(text: str, panel_type: str = "info") -> dict:
    return {
        "type": "panel",
        "attrs": {"panelType": panel_type},
        "content": [paragraph(text)],
    }


def metadata_table(rows: list[tuple[str, str]]) -> dict:
    def header_cell(text):
        return {"type": "tableHeader", "content": [paragraph(text)]}
    def data_cell(text):
        return {"type": "tableCell", "content": [paragraph(text)]}

    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
        "content": [
            {
                "type": "tableRow",
                "content": [header_cell(k), data_cell(v)],
            }
            for k, v in rows
        ],
    }


def to_adf(content: str, template: str = "general") -> dict:
    """
    Convert plain text content to ADF, applying template structure.
    This is a scaffold — Claude Code will expand section detection per template.
    """
    lines = content.strip().splitlines()
    nodes = []

    # Template metadata headers
    if template == "iso27001":
        nodes.append(info_panel(
            "ISO 27001 Compliance Document — review Annex A control mapping before approving.",
            "warning"
        ))
        nodes.append(metadata_table([
            ("Document ID", "[TO BE COMPLETED]"),
            ("Version", "1.0"),
            ("Status", "Draft"),
            ("Owner", "[TO BE COMPLETED]"),
            ("Classification", "Internal"),
            ("ISO 27001 Clause", "[TO BE COMPLETED]"),
            ("Annex A Controls", "[TO BE COMPLETED]"),
            ("Date Created", "[TO BE COMPLETED]"),
            ("Next Review Date", "[TO BE COMPLETED]"),
        ]))

    # Convert source lines to ADF nodes
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Wiki markup heading detection
        if line.startswith("h1. "):
            nodes.append(heading(1, line[4:]))
        elif line.startswith("h2. "):
            nodes.append(heading(2, line[4:]))
        elif line.startswith("h3. "):
            nodes.append(heading(3, line[4:]))
        elif line.startswith("# ") or line.startswith("## ") or line.startswith("### "):
            level = len(line.split(" ")[0])
            nodes.append(heading(level, line.lstrip("# ")))
        elif line.startswith("* ") or line.startswith("- "):
            nodes.append(bullet_list([line[2:]]))
        else:
            nodes.append(paragraph(line))

    # Template section scaffolding — add missing required sections
    section_map = {
        "policy": [
            "Purpose", "Scope", "Definitions", "Roles and Responsibilities",
            "Policy Statements", "Compliance and Exceptions", "Related Documents", "Revision History"
        ],
        "procedure": [
            "Purpose", "Scope", "Prerequisites", "Procedure Steps",
            "Exceptions and Escalations", "Related Documents", "Revision History"
        ],
        "workflow": [
            "Purpose", "Trigger", "Roles Involved", "Flow Steps",
            "Decision Points", "Outcomes", "Related Documents"
        ],
        "record": ["Metadata", "Data Fields", "Audit Trail"],
        "form": ["Instructions", "Fields", "Submission Guidance"],
        "meeting_minutes": ["Attendees", "Agenda", "Discussion", "Decisions", "Action Items"],
        "iso27001": [
            "Purpose", "Scope", "Definitions", "Roles and Responsibilities",
            "Policy Statements", "Control Mapping", "Compliance and Exceptions",
            "Related Documents", "Revision History"
        ],
    }

    required = section_map.get(template.lower().replace(" ", "_"), [])
    existing_text = content.lower()
    for section in required:
        if section.lower() not in existing_text:
            nodes.append(heading(2, section))
            nodes.append(paragraph(f"[TO BE COMPLETED — {section}]"))

    return {"version": 1, "type": "doc", "content": nodes}

# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

def create_page(
    space_id: str,
    title: str,
    adf_body: dict,
    parent_id: str = None,
    labels: list[str] = None,
    status: str = "current",
) -> dict:
    payload = {
        "spaceId": space_id,
        "status": status,
        "title": title,
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(adf_body),
        },
    }
    if parent_id:
        payload["parentId"] = parent_id
    if labels:
        payload["metadata"] = {"labels": [{"name": l} for l in labels]}

    r = requests.post(
        f"{ATLASSIAN_URL}/wiki/api/v2/pages",
        headers=get_headers(),
        json=payload,
    )
    r.raise_for_status()
    return r.json()


def update_page(
    page_id: str,
    title: str,
    adf_body: dict,
    status: str = "current",
) -> dict:
    version = get_page_version(page_id)
    payload = {
        "id": page_id,
        "status": status,
        "title": title,
        "version": {"number": version + 1},
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(adf_body),
        },
    }
    r = requests.put(
        f"{ATLASSIAN_URL}/wiki/api/v2/pages/{page_id}",
        headers=get_headers(),
        json=payload,
    )
    r.raise_for_status()
    return r.json()


def page_url(page: dict) -> str:
    return f"{ATLASSIAN_URL}/wiki{page['_links']['webui']}"

# ---------------------------------------------------------------------------
# Mapping file loader
# ---------------------------------------------------------------------------

def load_mapping(path: str) -> list[dict]:
    try:
        import pandas as pd
    except ImportError:
        os.system("pip install pandas openpyxl -q") 
        import pandas as pd

    ext = Path(path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str)

    df = df.fillna("")
    required = {"file", "space_key"}
    missing = required - set(df.columns.str.lower())
    if missing:
        raise ValueError(f"Mapping file missing required columns: {missing}")

    df.columns = df.columns.str.lower().str.strip()
    return df.to_dict(orient="records")

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def analyze_file(source: str):
    """Run structural analysis on a file and print a report. No publishing."""
    from docx import Document
    from docx.oxml.ns import qn

    def _para_size(para):
        for run in para.runs:
            if run.font.size: return run.font.size.pt
        return None

    def _heading_level(para):
        style = para.style.name
        size  = _para_size(para)
        if style == 'Title': return 1
        if 'Heading 1' in style: return 2 if (size is None or size >= 13) else None
        if 'Heading 2' in style: return 3
        if 'Heading 3' in style: return 4
        if style in ('Normal', 'Normal (Web)'):
            if size and size >= 18: return 1
            if size and size >= 13: return 2
        return None

    p = Path(source)
    doc = Document(str(p))
    issues = []
    headings = paras = lists = 0
    consec = 0
    prev_heading = False
    misuse = 0

    for para in doc.paragraphs:
        if not para.text.strip(): continue
        pPr = para._element.find(qn('w:pPr'))
        numPr = pPr.find(qn('w:numPr')) if pPr is not None else None
        if numPr is not None:
            lists += 1
            prev_heading = False
            consec = 0
            continue
        lvl = _heading_level(para)
        style = para.style.name
        size  = _para_size(para)
        if 'Heading 1' in style and size and size < 13:
            misuse += 1
        if lvl:
            headings += 1
            consec += 1
            if consec >= 3:
                issues.append(f'⚠  Consecutive headings: "{para.text.strip()[:50]}" is heading #{consec} in a row')
        else:
            paras += 1
            consec = 0

    if misuse:
        issues.append(f'⚠  Style misuse: {misuse} "Heading 1" paragraphs at ≤12pt — reclassify as body text')

    # Template detection
    text = ' '.join(p.text.lower() for p in doc.paragraphs)
    template = 'General'
    if any(k in text for k in ['annex a', 'iso', '27001', 'isms']):
        template = 'ISO 27001'
    elif sum(1 for k in ['purpose','scope','policy statement','shall'] if k in text) >= 3:
        template = 'Policy'
    elif sum(1 for k in ['steps','procedure','prerequisites'] if k in text) >= 2:
        template = 'Procedure'
    elif text.count('☐') >= 3:
        template = 'Form' if 'signature' in text or 'consent' in text else 'Checklist'

    print(f"\nAnalysis: {source}")
    print("─" * 60)
    print(f"Template (auto-detected): {template}")
    print(f"Structure: {headings} headings, {paras} paragraphs, {lists} list items, {len(doc.tables)} tables")
    if issues:
        print(f"\nIssues ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\nIssues: none")
    print(f"\nTo publish: python3 publish.py --file \"{source}\" --space SPACE --parent \"Parent\"")


def main():
    parser = argparse.ArgumentParser(description="Publish documents to Confluence")
    parser.add_argument("--mapping", help="Path to mapping CSV/Excel file")
    parser.add_argument("--file", help="Single file path or Google Doc URL")
    parser.add_argument("--space", help="Space key (e.g. ISMS)")
    parser.add_argument("--parent", help="Parent page title")
    parser.add_argument("--title", help="Page title")
    parser.add_argument("--template", default="general",
                        choices=["policy","procedure","workflow","record","form",
                                 "meeting_minutes","iso27001","general"])
    parser.add_argument("--labels", help="Comma-separated labels")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview upload plan without publishing")
    parser.add_argument("--test-auth", action="store_true",
                        help="Test credentials and list spaces, then exit")
    parser.add_argument("--analyze", help="Analyze a file's structure without publishing")
    args = parser.parse_args()

    # Analyze mode — no credentials needed
    if args.analyze:
        analyze_file(args.analyze)
        return

    # Auth test mode
    if args.test_auth:
        if not ATLASSIAN_URL:
            print("ERROR: ATLASSIAN_URL not set in .env")
            sys.exit(1)
        try:
            spaces = list_spaces()
            print(f"Connected! Found {len(spaces)} spaces:")
            for s in spaces:
                print(f"  {s['key']:12} — {s['name']}")
        except Exception as e:
            print(f"Connection failed: {e}")
            sys.exit(1)
        return

    if not ATLASSIAN_URL:
        print("ERROR: ATLASSIAN_URL not set in .env")
        sys.exit(1)

    # Show spaces
    print("\nFetching Confluence spaces...")
    spaces = list_spaces()
    print("\nAvailable spaces:")
    for i, s in enumerate(spaces, 1):
        print(f"  {i}. {s['key']:10} — {s['name']}")
    print()

    if args.dry_run:
        print("[DRY RUN] No pages will be published.\n")

    # Single file mode
    if args.file:
        if not args.space:
            print("ERROR: --space required for single file mode")
            sys.exit(1)
        print(f"Ingesting: {args.file}")
        content = ingest_file(args.file)
        # docx returns ADF directly; other formats return plain text
        adf = content if isinstance(content, dict) else to_adf(content, args.template)
        json.loads(json.dumps(adf))  # validate

        title = args.title or normalize_title(Path(args.file).stem)
        labels = [l.strip() for l in args.labels.split(",")] if args.labels else []

        print(f"\nUpload plan:")
        print(f"  Title:    {title}")
        print(f"  Space:    {args.space}")
        print(f"  Parent:   {args.parent or '(space root)'}")
        print(f"  Template: {args.template}")
        print(f"  Labels:   {', '.join(labels) or 'none'}")

        if args.dry_run:
            print("\n[DRY RUN] Would publish the above. Done.")
            return

        confirm = input("\nProceed? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

        space_id = resolve_space_id(args.space)
        parent_id = resolve_parent_id(space_id, args.parent) if args.parent else None
        existing = find_existing_page(space_id, title)

        if existing:
            print(f"\nCOLLISION: '{title}' already exists.")
            choice = input("  1=Overwrite  2=Skip  [1/2]: ").strip()
            if choice == "2":
                print("Skipped.")
                return
            page = update_page(existing["id"], title, adf)
        else:
            page = create_page(space_id, title, adf, parent_id, labels)

        print(f"\nPublished: {page_url(page)}")
        return

    # Bulk mode
    if args.mapping:
        rows = load_mapping(args.mapping)
        print(f"\nLoaded {len(rows)} rows from mapping file.")

        print(f"\n{'FILE':<40} {'TITLE':<40} {'SPACE':<8} {'PARENT':<30} {'TEMPLATE':<15}")
        print("-" * 140)
        for row in rows:
            print(f"{row.get('file',''):<40} {row.get('title','(auto)'):<40} "
                  f"{row.get('space_key',''):<8} {row.get('parent_page','(root)'):<30} "
                  f"{row.get('template', args.template):<15}")

        if args.dry_run:
            print("\n[DRY RUN] Would publish the above. Done.")
            return

        confirm = input(f"\nProceed with publishing {len(rows)} pages? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

        collision_default = None
        apply_to_all = False
        results = []

        for row in rows:
            source = row.get("file", "")
            space_key = row.get("space_key", args.space or "")
            template = row.get("template", args.template) or args.template
            parent_title = row.get("parent_page", "")
            raw_labels = row.get("labels", "")
            labels = [l.strip() for l in raw_labels.split(",")] if raw_labels else []

            try:
                print(f"\nProcessing: {source}")
                content = ingest_file(source)
                adf = content if isinstance(content, dict) else to_adf(content, template)
                json.loads(json.dumps(adf))  # validate

                # Apply naming convention if title blank
                title = row.get("title", "").strip() or normalize_title(Path(source).stem)

                space_id = resolve_space_id(space_key)
                parent_id = resolve_parent_id(space_id, parent_title) if parent_title else None
                existing = find_existing_page(space_id, title)

                if existing:
                    if apply_to_all and collision_default:
                        choice = collision_default
                    else:
                        print(f"  COLLISION: '{title}' exists.")
                        raw = input("  1=Overwrite  2=Skip  3=Cancel all  Apply to all? [y/n]: ")
                        parts = raw.strip().split()
                        choice = parts[0] if parts else "2"
                        if len(parts) > 1 and parts[1].lower() == "y":
                            apply_to_all = True
                            collision_default = choice

                    if choice == "3":
                        print("Cancelled.")
                        break
                    elif choice == "2":
                        results.append({"file": source, "title": title, "status": "SKIP", "url": ""})
                        continue
                    else:
                        page = update_page(existing["id"], title, adf)
                else:
                    page = create_page(space_id, title, adf, parent_id, labels)

                url = page_url(page)
                results.append({"file": source, "title": title, "status": "OK", "url": url})
                print(f"  Published: {url}")

            except Exception as e:
                results.append({"file": source, "title": title, "status": "FAIL", "url": str(e)})
                print(f"  FAILED: {e}")

        # Summary
        ok    = sum(1 for r in results if r["status"] == "OK")
        skip  = sum(1 for r in results if r["status"] == "SKIP")
        fail  = sum(1 for r in results if r["status"] == "FAIL")

        print(f"\n{'='*60}")
        print(f"Results: {ok} published, {skip} skipped, {fail} failed")
        print(f"{'FILE':<40} {'STATUS':<8} {'URL'}")
        print("-" * 100)
        for r in results:
            print(f"{r['file']:<40} {r['status']:<8} {r['url']}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
