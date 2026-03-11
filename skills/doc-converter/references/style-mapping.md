# Style Mapping Reference

Mapping tables for Word styles and Google Docs HTML → ADF, Markdown, and HTML output.

---

## Word Style → ADF

### Heading Mapping

| Word Style | Size condition | ADF node | Level |
|---|---|---|---|
| `Title` | any | `heading` | 1 |
| `Heading 1` | ≥ 13pt or no size | `heading` | 2 |
| `Heading 1` | ≤ 12pt | `paragraph` | — |
| `Heading 2` | any | `heading` | 3 |
| `Heading 3` | any | `heading` | 4 |
| `Heading 4` | any | `heading` | 5 |
| `Normal` | ≥ 18pt | `heading` | 1 |
| `Normal` | ≥ 13pt | `heading` | 2 |
| `Normal` | any other | `paragraph` | — |
| `Normal (Web)` | same as Normal | same as Normal | — |
| `Default Paragraph Style` | same as Normal | same as Normal | — |
| `List Paragraph` | — | `listItem` > `paragraph` | — |
| Any other | — | `paragraph` | — |

### Inline Run Marks

| Word run property | ADF mark |
|---|---|
| `bold = True` | `{"type": "strong"}` |
| `italic = True` | `{"type": "em"}` |
| `underline = True` | `{"type": "underline"}` |
| `strike = True` | `{"type": "strike"}` |
| `font.color.rgb` (non-black) | `{"type": "textColor", "attrs": {"color": "#RRGGBB"}}` |
| Monospace font (Courier, Consolas, Mono) | `{"type": "code"}` |

### List Type Mapping (from numFmt)

| Word `numFmt` value | ADF list type |
|---|---|
| `decimal` | `orderedList` |
| `lowerRoman` / `upperRoman` | `orderedList` (normalized to decimal) |
| `lowerLetter` / `upperLetter` | `orderedList` (normalized to decimal) |
| `bullet` / `none` / anything else | `bulletList` |

### Table Cells

| Row index | ADF cell type |
|---|---|
| 0 (first row) | `tableHeader` |
| 1+ | `tableCell` |

Merged cells: deduplicate by tracking `id(cell)` — skip if already seen in that row.

---

## Google Docs HTML → ADF

Google Docs exported as HTML uses `<h1>`–`<h6>` tags and inline `<span>` with `style` attributes.

### Heading Tags

| HTML tag | ADF heading level |
|---|---|
| `<h1>` | 1 |
| `<h2>` | 2 |
| `<h3>` | 3 |
| `<h4>` | 4 |
| `<h5>` | 5 |
| `<h6>` | 6 |
| `<p>` | `paragraph` |
| `<ul>` / `<li>` | `bulletList` / `listItem` |
| `<ol>` / `<li>` | `orderedList` / `listItem` |
| `<table>` | `table` |
| `<tr>` | `tableRow` |
| `<th>` | `tableHeader` |
| `<td>` | `tableCell` |

### Inline Span Styles

Parse `style` attribute on `<span>` elements:

| CSS property | Value | ADF mark |
|---|---|---|
| `font-weight` | `bold` or `700` | `strong` |
| `font-style` | `italic` | `em` |
| `text-decoration` | `underline` | `underline` |
| `text-decoration` | `line-through` | `strike` |
| `color` | any hex/rgb | `textColor` |
| `font-family` | monospace family | `code` |

### Google Docs List Detection

Google Docs exports lists as `<ul>`/`<ol>` with nested `<li>`. Detect ordered vs unordered from the tag, not the style attribute.

Indent level = nesting depth of `<ul>`/`<ol>` elements.

---

## ADF → Markdown

For Markdown output, convert ADF nodes as follows:

| ADF node | Markdown |
|---|---|
| `heading` level 1 | `# text` |
| `heading` level 2 | `## text` |
| `heading` level 3 | `### text` |
| `heading` level 4 | `#### text` |
| `paragraph` | `text\n\n` |
| `bulletList` / `listItem` | `- text` |
| `orderedList` / `listItem` | `1. text` (let renderer handle numbering) |
| `table` | GFM pipe table |
| `rule` | `---` |
| `panel` (info) | `> **Info:** text` |
| `panel` (warning) | `> **Warning:** text` |
| `panel` (note) | `> **Note:** text` |

### Inline Marks → Markdown

| ADF mark | Markdown |
|---|---|
| `strong` | `**text**` |
| `em` | `*text*` |
| `underline` | `<u>text</u>` (HTML in MD) |
| `strike` | `~~text~~` |
| `code` | `` `text` `` |
| `textColor` | `<span style="color:#RRGGBB">text</span>` |

---

## ADF → HTML

| ADF node | HTML |
|---|---|
| `heading` level N | `<hN>text</hN>` |
| `paragraph` | `<p>text</p>` |
| `bulletList` | `<ul>` |
| `orderedList` | `<ol>` |
| `listItem` | `<li>text</li>` |
| `table` | `<table>` |
| `tableRow` | `<tr>` |
| `tableHeader` | `<th>text</th>` |
| `tableCell` | `<td>text</td>` |
| `rule` | `<hr>` |
| `panel` (info) | `<div class="panel info">text</div>` |
| `panel` (warning) | `<div class="panel warning">text</div>` |

### Inline Marks → HTML

| ADF mark | HTML |
|---|---|
| `strong` | `<strong>text</strong>` |
| `em` | `<em>text</em>` |
| `underline` | `<u>text</u>` |
| `strike` | `<s>text</s>` |
| `code` | `<code>text</code>` |
| `textColor` | `<span style="color:#RRGGBB">text</span>` |
