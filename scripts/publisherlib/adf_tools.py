import copy
import json
import re


def node_text(node: dict) -> str:
    if node.get("type") == "text":
        return node.get("text", "")
    return "".join(node_text(child) for child in node.get("content", []))


def adf_to_markdown(adf: dict) -> str:
    lines: list[str] = []

    def walk(node: dict, list_marker: str = ""):
        node_type = node.get("type", "")
        children = node.get("content", [])

        if node_type == "heading":
            level = node.get("attrs", {}).get("level", 1)
            text = node_text(node).strip()
            lines.append("#" * level + " " + text)
        elif node_type in ("paragraph", "tableCell", "tableHeader"):
            text = node_text(node).strip()
            if text:
                lines.append(list_marker + text if list_marker else text)
        elif node_type == "listItem":
            for child in children:
                walk(child, list_marker="- ")
            return
        elif node_type in ("bulletList", "orderedList"):
            for child in children:
                walk(child)
            return
        elif node_type == "rule":
            lines.append("---")
        elif node_type == "panel":
            text = node_text(node).strip()
            if text:
                lines.append(f"> {text}")
        elif node_type in ("table", "tableRow", "doc", "blockquote", "expand"):
            for child in children:
                walk(child)
            return
        else:
            for child in children:
                walk(child)

    for node in adf.get("content", []):
        walk(node)

    return "\n".join(lines)


def text_node(text: str, marks: list = None) -> dict:
    node = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def paragraph(*texts) -> dict:
    return {"type": "paragraph", "content": [text_node(text) for text in texts]}


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
    def header_cell(text: str) -> dict:
        return {"type": "tableHeader", "content": [paragraph(text)]}

    def data_cell(text: str) -> dict:
        return {"type": "tableCell", "content": [paragraph(text)]}

    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
        "content": [
            {"type": "tableRow", "content": [header_cell(key), data_cell(value)]}
            for key, value in rows
        ],
    }


def to_adf(content: str, template: str = "general") -> dict:
    lines = content.strip().splitlines()
    nodes = []

    if template == "iso27001":
        nodes.append(info_panel(
            "ISO 27001 Compliance Document — review Annex A control mapping before approving.",
            "warning",
        ))

    for line in lines:
        line = line.strip()
        if not line:
            continue
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

    section_map = {
        "policy": [
            "Purpose", "Scope", "Definitions", "Roles and Responsibilities",
            "Policy Statements", "Compliance and Exceptions", "Related Documents", "Revision History",
        ],
        "procedure": [
            "Purpose", "Scope", "Prerequisites", "Procedure Steps",
            "Exceptions and Escalations", "Related Documents", "Revision History",
        ],
        "workflow": [
            "Purpose", "Trigger", "Roles Involved", "Flow Steps",
            "Decision Points", "Outcomes", "Related Documents",
        ],
        "record": ["Metadata", "Data Fields", "Audit Trail"],
        "form": ["Instructions", "Fields", "Submission Guidance"],
        "meeting_minutes": ["Attendees", "Agenda", "Discussion", "Decisions", "Action Items"],
        "iso27001": [
            "Purpose", "Scope", "Definitions", "Roles and Responsibilities",
            "Policy Statements", "Control Mapping", "Compliance and Exceptions",
            "Related Documents", "Revision History",
        ],
    }

    required = section_map.get(template.lower().replace(" ", "_"), [])
    existing_text = content.lower()
    for section in required:
        if section.lower() not in existing_text:
            nodes.append(heading(2, section))
            nodes.append(paragraph(f"[TO BE COMPLETED — {section}]"))

    return {"version": 1, "type": "doc", "content": nodes}


_DOC_ID_PAT = re.compile(
    r"^((?:[A-Z]{2,6}-[A-Z]{2,6}-\d{2,4})(?:\s+\d{2,3}-[A-Z]+)?)\s+",
    re.IGNORECASE,
)
_CLF_RE = re.compile(r"document\s+classification", re.IGNORECASE)


def extract_doc_id_from_title(title: str) -> str | None:
    match = _DOC_ID_PAT.match(title)
    return match.group(1).strip() if match else None


def extract_classification_from_adf(adf: dict) -> str:
    classification_re = re.compile(r"document\s+classification[:\-]\s*(.+)", re.IGNORECASE)
    for node in adf.get("content", [])[:10]:
        match = classification_re.search(node_text(node).strip())
        if match:
            return match.group(1).strip()
    return "Internal"


def build_doc_control_header(classification: str = "Internal") -> list[dict]:
    return [{
        "type": "paragraph",
        "attrs": {"textAlign": "right"},
        "content": [{
            "type": "text",
            "text": f"Document classification: {classification}",
            "marks": [{"type": "em"}],
        }],
    }]


