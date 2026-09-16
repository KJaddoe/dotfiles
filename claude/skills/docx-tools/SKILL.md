---
name: docx-tools
description: Use when creating, reading, editing, or analyzing Word documents (.docx) - extracting text and structure, generating new documents, modifying existing ones, or working with tracked changes and comments.
---

# Docx Tools

## Overview

A `.docx` file is a zip archive of XML parts (`word/document.xml` plus relationship and
content-type manifests). `python-docx` covers reading, creating, and simple editing against this
structure, but it has no native support for tracked changes or comments, so redlining requires
editing the underlying XML directly.

## Workflow Decision Tree

| Situation                                                                                 | Go to                                               |
|-------------------------------------------------------------------------------------------|-----------------------------------------------------|
| Reading or extracting text and structure from a document                                  | Reading and analyzing content                       |
| Creating a new document from scratch                                                      | Creating a new document                             |
| Editing your own document, simple text changes                                            | Basic editing                                       |
| Editing someone else's document, or any legal, academic, business, or government document | Redlining workflow (required default, not optional) |

## Reading and analyzing content

Open the document with `Document(path)` and iterate `doc.paragraphs` for body text and
`doc.tables` for tabular content. A table's cells are reached through `table.rows[i].cells[j]`.

```python
from docx import Document

doc = Document("report.docx")

for paragraph in doc.paragraphs:
    if paragraph.text.strip():
        print(f"[{paragraph.style.name}] {paragraph.text}")

for table_index, table in enumerate(doc.tables):
    print(f"Table {table_index}:")
    for row in table.rows:
        cells = [cell.text for cell in row.cells]
        print(cells)
```

Paragraph order in `doc.paragraphs` reflects body flow, but text inside tables, headers, footers,
and text boxes is not included there; walk `doc.tables` and `doc.sections[i].header` /
`.footer` separately when those matter.

## Creating a new document

Call `Document()` with no path to start a blank document, build it with `add_heading()`,
`add_paragraph()`, and `add_table()`, then `save()`.

```python
from docx import Document
from docx.shared import Pt

doc = Document()

doc.add_heading("Quarterly Summary", level=1)
doc.add_paragraph(
    "This report covers revenue and headcount for the quarter."
)

doc.add_heading("Revenue", level=2)
doc.add_paragraph("Revenue grew 12% quarter over quarter, driven by renewals.")

doc.add_heading("Headcount", level=2)
table = doc.add_table(rows=1, cols=2)
table.style = "Light Grid Accent 1"
header_cells = table.rows[0].cells
header_cells[0].text = "Department"
header_cells[1].text = "Headcount"
for department, headcount in [("Engineering", 42), ("Sales", 18)]:
    row_cells = table.add_row().cells
    row_cells[0].text = department
    row_cells[1].text = str(headcount)

disclaimer = doc.add_paragraph("Generated report - internal use only")
disclaimer.runs[0].font.size = Pt(8)

doc.save("quarterly_summary.docx")
```

## Basic editing (own document, simple changes)

Modify `run.text` on an existing run to change wording while keeping its formatting (font, bold,
color, size). Deleting a paragraph or run and adding a new one loses that formatting, because the
new object starts with the style defaults instead of copying the old run's direct formatting.

```python
from docx import Document

doc = Document("draft.docx")

for paragraph in doc.paragraphs:
    for run in paragraph.runs:
        if "DRAFT" in run.text:
            run.text = run.text.replace("DRAFT", "FINAL")

doc.save("draft.docx")
```

A paragraph's visible text can be split across several runs (Word splits runs on formatting
changes, spell-check markers, and edit history), so a search string can straddle a run boundary.
Check `paragraph.text` to find matches, then edit the specific run(s) that contain the text; when a
match spans multiple runs, edit each run's slice in place rather than concatenating and
reassigning `paragraph.text` (that attribute is read-only in `python-docx`).

## Redlining workflow (someone else's document, or legal/academic/business/government docs)

This is the required workflow for editing a document you do not own, or any legal, academic,
business, or government document, regardless of how small the change is. Silently rewriting text
in someone else's document removes their ability to see what changed and reject it; tracked
changes preserve that review.

`python-docx` has no API for tracked changes, so this happens at the raw XML level:

1. Unpack the `.docx` (a zip archive) to a working directory.
2. Edit `word/document.xml` directly: wrap inserted text in a `<w:ins>` element and wrap deleted
   text in a `<w:del>` element (with the deleted run's `<w:t>` changed to `<w:delText>`), each
   carrying `w:id`, `w:author`, and `w:date` attributes so Word can attribute and date the change.
3. Repack the zip, preserving the original archive's entries and order so Word does not treat the
   file as corrupted.

Read `references/tracked-changes.md` before doing this; it has the full XML shapes, the
attribute rules, and the exact repacking steps that keep the archive valid.

## Comments

Comments use the same raw-XML approach as redlining: a new `word/comments.xml` part holds the
comment text, and `word/document.xml` is marked up with `<w:commentRangeStart>` /
`<w:commentRangeEnd>` around the commented text plus a `<w:commentReference>` run. Adding the part
also requires a relationship entry and a content-type declaration, or Word won't discover it.
`references/tracked-changes.md` covers the full mechanism, including those two entries.

## Constraints

### MUST DO

- Preserve the document's existing formatting and template conventions (styles, fonts, table
  styles) when editing; match what is already there rather than introducing new styles.
- Verify extracted text against the source document before treating it as ground truth. Tables,
  headers/footers, and text boxes live outside `doc.paragraphs` and are easy to miss.
- Use the redlining workflow for any document you do not own, or any legal, academic, business, or
  government document, even for a one-word change.

### MUST NOT DO

- Don't delete and recreate a run or paragraph to change its text when the run already exists;
  edit `run.text` in place instead, or the formatting is lost.
- Don't write `<w:ins>` / `<w:del>` (or comment) XML from memory or by guessing the shape; read
  `references/tracked-changes.md` first and follow it.
- Don't silently drop tables, images, or other non-paragraph content when reading a document and
  rewriting it; account for everything the source contains or flag what could not be preserved.

## Quick Reference

| Task                                   | API                                    |
|----------------------------------------|----------------------------------------|
| Open an existing document              | `Document(path)`                       |
| Create a new document                  | `Document()`                           |
| Iterate paragraphs                     | `doc.paragraphs`                       |
| Iterate tables                         | `doc.tables`                           |
| Add a heading                          | `doc.add_heading(text, level)`         |
| Add a paragraph                        | `doc.add_paragraph(text, style=None)`  |
| Add a run to a paragraph               | `paragraph.add_run(text)`              |
| Add a table                            | `doc.add_table(rows, cols)`            |
| Save the document                      | `doc.save(path)`                       |
| Change text without losing formatting  | `run.text = "new text"`                |
