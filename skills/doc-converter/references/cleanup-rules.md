# Document Cleanup Rules

Apply these rules in order during Step 5 of the doc-converter workflow.

---

## 1. Consecutive Headings

**Rule:** No more than 2 consecutive headings without body content between them.

**Detection:** Walk the node list. Track runs of consecutive heading nodes. Flag any run ≥ 3.

**Action:**
- 2 consecutive headings → allowed, no action.
- 3+ consecutive headings → insert placeholder paragraph between headings 2 and 3:
  `[Section content pending — review before publishing]`
- Report each instance to the user before publishing.

**Example (before):**
```
H2: Background Verification
H3: Identity Verification
H3: Employment History
H3: Criminal History Checks
```
**Example (after):**
```
H2: Background Verification
H3: Identity Verification
  [Section content pending — review before publishing]
H3: Employment History
  [Section content pending — review before publishing]
H3: Criminal History Checks
```

---

## 2. Empty Sections

**Rule:** A heading immediately followed by another heading (no content at all) is an empty section.

**Action:** Flag with a warning panel in ADF (`panelType: warning`), or an HTML comment in Markdown/HTML:
```
⚠ Empty section: "[Heading title]" — no content before next heading.
```
Do not silently drop the heading.

---

## 3. Heading Level Skips

**Rule:** Heading levels should not skip (e.g. H1 → H3 with no H2).

**Detection:** Track current heading level. Flag when `new_level > current_level + 1`.

**Action:** Demote the skipped-to heading to `current_level + 1` and report. Do not silently promote content.

---

## 4. Style Misuse — Heading Used as Body Text

**Rule:** A Word "Heading N" style paragraph that is actually body text (identified by font size ≤ 12pt when the heading style's normal size is ≥ 14pt) should be reclassified as a paragraph.

**Detection logic:**
| Word Style | Expected size | Reclassify if size is... |
|---|---|---|
| Heading 1 | ≥ 14pt | ≤ 12pt |
| Heading 2 | ≥ 12pt | ≤ 10pt |
| Heading 3 | ≥ 11pt | ≤ 9pt |

**Action:** Reclassify as `paragraph`. Report count at end of analysis (e.g. "6 Heading 1 paragraphs reclassified as body text").

---

## 5. Font Size Standardization

**Standard scale for ADF/Confluence output:**

| Content type | Standard size | ADF node |
|---|---|---|
| Document title | 20pt | `heading` level 1 |
| Major section | 16pt | `heading` level 2 |
| Subsection | 14pt | `heading` level 3 |
| Sub-subsection | 12pt | `heading` level 4 |
| Body paragraph | 11pt | `paragraph` |
| Table cell | 11pt | `tableCell` → `paragraph` |
| List item | 11pt | `listItem` → `paragraph` |
| Caption / footnote | 9pt | `paragraph` |

**Action:** Map each node to the standard size for its type. Do not propagate non-standard sizes to ADF — ADF heading levels control rendered size in Confluence. Font size in the source is used only for *classification*, not for styling the output.

---

## 6. Font Standardization

**Rule:** Body text should use a single consistent font. Mixed fonts in body paragraphs indicate copy-paste from external sources.

**Detection:** Collect unique font families used across body paragraph runs. If more than one font family appears in body text, flag it.

**Standard fonts (in preference order):**
1. Use the document's declared default font if set.
2. Fall back to Calibri.
3. If no default is detectable, use the majority font.

**Action:**
- Normalize body text runs to the standard font in the output.
- Heading fonts are normalized to the standard font as well.
- Preserve `code`/`monospace` fonts (Courier New, Consolas, Mono) — do not normalize these.
- Report: "Body text font normalized: 3 fonts → Calibri"

---

## 7. List Numbering Normalization

**Rule:** Ordered lists must use Arabic numerals (1, 2, 3). Roman numerals and alphabetic lists are non-standard.

**Detection:** Check the `numFmt` value in the Word numbering definition:
- `lowerRoman` / `upperRoman` → Roman numerals (i/ii/iii or I/II/III)
- `lowerLetter` / `upperLetter` → Alphabetic (a/b/c or A/B/C)
- `decimal` → correct, no change needed

**Action:** Convert all non-decimal ordered lists to `decimal` (`orderedList` in ADF). The rendered order is always 1, 2, 3... in Confluence.

---

## 8. Single-Item Lists

**Rule:** A list containing only one item is not a list — it is a paragraph.

**Detection:** Any `bulletList` or `orderedList` node with exactly one `listItem` child.

**Action:** Replace the list node with a plain `paragraph` node containing the same inline content. Report: "1 single-item list converted to paragraph."

---

## 9. Orphaned Bold / Italic Paragraphs

**Rule:** An entire paragraph where every run is `bold` (or `italic`) often means it was intended as a heading or callout, not a body paragraph.

**Detection:** A `paragraph` node where all text runs carry the `strong` (or `em`) mark and the text is short (≤ 80 characters).

**Action:** Ask the user:
```
Found 2 fully-bold short paragraphs — possible headings:
  • "Legal and Regulatory Compliance"
  • "Candidate Consent"
Promote these to headings? [y/n] If yes, what level? [H2/H3/H4]
```
If the user declines, retain as a styled paragraph.

---

## 10. Checkbox / Form Field Preservation

**Rule:** Checkbox characters (☐ ✓ ✗) and fill-in blanks (`___`) are meaningful content in forms and checklists. Do not strip or normalize them.

**Action:** Preserve verbatim in `paragraph` or `listItem` content. Do not convert to bullet points.

---

## 11. Numbered Heading Continuity

**Rule:** If headings use manual numbering in their text (e.g. "1. Purpose", "2. Scope"), that numbering must be continuous throughout the document at each level. Restarting at 1 mid-document is an error.

**Detection:** A document uses manual numbered headings if ≥ 2 headings at any level begin with an Arabic numeral pattern: `^\d+\.`, `^\d+\.\d+`, etc. Walk all headings at each level in document order; flag any heading where the number ≤ the previous number at the same level.

**Exception:** Hierarchical sub-numbering that resets per parent (1.1, 1.2 under section 1, then 2.1, 2.2 under section 2) is correct — do NOT flag.

**Action:** Replace the leading number with the correct sequential value. Preserve everything after the number. Report: "Numbered heading continuity: 2 headings renumbered at H2 (4, 5)". If the pattern is ambiguous, flag for user review rather than auto-fixing.

---

## Summary Checklist

Run these in order for every document:

- [ ] Consecutive headings (≥ 3 in a row) — insert placeholder
- [ ] Empty sections — add warning panel
- [ ] Heading level skips — demote to correct level
- [ ] Style misuse — reclassify body-sized headings as paragraphs
- [ ] Font sizes — use for classification only; do not propagate to ADF
- [ ] Font families — normalize body text to document default
- [ ] List numbering — convert Roman/alphabetic to Arabic
- [ ] Single-item lists — convert to paragraphs
- [ ] Orphaned bold paragraphs — ask user about promotion
- [ ] Checkboxes / fill-in fields — preserve verbatim
- [ ] Numbered heading continuity — renumber headings that restart mid-document
