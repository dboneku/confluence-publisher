import re


REQUIRED_SECTIONS = {
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
    "form": ["Instructions", "Fields", "Submission Guidance"],
    "checklist": ["Instructions", "Checklist Items", "Completion"],
    "meeting_minutes": ["Attendees", "Agenda", "Decisions", "Action Items"],
    "iso27001": [
        "Purpose", "Scope", "Definitions", "Roles and Responsibilities",
        "Policy Statements", "Control Mapping", "Compliance and Exceptions",
        "Related Documents", "Revision History",
    ],
}


NAMING_PATTERNS = {
    "policy": (re.compile(r"^[A-Z]+-POL-\d+[\s\-].+", re.I), "ORG-POL-001 Document Title"),
    "procedure": (re.compile(r"^[A-Z]+-PRO-\d+[\s\-].+", re.I), "ORG-PRO-001 Document Title"),
    "workflow": (re.compile(r"^[A-Z]+-WF-\d+[\s\-].+", re.I), "ORG-WF-001 Document Title"),
    "form": (re.compile(r"^[A-Z]+-FRM-\d+[\s\-].+", re.I), "ORG-FRM-001 Document Title"),
    "checklist": (re.compile(r"^[A-Z]+-CHK-\d+[\s\-].+", re.I), "ORG-CHK-001 Document Title"),
    "meeting_minutes": (re.compile(r"^\d{4}-\d{2}-\d{2}.+", re.I), "2026-01-01 Team Meeting Minutes"),
    "iso27001": (re.compile(r"^[A-Z]+-\d+[\s\-].+", re.I), "ORG-001-DOMAIN Document Title (Type)"),
}


def detect_template_from_text(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["annex a", "iso 27001", "27001", "isms"]):
        return "iso27001"
    if sum(1 for token in ["purpose", "scope", "policy statement", "shall"] if token in lowered) >= 3:
        return "policy"
    if sum(1 for token in ["steps", "procedure", "prerequisites"] if token in lowered) >= 2:
        return "procedure"
    if sum(1 for token in ["attendees", "agenda", "action items", "decisions"] if token in lowered) >= 2:
        return "meeting_minutes"
    if sum(1 for token in ["trigger", "flow steps", "decision points"] if token in lowered) >= 2:
        return "workflow"
    if lowered.count("☐") >= 5:
        return "checklist"
    if lowered.count("☐") >= 3 or "___" in lowered:
        return "form"
    return "general"


def check_template_sections(content_nodes: list[dict], template: str) -> list[str]:
    required = REQUIRED_SECTIONS.get(template.lower(), [])
    if not required:
        return []
    heading_texts = set()
    for node in content_nodes:
        if node.get("type") != "heading":
            continue
        text = "".join(
            child.get("text", "") for child in node.get("content", [])
            if child.get("type") == "text"
        )
        heading_texts.add(text.lower().strip())
    return [section for section in required if section.lower() not in heading_texts]


def validate_naming_convention(stem: str, template: str) -> tuple[bool, str]:
    entry = NAMING_PATTERNS.get(template.lower())
    if entry is None:
        return True, ""
    pattern, example = entry
    return bool(pattern.match(stem)), example