# Confluence Page Templates

## Template Detection Keywords

| Template | Signal keywords / patterns | Minimum matches |
|---|---|---|
| Policy | "purpose", "scope", "policy statement", "shall", "compliance" | 3 |
| Procedure | "steps", "procedure", "prerequisites", "how to" | 2 |
| Form | Checkbox chars (☐ ✓), fill-in blanks (`___`), "signature" | ☐ × 3 or ___ × 3 |
| Checklist | Majority of content is checkbox items, short lines | ☐ × 5 |
| Meeting Minutes | "attendees", "agenda", "action items", "decisions" | 2 |
| ISO 27001 | "ISO", "annex A", "27001", "ISMS", control IDs (A.x.x) | 1 |
| General | No clear match | — |

If two templates score equally or match is weak, ask the user.

**Missing sections:** Never auto-add missing sections during publish or remediation. Identify them in the audit report and ask the user which (if any) to add. Only add what is explicitly confirmed.

---

## Required Sections by Template

### Policy
Purpose, Scope, Definitions, Roles and Responsibilities, Policy Statements, Compliance and Exceptions, Related Documents, Revision History

### Procedure
Purpose, Scope, Prerequisites, Procedure Steps, Exceptions and Escalations, Related Documents, Revision History

### Workflow
Purpose, Trigger, Roles Involved, Flow Steps, Decision Points, Outcomes, Related Documents

### Form
Instructions, Fields (label / type / required / options), Submission Guidance

### Checklist
Instructions, Checklist Items (grouped by section), Completion / Sign-off

### Meeting Minutes
Date, Attendees, Agenda, Discussion, Decisions, Action Items (owner + due date)

### ISO 27001
Mandatory metadata block + Purpose, Scope, Definitions, Roles and Responsibilities, Policy Statements, Control Mapping (Annex A), Compliance and Exceptions, Related Documents, Revision History

### General
No required sections. Publish content as-is.

---

## ISO 27001 Metadata Block

Add as an ADF table at the top of the document:

| Field | Value |
|---|---|
| Document ID | [TO BE COMPLETED] |
| Title | [document title] |
| Version | 1.0 |
| Status | Draft |
| Owner | [TO BE COMPLETED] |
| Classification | Internal |
| ISO 27001 Clause | [TO BE COMPLETED] |
| Annex A Controls | [TO BE COMPLETED] |
| Date Created | [TODAY] |
| Next Review Date | [TO BE COMPLETED] |

### Annex A Themes
- Organizational: A.5.1–A.5.37
- People: A.6.1–A.6.8
- Physical: A.7.1–A.7.14
- Technological: A.8.1–A.8.34

For clinical/healthcare content: always include A.8.10 (Data Masking), A.5.33 (Protection of Records), A.5.34 (Privacy).

---

## Naming Conventions

All document types use the same convention:

```
[DOC_TYPE]-[ISO_CODE]-[SPACE]-[Document Name]
```

| Part | Rule |
|---|---|
| DOC_TYPE | `POL`, `PRO`, `REC`, `GUI`, `STD` — required |
| ISO_CODE | Primary Annex A control or clause (e.g. `A.5.1`, `6.1.2`) — omit if unknown |
| SPACE | Confluence space key (e.g. `ISMS`, `OHH`, `HR`) — required |
| Document Name | Title-cased, spaces preserved — **never underscores** |

Examples:
- `POL-A.5.1-ISMS-Information Security Policy`
- `PRO-A.5.24-OHH-Incident Response Procedure`
- `REC-OHH-Asset Inventory`
- `GUI-A.8.1-ISMS-Endpoint Security Guideline`

**Meeting Minutes** (no DOC_TYPE prefix): `[YYYY-MM-DD] [Team] Meeting Minutes`

**Document ID** (metadata field, not the title): `DOC-YYYY-NNN` — always auto-assigned from live Confluence query. Never use a local spreadsheet or tracker. Strip any old-format prefixes (e.g. `OHH-POL-001`, `OverSite 09-IS`) and reformat to the convention above.
