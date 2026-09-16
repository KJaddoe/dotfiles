# Comments (raw OOXML)

`python-pptx` reads and writes slide XML through its object model, but that model has no concept
of a review comment. Current PowerPoint writes comments as a set of separate XML parts (Microsoft
calls this "modern comments"), and producing or editing one means opening the `.pptx` as a zip
archive and editing those parts by hand.

## Unpacking

A `.pptx` is a standard zip archive. Extract it to inspect or edit the parts:

```sh
python -m zipfile -e file.pptx unpacked/
# or
unzip file.pptx -d unpacked/
```

The parts that matter here:

| Part                                  | Holds                                                            |
|---------------------------------------|------------------------------------------------------------------|
| `ppt/slides/slideN.xml`               | The slide body, and the pointer to its comment part              |
| `ppt/slides/_rels/slideN.xml.rels`    | The relationship the slide's pointer resolves through            |
| `ppt/comments/modernComment_<N>.xml`  | One comment part's `cm` elements (its text, position, replies)   |
| `ppt/authors.xml`                     | Author identities shared by every comment in the file            |
| `[Content_Types].xml`                 | Declares the content type of each new part                       |

Do not edit the extracted directory and hand it back as the deliverable; a `.pptx` is the zip
archive, not the directory. See Repacking below for turning the edits back into a valid file.

## Comment parts

Each comment part is a `cmLst` (a list of comments) containing one or more `cm` elements:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p188:cmLst xmlns:p188="http://schemas.microsoft.com/office/powerpoint/2018/8/main">
  <p188:cm id="{62A8A96D-E5A8-4BFC-B993-A6EAE3907CAD}"
           authorId="{F5C2E01A-9B3D-4C87-A6E2-3B7C1F805AD9}"
           created="2026-09-16T10:00:00.000">
    <p188:pos x="1426" y="660"/>
    <p188:txBody>
      <a:bodyPr/>
      <a:p><a:r><a:t>Confirm this figure with finance before sending.</a:t></a:r></a:p>
    </p188:txBody>
  </p188:cm>
</p188:cmLst>
```

| Attribute/element | Meaning                                                                          |
|-------------------|----------------------------------------------------------------------------------|
| `id`              | GUID identifying this comment, unique within the file                            |
| `authorId`        | GUID matching an `author` element's `id` in `ppt/authors.xml`                    |
| `created`         | ISO 8601 timestamp                                                               |
| `pos`             | Position relative to the top-left of the first shape the comment is anchored to  |
| `txBody`          | The comment's rich text, an `a:CT_TextBody` (the same shape used for slide text) |
| `replyLst`        | Threaded replies to this comment, each a `cm`-like element                       |

PowerPoint gives each comment part its own file, named `modernComment_1.xml`,
`modernComment_2.xml`, and so on; treat that numbering as PowerPoint's own bookkeeping. A comment
does not need a particular number to be valid, only one not already used in the file's
`[Content_Types].xml`.

## Author identities

`ppt/authors.xml` holds one `author` element per commenter, referenced by `authorId` from every
`cm` element they wrote:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p188:authorLst xmlns:p188="http://schemas.microsoft.com/office/powerpoint/2018/8/main">
  <p188:author id="{F5C2E01A-9B3D-4C87-A6E2-3B7C1F805AD9}"
               name="Reviewer Name"
               initials="RN"
               providerId="None"/>
</p188:authorLst>
```

A file has at most one `ppt/authors.xml`; every comment part references into that same list rather
than carrying its own copy of the author's name.

## Wiring: how a slide points at its comment part

Unlike `docx`, where a `<w:commentReference>` run sits directly in the paragraph it annotates, a
`.pptx` slide never references a comment part inline. The pointer lives in the slide's own
extension list:

```xml
<p:sld ...>
  ...
  <p:extLst>
    <p:ext uri="{6950BFC3-D8DA-4A85-94F7-54DA5524770B}">
      <p188:commentRel r:id="rIdComment1"/>
    </p:ext>
  </p:extLst>
</p:sld>
```

