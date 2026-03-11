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

| Template | Default pattern |
|---|---|
| Policy | `[Org]-POL-[NN] [Title]` |
| Procedure | `[Org]-PRO-[NN] [Title]` |
| Workflow | `[Org]-WF-[NN] [Title]` |
| Form | `[Org]-FRM-[NN] [Title]` |
| Checklist | `[Org]-CHK-[NN] [Title]` |
| Meeting Minutes | `[YYYY-MM-DD] [Team] Meeting Minutes` |
| ISO 27001 | `[Org]-[NN]-[DOMAIN] [Title] ([Type])` |
| General | Use source filename (normalized — collapse spaces around hyphens) |
