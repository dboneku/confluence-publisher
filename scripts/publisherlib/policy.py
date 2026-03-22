import copy
import re


_NUMBERED_HEADING_RE = re.compile(r"^\s*((?:\d+\.)*\d+)(?:[\.)])?\s+(.+\S)\s*$")


def extract_required_headings_from_policy(policy_text: str) -> list[str]:
    """Parse a style policy text and return detected required section/heading names."""
    required: list[str] = []
    lines = policy_text.splitlines()
    in_block = False

    trigger_re = re.compile(
        r"required.{0,30}section|must include|must contain|required heading"
        r"|all documents.{0,30}(?:must|shall).{0,30}(?:include|contain|have)",
        re.IGNORECASE,
    )
    inline_re = re.compile(r"(?:required.{0,30}:|headings[:：]|sections[:：])\s*(.+)", re.IGNORECASE)
    item_re = re.compile(r"^[\s\-\*•\d\.]+(.+)")

    for line in lines:
        stripped = line.strip()
        match = inline_re.search(stripped)
        if match:
            for part in re.split(r"[,;/]", match.group(1)):
                name = part.strip(' ."\'')
                if 2 <= len(name.split()) <= 6:
                    required.append(name)
            in_block = False
            continue
        if trigger_re.search(stripped):
            in_block = True
            continue
        if in_block:
            if not stripped:
                continue
            item_match = item_re.match(stripped)
            if item_match:
                name = item_match.group(1).strip(' ."\'')
                if 1 <= len(name.split()) <= 7:
                    required.append(name)
            elif stripped.startswith("#") or (stripped and stripped[0] not in "-*•0123456789"):
                in_block = False

    return list(dict.fromkeys(required))


def check_adf_against_style_policy(adf: dict, policy_text: str, node_text) -> list[str]:
    """Return warning strings for required headings that are absent in the ADF."""
    required = extract_required_headings_from_policy(policy_text)
    if not required:
        return []
    heading_texts = {
        node_text(node).lower().strip()
        for node in adf.get("content", [])
        if node.get("type") == "heading"
    }
    return [
        f'Style policy: missing required section "{required_heading}"'
        for required_heading in required
        if not any(required_heading.lower() in heading or heading in required_heading.lower() for heading in heading_texts)
    ]


def normalize_tokens(text: str) -> set[str]:
    """Lowercase, strip punctuation, remove common stop words, and return a token set."""
    stop = {
        "the", "of", "and", "a", "an", "in", "for", "to", "with", "on", "at",
        "by", "or", "is", "its", "their", "rec", "pol", "pro", "wf", "chk",
    }
    return {word for word in re.sub(r"[^\w\s]", "", text.lower()).split() if word not in stop}


def fuzzy_doc_match(title: str, regulation: str, regulation_configs: dict) -> tuple[str | None, float]:
    """Fuzzy-match a page title against a regulation's document catalog."""
    catalog = regulation_configs.get(regulation, {}).get("docs", {})
    title_tokens = normalize_tokens(title)
    best_id, best_score = None, 0.0
    for doc_id, doc_name in catalog.items():
        doc_tokens = normalize_tokens(doc_name)
        if not title_tokens or not doc_tokens:
            continue
        intersection = title_tokens & doc_tokens
        union = title_tokens | doc_tokens
        score = len(intersection) / len(union) if union else 0.0
        if score > best_score:
            best_score = score
            best_id = doc_id
    if best_score >= 0.35:
        return best_id, best_score
    return None, 0.0


def inject_regulation_doc_id(title: str, regulation: str | None, regulation_configs: dict) -> str:
    """Insert a matched regulation document ID into a title when applicable."""
    if not regulation:
        return title
    doc_id, _ = fuzzy_doc_match(title, regulation, regulation_configs)
    if not doc_id:
        return title
    match = re.match(r"^([A-Z0-9]+-[A-Z0-9]+-\d+)\s+(.+)$", title, re.I)
    if match:
        return f"{match.group(1)} {doc_id} {match.group(2)}"
    return f"{doc_id} {title}"


def strip_title_heading_from_adf(adf: dict, title: str, node_text) -> dict:
    """Remove a leading heading if it substantially duplicates the page title."""
    nodes = adf.get("content", [])
    if not nodes:
        return adf
    first = nodes[0]
    if first.get("type") != "heading":
        return adf
    heading_text = "".join(
        child.get("text", "") for child in first.get("content", []) if child.get("type") == "text"
    )
    title_tokens = normalize_tokens(title)
    heading_tokens = normalize_tokens(heading_text)
    if not title_tokens or not heading_tokens:
        return adf
    intersection = title_tokens & heading_tokens
    union = title_tokens | heading_tokens
    score = len(intersection) / len(union) if union else 0.0
    if score >= 0.5:
        result = copy.deepcopy(adf)
        result["content"] = result["content"][1:]
        return result
    return adf


