---
name: pdf-tools
description: Use when extracting text or tables from PDF files, creating new PDFs, merging or splitting PDF documents, or filling PDF form fields.
---

# PDF Tools

## Overview

Three libraries cover three different jobs: `pypdf` handles structural operations (reading pages,
merging, splitting, and form fields) because it works directly with the PDF object model;
`pdfplumber` handles table extraction because it reconstructs table structure from character and
line positions instead of returning a flat text stream; `reportlab` generates new PDFs from
scratch, since none of the other two can write pages.

## Reading and extracting text

`pypdf.PdfReader` loads a file and exposes its pages through `reader.pages`. Each page's
`extract_text()` returns the text pypdf can recover from that page's content stream.

```python
from pypdf import PdfReader

reader = PdfReader("report.pdf")

for page_number, page in enumerate(reader.pages):
    text = page.extract_text()
    print(f"--- page {page_number} ---")
    print(text)
```

`extract_text()` walks the content stream in the order text-drawing operators appear in the file,
not necessarily left-to-right, top-to-bottom reading order. For a single-column document the two
usually coincide; they do not for multi-column layouts (see Constraints).

## Extracting tables

`pypdf`'s `extract_text()` returns a flat string; the spacing between columns is whatever the PDF's
text-drawing operators produced, which does not reliably map back onto rows and columns. Use
`pdfplumber` instead: it looks at the actual character positions and any ruling lines on the page
and reconstructs the table grid, returning each table as a list of rows.

```python
import pdfplumber

with pdfplumber.open("invoice.pdf") as pdf:
    for page_number, page in enumerate(pdf.pages):
        for table in page.extract_tables():
            print(f"--- page {page_number} ---")
            for row in table:
                print(row)
```

A cell with no text extracts as `None`, not an empty string; check for both when reading the result.
`extract_tables()` finds tables by detecting ruling lines or aligned whitespace, so it can miss a
table that has neither (for example, one laid out with only vertical spacing). Pass a
`table_settings` dict (`vertical_strategy`, `horizontal_strategy`) when the default detection misses
or over-splits a table; see the `pdfplumber` documentation for the available strategies.

## Creating new PDFs

Reach for `reportlab.pdfgen.canvas.Canvas` when the layout is simple and you are placing text,
lines, or shapes at fixed coordinates yourself (a label, a single-page certificate, a form
overlay). Reach for `reportlab.platypus` when the document has multiple sections that need to flow
and reflow automatically (headings, paragraphs, and tables that must wrap and paginate on their
own) since platypus lays elements out for you instead of requiring manual coordinates.

```python
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

doc = SimpleDocTemplate("summary.pdf", pagesize=letter)
styles = getSampleStyleSheet()

elements = [
    Paragraph("Quarterly Summary", styles["Title"]),
    Spacer(1, 12),
    Paragraph("Revenue grew 12% quarter over quarter, driven by renewals.", styles["BodyText"]),
    Spacer(1, 12),
]

data = [["Department", "Headcount"], ["Engineering", "42"], ["Sales", "18"]]
table = Table(data, colWidths=[2 * inch, 2 * inch])
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
]))
elements.append(table)

doc.build(elements)
```

## Merging and splitting

Both operations go through `pypdf.PdfWriter`. Merging feeds `add_page()` pages from more than one
`PdfReader`, in the order they should appear in the output:

```python
from pypdf import PdfReader, PdfWriter

writer = PdfWriter()
for path in ("chapter1.pdf", "chapter2.pdf"):
    reader = PdfReader(path)
    for page in reader.pages:
        writer.add_page(page)
with open("combined.pdf", "wb") as f:
    writer.write(f)
```

Splitting feeds `add_page()` a slice of one reader's `pages` instead of all of them:

```python
reader = PdfReader("combined.pdf")
writer = PdfWriter()
for page in reader.pages[0:3]:
    writer.add_page(page)
with open("first_three.pdf", "wb") as f:
    writer.write(f)
```

`reader.pages` supports normal Python slicing, so `reader.pages[-1]` is the last page and
`reader.pages[::2]` is every other page.

## Filling PDF forms

The critical rule: never guess a form's field names. Call `reader.get_fields()` first and read the
names it returns; a name you assume from the visible label (`"Full Name"` instead of the field's
actual internal name `full_name`) silently fails to fill anything.

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("application.pdf")
for name, field in reader.get_fields().items():
    print(name, field.field_type, field.value)

writer = PdfWriter()
writer.append(reader)
writer.set_need_appearances_writer(True)
writer.update_page_form_field_values(
    writer.pages[0],
    {"full_name": "Ada Lovelace"},
)
with open("application_filled.pdf", "wb") as f:
    writer.write(f)
```

That covers a plain text field. Checkboxes and radio buttons take their field's export value
(discovered from `get_fields()`, not a plain `True`/`False`), and skipping
`set_need_appearances_writer(True)` leaves the values in the saved file invisible until a user
clicks into each field. Read `references/form-filling.md` before filling any form that has
checkboxes, radio buttons, or choice fields.

## Constraints

### MUST DO

- Call `reader.get_fields()` before filling any form field, every time, even on a form you filled
  before; a template can change its field names between versions.
- Verify extracted text against the actual PDF content rather than trusting it outright.
  `extract_text()` on a scanned or image-based PDF returns little or no text because there is no
  text layer to extract from, not because the extraction failed; flag that case instead of treating
  an empty or near-empty result as "the document is blank."

### MUST NOT DO

- Don't guess a form field's name or type. A label visible in the PDF viewer is not the field's
  internal name, and treating a checkbox's export value as a Python boolean writes the wrong value.
- Don't assume `pypdf`'s `extract_text()` preserves reading order on a multi-column layout; it
  follows the order of drawing operators in the content stream, which can interleave columns.
  Verify against the source for any document that is not single-column.
- Don't silently drop pages during a merge or split. Compare the input and output page counts
  (`len(reader.pages)` before and after) and confirm the result matches what was expected.
