---
name: pptx-tools
description: Use when creating, reading, editing, or analyzing PowerPoint presentations (.pptx) - slide content, layouts, speaker notes, or comments.
---

# Pptx Tools

## Overview

A `.pptx` file is a zip archive of XML parts, like `.docx`. `python-pptx` covers slide content,
layouts, and speaker notes natively through its object model, but it has no API for comments, so
those require editing the raw XML.

## Reading and analyzing content

Open the file with `Presentation(path)` and iterate `prs.slides`, then each slide's `slide.shapes`.
Not every shape carries text (images and some connectors do not), so check `shape.has_text_frame`
before reading `shape.text_frame.text`.

```python
from pptx import Presentation

prs = Presentation("deck.pptx")

for slide_index, slide in enumerate(prs.slides):
    print(f"--- Slide {slide_index + 1} ---")
    for shape in slide.shapes:
        if shape.has_text_frame and shape.text_frame.text.strip():
            print(shape.text_frame.text)
```

`shape.text_frame.text` joins a text box's paragraphs with newlines; it does not include text
inside tables (`shape.table`) or charts, which need their own walk when those matter.

## Creating a new presentation

Call `Presentation()` with no path to start from the built-in template, pick a layout from
`prs.slide_layouts`, add a slide with `prs.slides.add_slide(layout)`, and fill its placeholders by
setting `slide.placeholders[idx].text`.

```python
from pptx import Presentation

prs = Presentation()

title_slide = prs.slides.add_slide(prs.slide_layouts[0])
title_slide.placeholders[0].text = "Quarterly Summary"
title_slide.placeholders[1].text = "Engineering and Sales"

content_slide = prs.slides.add_slide(prs.slide_layouts[1])
content_slide.placeholders[0].text = "Revenue"
body = content_slide.placeholders[1].text_frame
body.text = "Grew 12% quarter over quarter"
body.add_paragraph().text = "Driven by renewals"

prs.save("quarterly_summary.pptx")
```

The built-in template's layout indices (0 = Title Slide, 1 = Title and Content, and so on) come
from `prs.slide_layouts`; a template supplied by the user can order or name its layouts
differently, so inspect `prs.slide_layouts` rather than assuming the index.

## Editing existing slides

Modify `run.text` on an existing run in a `text_frame` to change wording while keeping its
formatting (font, bold, color, size), the same principle as `docx-tools`' editing gotcha. Deleting
a paragraph or run and adding a new one loses that formatting, because the new object starts with
the style defaults instead of copying the old run's direct formatting.

```python
from pptx import Presentation

prs = Presentation("deck.pptx")

for slide in prs.slides:
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                if "DRAFT" in run.text:
                    run.text = run.text.replace("DRAFT", "FINAL")

prs.save("deck.pptx")
```

A text frame's visible text can be split across several runs (PowerPoint splits runs on formatting
changes and spell-check markers), so a search string can straddle a run boundary. Check
`paragraph.text` to find matches, then edit the specific run(s) that contain the text.

## Speaker notes

`python-pptx` supports speaker notes natively through `slide.notes_slide`. A slide has no notes
part until one is requested; reading or writing `notes_slide` creates it if it does not already
exist.

```python
from pptx import Presentation

prs = Presentation("deck.pptx")
slide = prs.slides[0]

notes_frame = slide.notes_slide.notes_text_frame
print(notes_frame.text)

notes_frame.text = "Open with the revenue chart before taking questions."
prs.save("deck.pptx")
```

`slide.has_notes_slide` checks for existing notes without creating a part as a side effect, useful
when scanning many slides and only some have notes.

## Comments

Comments are review annotations, not presenter notes, and `python-pptx` has no API for them: a
comment lives in its own `ppt/comments/modernComment_<N>.xml` part, author identities live
separately in `ppt/authors.xml`, and the slide points to its comment part through a relationship
buried inside the slide XML's own extension list, not a plain top-level relationship the way
`docx` comments work. Read `references/comments-and-notes.md` before touching any of this; it has
the full part layout and the exact repacking steps that keep the archive valid.

## Constraints

### MUST DO

- Preserve the presentation's existing layout and theme conventions when editing; match what a
  slide's layout already provides (placeholders, fonts, color scheme) rather than introducing new
  ones.
- Verify slide count and text content against the source presentation after any read-modify-write
  round-trip; a save that silently drops a shape or a slide is easy to miss otherwise.

### MUST NOT DO

- Don't clear and recreate a `text_frame`'s paragraphs to change its text if only the words
  changed; that loses run-level formatting like bold, italic, and color. Edit `run.text` in place
  instead.
- Don't assume every placeholder index exists on every layout. A layout only defines the
  placeholders it was designed with, so index into `slide.placeholders` only after confirming that
  index is present, not by copying an index that worked on a different layout.
