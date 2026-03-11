# ADF (Atlassian Document Format) Reference

Quick reference for building valid ADF JSON for Confluence Cloud REST API v2.

---

## Document Root

```json
{
  "version": 1,
  "type": "doc",
  "content": [ /* block nodes */ ]
}
```

---

## Block Nodes

### Heading

```json
{
  "type": "heading",
  "attrs": { "level": 1 },
  "content": [ /* inline nodes */ ]
}
```
`level`: 1–6. Confluence renders H1–H4 with distinct styles; H5–H6 are small.

---

### Paragraph

```json
{
  "type": "paragraph",
  "content": [ /* inline nodes */ ]
}
```
Empty paragraph (blank line): `{"type": "paragraph", "content": []}` — valid but omit if not needed.

---

### Bullet List

```json
{
  "type": "bulletList",
  "content": [
    {
      "type": "listItem",
      "content": [
        { "type": "paragraph", "content": [ /* inline */ ] }
      ]
    }
  ]
}
```

---

### Ordered List

```json
{
  "type": "orderedList",
  "attrs": { "order": 1 },
  "content": [
    {
      "type": "listItem",
      "content": [
        { "type": "paragraph", "content": [ /* inline */ ] }
      ]
    }
  ]
}
```
`order`: starting number (default 1). Always use Arabic numerals — Confluence ignores other formats.

---

### Table

```json
{
  "type": "table",
  "attrs": {
    "isNumberColumnEnabled": false,
    "layout": "default"
  },
  "content": [
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableHeader",
          "attrs": {},
          "content": [ { "type": "paragraph", "content": [ /* inline */ ] } ]
        }
      ]
    },
    {
      "type": "tableRow",
      "content": [
        {
          "type": "tableCell",
          "attrs": {},
          "content": [ { "type": "paragraph", "content": [ /* inline */ ] } ]
        }
      ]
    }
  ]
}
```
`layout` options: `"default"`, `"wide"`, `"full-width"`.
Table cells must always contain at least one block node (e.g. paragraph). Never put inline nodes directly in a cell.

---

### Panel

```json
{
  "type": "panel",
  "attrs": { "panelType": "info" },
  "content": [ { "type": "paragraph", "content": [ /* inline */ ] } ]
}
```
`panelType` options: `"info"` (blue), `"warning"` (yellow), `"error"` (red), `"success"` (green), `"note"` (purple).

---

### Rule (Horizontal Divider)

```json
{ "type": "rule" }
```

---

### Code Block

```json
{
  "type": "codeBlock",
  "attrs": { "language": "python" },
  "content": [ { "type": "text", "text": "print('hello')" } ]
}
```
`language`: optional. Common values: `"python"`, `"javascript"`, `"bash"`, `"sql"`, `"json"`, `"plain"`.

---

## Inline Nodes

### Text with Marks

```json
{
  "type": "text",
  "text": "Hello world",
  "marks": [
    { "type": "strong" },
    { "type": "em" }
  ]
}
```

### Available Marks

| Mark type | Effect | Attrs required |
|---|---|---|
| `strong` | Bold | none |
| `em` | Italic | none |
| `underline` | Underline | none |
| `strike` | Strikethrough | none |
| `code` | Inline code | none |
| `textColor` | Text color | `{"color": "#RRGGBB"}` |
| `link` | Hyperlink | `{"href": "https://..."}` |
| `subsup` | Superscript/subscript | `{"type": "sup"}` or `{"type": "sub"}` |

Multiple marks can be applied to one text node — put them all in the `marks` array.

---

## Common Validation Errors

| Error | Cause | Fix |
|---|---|---|
| `inline node in block position` | Text node placed directly in `doc` or `table` | Wrap in `paragraph` |
| `block node in inline position` | `paragraph` placed inside `paragraph` | Flatten the structure |
| `empty content array` | `listItem` or `tableCell` with no children | Add at least one `paragraph` |
| `invalid panelType` | Misspelled panel type | Use only: info, warning, error, success, note |
| `level out of range` | Heading level 0 or > 6 | Clamp to 1–6 |
| `missing version` | Root doc node missing `"version": 1` | Always include it |

---

## Publish / Update API

**Create page:**
```
POST /wiki/api/v2/pages
{
  "spaceId": "884740",
  "status": "current",
  "title": "Page Title",
  "parentId": "4751361",          // optional folder or page ID
  "body": {
    "representation": "atlas_doc_format",
    "value": "<json-stringified ADF>"
  }
}
```

**Update page:**
```
PUT /wiki/api/v2/pages/{page_id}
{
  "id": "{page_id}",
  "status": "current",
  "title": "Page Title",
  "version": { "number": <current_version + 1> },
  "body": {
    "representation": "atlas_doc_format",
    "value": "<json-stringified ADF>"
  }
}
```

Always `json.dumps()` the ADF dict for the `value` field — it must be a JSON string, not an object.

Always fetch current version before updating:
```
GET /wiki/api/v2/pages/{page_id}  →  response["version"]["number"]
```