`r:id` is an ordinary relationship id, resolved the same way any other slide relationship is: look
it up in `ppt/slides/_rels/slideN.xml.rels`:

```xml
<Relationship Id="rIdComment1"
              Type="http://schemas.microsoft.com/office/2018/10/relationships/comments"
              Target="../comments/modernComment_1.xml"/>
```

So adding a comment to a slide touches four things, all consistent with each other: the new
`modernComment_<N>.xml` part, an `author` entry in `ppt/authors.xml` (reuse an existing one by
`id` if the commenter already has one), the relationship entry in the slide's `.rels` file, and the
`commentRel` extension inside `<p:sld><p:extLst>`. `[Content_Types].xml` also needs an Override for
the new comment part (and for `ppt/authors.xml` if the file had no comments before):

```xml
<Override PartName="/ppt/comments/modernComment_1.xml" ContentType="application/vnd.ms-powerpoint.comments+xml"/>
<Override PartName="/ppt/authors.xml" ContentType="application/vnd.ms-powerpoint.authors+xml"/>
```

Skipping any one of these four leaves the comment orphaned: PowerPoint opens the file without
error but never shows it.

## How this differs from speaker notes

Speaker notes and comments are unrelated features that are easy to conflate because both are
"extra text attached to a slide that the audience never sees":

- Notes are content for the presenter to read while presenting: one `notesSlideN.xml` part per
  slide, laid out with its own placeholders, fully modeled by `python-pptx` through
  `slide.notes_slide`. See the main `SKILL.md` for reading and writing them.
- Comments are review annotations addressed to other people editing the file, anchored to a
  position (or a shape or text range) rather than replacing slide content, and never rendered
  during a slide show or in Presenter View's notes pane. `python-pptx` has no object model for
  them at all, so they only exist at the raw XML level described above.

## Repacking

A `.pptx` with reordered, added, or recompressed zip entries can become unreadable by PowerPoint
even though every individual part is valid XML. Do not extract to a directory and then rezip the
directory (`zip -r out.pptx unpacked/*`, `shutil.make_archive`, or similar): that produces a fresh
archive with its own entry order and adds directory entries the original never had.

Instead, update the existing archive in place: read every entry from the original zip, keep the
untouched ones byte-for-byte, and only replace or add the parts that changed.

```python
import shutil
import zipfile

SOURCE = "deck.pptx"
MODIFIED_PARTS = {
    "ppt/slides/slide1.xml": new_slide_xml_bytes,
    "ppt/slides/_rels/slide1.xml.rels": new_slide_rels_bytes,
    "ppt/comments/modernComment_1.xml": new_comment_xml_bytes,
    "ppt/authors.xml": new_authors_xml_bytes,
    "[Content_Types].xml": new_content_types_xml_bytes,
}

shutil.copyfile(SOURCE, SOURCE + ".bak")

with zipfile.ZipFile(SOURCE, "r") as src:
    entries = src.infolist()
    original_bytes = {info.filename: src.read(info.filename) for info in entries}

existing_names = {info.filename for info in entries}
new_parts = {name: data for name, data in MODIFIED_PARTS.items() if name not in existing_names}

with zipfile.ZipFile(SOURCE + ".tmp", "w", zipfile.ZIP_DEFLATED) as dst:
    for info in entries:
        data = MODIFIED_PARTS.get(info.filename, original_bytes[info.filename])
        dst.writestr(info, data)
    for name, data in new_parts.items():
        dst.writestr(name, data)

shutil.move(SOURCE + ".tmp", SOURCE)
```

Writing with `dst.writestr(info, data)` (the original `ZipInfo`, not just the filename) keeps each
existing entry's compression type and metadata, and iterating `entries` in their original order
keeps the archive's structure exactly as PowerPoint produced it, changed only where it needed to
change. A comment part, `ppt/authors.xml`, and the slide's `.rels` file are often genuinely new, so
they get appended in the same write pass rather than as a separate step, so the whole file is
written once.