def build_doc_control_footer(title: str, doc_id: str = None) -> list[dict]:
    doc_prefix = f"{doc_id}  " if doc_id else ""
    message = (
        f"⚠  UNCONTROLLED WHEN PRINTED  —  {doc_prefix}{title}.  "
        "The print date, version, and page numbers are supplied by your browser or PDF viewer.  "
        "Verify this is the current approved version before use."
    )
    return [{"type": "rule"}, info_panel(message, "warning")]


def has_doc_control_header(adf: dict) -> bool:
    for node in adf.get("content", [])[:3]:
        text = node_text(node).strip()
        if _CLF_RE.search(text):
            return True
        if node.get("type") == "table" and "Document Title" in text:
            return True
    return False


def strip_doc_control_blocks(adf: dict) -> dict:
    result = copy.deepcopy(adf)
    nodes = result.get("content", [])

    top_keep = []
    scanned = 0
    for node in nodes:
        node_type = node.get("type", "")
        text = node_text(node).strip()
        is_classification = bool(_CLF_RE.search(text)) and node_type == "paragraph"
        is_old_table = node_type == "table" and "Document Title" in text
        if (is_classification or is_old_table) and scanned < 6:
            scanned += 1
            continue
        top_keep.append(node)
        scanned += 1

    nodes = top_keep

    if nodes and nodes[-1].get("type") == "panel" and "UNCONTROLLED WHEN PRINTED" in node_text(nodes[-1]):
        nodes.pop()
        if nodes and nodes[-1].get("type") == "rule":
            nodes.pop()

    result["content"] = nodes
    return result


def wrap_with_print_controls(
    adf: dict,
    title: str,
    doc_id: str = None,
    classification: str = None,
) -> dict:
    resolved_classification = classification or extract_classification_from_adf(adf)
    clean = strip_doc_control_blocks(adf)
    result = dict(clean)
    result["content"] = (
        build_doc_control_header(resolved_classification)
        + clean.get("content", [])
        + build_doc_control_footer(title, doc_id)
    )
    return result


def diff_adf(old_adf: dict, new_adf: dict) -> tuple[bool, list[str]]:
    old_nodes = strip_doc_control_blocks(copy.deepcopy(old_adf)).get("content", [])
    new_nodes = strip_doc_control_blocks(copy.deepcopy(new_adf)).get("content", [])

    old_signatures = [json.dumps(node, sort_keys=True) for node in old_nodes]
    new_signatures = [json.dumps(node, sort_keys=True) for node in new_nodes]
    if old_signatures == new_signatures:
        return False, []

    old_headings = {node_text(node).strip() for node in old_nodes if node.get("type") == "heading"}
    new_headings = {node_text(node).strip() for node in new_nodes if node.get("type") == "heading"}
    added = new_headings - old_headings
    removed = old_headings - new_headings

    summary = []
    if added:
        summary.append(f"  + sections added:   {', '.join(sorted(added))}")
    if removed:
        summary.append(f"  - sections removed: {', '.join(sorted(removed))}")
    if not added and not removed:
        summary.append("  ~ text content modified")
    return True, summary


