import copy
import re


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
    """Strip simple numeric prefixes from ADF heading nodes."""
    numbered_pat = re.compile(r"^\d+\.\s+")
    changes = 0
    result = copy.deepcopy(adf)
    for node in result.get("content", []):
        if node.get("type") != "heading":
            continue
        first_text = next((child for child in node.get("content", []) if child.get("type") == "text"), None)
        if not first_text:
            continue
        match = numbered_pat.match(first_text.get("text", ""))
        if match:
            first_text["text"] = first_text["text"][len(match.group(0)) :]
            changes += 1
    return result, changes