def fix_adf_heading_numbers(adf: dict) -> tuple[dict, int]:
    """Normalize numbered heading-like blocks in ADF.

    Rules:
    - Remove leading numeric prefixes such as "1. ", "2) ", or "3.1 ".
    - Convert short numbered paragraphs into headings.
    - Default the heading level to 1.
    - If a numbered "1" block is immediately followed by a numbered "2" block,
      treat the first as level 1 and subsequent numbered heading-like blocks as
      level 2 until another adjacent 1→2 pair starts a new major section.
    """

    def _node_text(node: dict) -> str:
        parts: list[str] = []
        for child in node.get("content", []):
            if child.get("type") == "text":
                parts.append(child.get("text", ""))
            elif isinstance(child, dict) and child.get("content"):
                parts.append(_node_text(child))
        return "".join(parts).strip()

    def _numbered_heading_parts(text: str) -> tuple[str, int, str] | None:
        match = _NUMBERED_HEADING_RE.match(text)
        if not match:
            return None
        raw_number = match.group(1)
        heading_text = match.group(2).strip()
        if not heading_text:
            return None
        return raw_number, int(raw_number.split(".")[0]), heading_text

    def _is_heading_like_text(heading_text: str) -> bool:
        if len(heading_text) > 120:
            return False
        if len(heading_text.split()) > 12:
            return False
        if heading_text.endswith((".", "?", "!", ":", ";")):
            return False
        return True

    def _is_heading_like_paragraph(node: dict, heading_text: str) -> bool:
        if node.get("type") == "heading":
            return True
        if node.get("type") != "paragraph":
            return False
        return _is_heading_like_text(heading_text)

    def _ordered_list_heading_items(node: dict) -> list[dict] | None:
        if node.get("type") != "orderedList":
            return None
        items = []
        for item_index, list_item in enumerate(node.get("content", [])):
            if list_item.get("type") != "listItem":
                return None
            blocks = list_item.get("content", [])
            if len(blocks) != 1:
                return None
            block = blocks[0]
            if block.get("type") != "paragraph":
                return None
            heading_text = _node_text(block)
            if not heading_text or not _is_heading_like_text(heading_text):
                return None
            items.append(
                {
                    "list_item_index": item_index,
                    "major": item_index + 1,
                    "heading_text": heading_text,
                    "content": copy.deepcopy(block.get("content", [])),
                }
            )
        return items or None

    def _rewrite_inline_content(content: list[dict], stripped_text: str) -> list[dict]:
        new_content = copy.deepcopy(content)
        text_children = [child for child in new_content if child.get("type") == "text"]
        if len(text_children) == 1:
            text_children[0]["text"] = stripped_text
            return new_content
        return [{"type": "text", "text": stripped_text}]

    result = copy.deepcopy(adf)
    nodes = result.get("content", [])
    candidates: list[dict] = []

    def _is_adjacent(left: dict, right: dict) -> bool:
        if left["node_index"] == right["node_index"]:
            return (
                left.get("list_item_index") is not None
                and right.get("list_item_index") is not None
                and right["list_item_index"] == left["list_item_index"] + 1
            )
        return right["node_index"] == left["node_index"] + 1

    for index, node in enumerate(nodes):
        list_items = _ordered_list_heading_items(node)
        if list_items:
            for item in list_items:
                candidates.append(
                    {
                        "node_index": index,
                        "list_item_index": item["list_item_index"],
                        "major": item["major"],
                        "heading_text": item["heading_text"],
                        "source": "orderedList",
                        "content": item["content"],
                    }
                )
            continue

        text = _node_text(node)
        parts = _numbered_heading_parts(text)
        if not parts:
            continue
        _, major, heading_text = parts
        if not _is_heading_like_paragraph(node, heading_text):
            continue
        candidates.append(
            {
                "node_index": index,
                "list_item_index": None,
                "major": major,
                "heading_text": heading_text,
                "source": node.get("type"),
            }
        )

    levels = [1] * len(candidates)
    pair_starts = [
        idx
        for idx in range(len(candidates) - 1)
        if candidates[idx]["major"] == 1
        and candidates[idx + 1]["major"] == 2
        and _is_adjacent(candidates[idx], candidates[idx + 1])
    ]
    if pair_starts:
        current_pair = 0
        for idx in range(pair_starts[0] + 1, len(candidates)):
            next_pair_start = pair_starts[current_pair + 1] if current_pair + 1 < len(pair_starts) else None
            if next_pair_start is not None and idx == next_pair_start:
                levels[idx] = 1
                current_pair += 1
            else:
                levels[idx] = 2

    changes = 0
    list_replacements: dict[int, list[dict]] = {}
    list_changes: dict[int, int] = {}

    for candidate, level in zip(candidates, levels):
        if candidate["source"] == "orderedList":
            list_replacements.setdefault(candidate["node_index"], []).append(
                {
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": _rewrite_inline_content(candidate["content"], candidate["heading_text"]),
                }
            )
            list_changes[candidate["node_index"]] = list_changes.get(candidate["node_index"], 0) + 1
            continue

        node = nodes[candidate["node_index"]]
        new_content = _rewrite_inline_content(node.get("content", []), candidate["heading_text"])
        new_node = copy.deepcopy(node)
        old_type = new_node.get("type")
        old_level = new_node.get("attrs", {}).get("level") if old_type == "heading" else None
        new_node["type"] = "heading"
        new_node["attrs"] = dict(new_node.get("attrs") or {})
        new_node["attrs"]["level"] = level
        new_node["content"] = new_content
        nodes[candidate["node_index"]] = new_node
        if old_type != "heading" or old_level != level or _node_text(node) != candidate["heading_text"]:
            changes += 1

    if list_replacements:
        rebuilt_nodes = []
        for index, node in enumerate(nodes):
            if index in list_replacements:
                rebuilt_nodes.extend(list_replacements[index])
                changes += list_changes.get(index, 0)
            else:
                rebuilt_nodes.append(node)
        result["content"] = rebuilt_nodes

    return result, changes