def adf_to_html(adf: dict, title: str = "") -> str:
    css = """
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           max-width: 960px; margin: 40px auto; padding: 0 20px; color: #172b4d; line-height: 1.6; }
    h1 { font-size: 1.8em; border-bottom: 2px solid #dfe1e6; padding-bottom: 8px; margin-top: 32px; }
    h2 { font-size: 1.4em; border-bottom: 1px solid #dfe1e6; padding-bottom: 4px; margin-top: 28px; }
    h3, h4, h5, h6 { font-size: 1.1em; margin-top: 20px; }
    p { margin: 10px 0; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0; }
    th { background: #f4f5f7; font-weight: 600; }
    th, td { border: 1px solid #dfe1e6; padding: 8px 12px; text-align: left; vertical-align: top; }
    ul, ol { padding-left: 24px; margin: 8px 0; }
    li { margin: 4px 0; }
    .panel { border-radius: 4px; padding: 12px 16px; margin: 16px 0; border-left: 4px solid; }
    .panel-info    { background: #e9f2ff; border-color: #0052cc; }
    .panel-warning { background: #fffae6; border-color: #ff8b00; }
    .panel-note    { background: #e3fcef; border-color: #00875a; }
    .panel-error   { background: #ffebe6; border-color: #de350b; }
    .panel-success { background: #e3fcef; border-color: #00875a; }
    .panel-title   { font-weight: 600; margin-bottom: 6px; }
    hr { border: none; border-top: 2px solid #dfe1e6; margin: 24px 0; }
    code { background: #f4f5f7; padding: 2px 5px; border-radius: 3px; font-family: monospace; font-size: 0.9em; }
    pre  { background: #f4f5f7; padding: 16px; border-radius: 4px; overflow-x: auto; margin: 16px 0; }
    pre code { background: none; padding: 0; }
    blockquote { border-left: 4px solid #dfe1e6; margin: 0; padding-left: 16px; color: #6b778c; }
    .clf { text-align: right; font-style: italic; color: #6b778c; font-size: 0.9em; margin-bottom: 24px; }
    .page-title { font-size: 2em; font-weight: 700; border-bottom: 2px solid #0052cc;
                  padding-bottom: 10px; margin-bottom: 24px; color: #0052cc; }
    .preview-badge { background: #ff8b00; color: white; font-size: 0.75em; font-weight: 600;
                     padding: 2px 8px; border-radius: 12px; vertical-align: middle; margin-left: 8px; }
    """

    def esc(value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def render_marks(text: str, marks: list[dict]) -> str:
        for mark in marks:
            mark_type = mark.get("type")
            if mark_type == "strong":
                text = f"<strong>{text}</strong>"
            elif mark_type == "em":
                text = f"<em>{text}</em>"
            elif mark_type == "code":
                text = f"<code>{text}</code>"
            elif mark_type == "underline":
                text = f"<u>{text}</u>"
            elif mark_type == "strike":
                text = f"<s>{text}</s>"
            elif mark_type == "link":
                href = esc(mark.get("attrs", {}).get("href", "#"))
                text = f'<a href="{href}">{text}</a>'
        return text

    def render_inline(nodes: list[dict]) -> str:
        parts = []
        for node in nodes:
            node_type = node.get("type")
            if node_type == "text":
                text = esc(node.get("text", "")).replace("\n", "<br>")
                parts.append(render_marks(text, node.get("marks", [])))
            elif node_type == "hardBreak":
                parts.append("<br>")
            elif node_type == "mention":
                parts.append(f"@{esc(node.get('attrs', {}).get('text', 'user'))}")
            elif node_type == "emoji":
                parts.append(esc(node.get("attrs", {}).get("text", "")))
        return "".join(parts)

    def render_list_item(node: dict) -> str:
        parts = []
        for child in node.get("content", []):
            if child.get("type") == "paragraph":
                parts.append(render_inline(child.get("content", [])))
            else:
                parts.append(render_node(child))
        return "".join(parts)

    def render_node(node: dict) -> str:
        node_type = node.get("type")
        children = node.get("content", [])
        attrs = node.get("attrs", {})

        if node_type == "heading":
            level = attrs.get("level", 2)
            return f"<h{level}>{render_inline(children)}</h{level}>\n"
        if node_type == "paragraph":
            inner = render_inline(children)
            if not inner.strip():
                return "<p>&nbsp;</p>\n"
            align = attrs.get("textAlign", "")
            if align == "right":
                return f'<p class="clf">{inner}</p>\n'
            style = f' style="text-align:{align}"' if align and align != "left" else ""
            return f"<p{style}>{inner}</p>\n"
        if node_type == "bulletList":
            items = "".join(f"<li>{render_list_item(item)}</li>" for item in children)
            return f"<ul>{items}</ul>\n"
        if node_type == "orderedList":
            start = attrs.get("order", 1)
            items = "".join(f"<li>{render_list_item(item)}</li>" for item in children)
            return f'<ol start="{start}">{items}</ol>\n'
        if node_type == "table":
            return f"<table>{''.join(render_node(row) for row in children)}</table>\n"
        if node_type == "tableRow":
            return f"<tr>{''.join(render_node(cell) for cell in children)}</tr>\n"
        if node_type == "tableHeader":
            return f"<th>{''.join(render_node(child) for child in children)}</th>"
        if node_type == "tableCell":
            return f"<td>{''.join(render_node(child) for child in children)}</td>"
        if node_type == "panel":
            panel_type = attrs.get("panelType", "info")
            body_html = "".join(render_node(child) for child in children)
            return f'<div class="panel panel-{esc(panel_type)}">{body_html}</div>\n'
        if node_type == "rule":
            return "<hr>\n"
        if node_type == "codeBlock":
            language = esc(attrs.get("language", ""))
            code_text = esc("".join(child.get("text", "") for child in children if child.get("type") == "text"))
            return f'<pre><code class="language-{language}">{code_text}</code></pre>\n'
        if node_type == "blockquote":
            return f"<blockquote>{''.join(render_node(child) for child in children)}</blockquote>\n"
        return "".join(render_node(child) for child in children)

    body_html = "".join(render_node(node) for node in adf.get("content", []))
    title_escaped = esc(title)
    title_block = (
        f'<div class="page-title">{title_escaped}<span class="preview-badge">PREVIEW</span></div>\n'
        if title else ""
    )
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        f"<title>{title_escaped} (Preview)</title>\n"
        f"<style>{css}</style>\n"
        "</head>\n<body>\n"
        f"{title_block}{body_html}"
        "</body>\n</html>\n"
    )


def extract_text_from_adf(nodes: list[dict]) -> str:
    parts = []
    for node in nodes:
        if node.get("type") == "text":
            parts.append(node.get("text", ""))
        child_text = extract_text_from_adf(node.get("content", []))
        if child_text:
            parts.append(child_text)
    return " ".join(parts)