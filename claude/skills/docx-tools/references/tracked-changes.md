# Tracked changes and comments (raw OOXML)

`python-docx` reads and writes `word/document.xml` through its object model, but that model has no
concept of an insertion or deletion mark, and no concept of a comment. Both features are
represented as extra XML elements that `python-docx` never generates or parses. Producing them
means opening the `.docx` as a zip archive and editing the XML parts by hand.

## Unpacking

A `.docx` is a standard zip archive. Extract it to inspect or edit the parts:

```sh
python -m zipfile -e file.docx unpacked/
# or
unzip file.docx -d unpacked/
```

The parts that matter here:

| Part                           | Holds                                                     |
|--------------------------------|-----------------------------------------------------------|
| `word/document.xml`            | The body: paragraphs, runs, tables, and the redline marks |
| `word/comments.xml`            | Comment text (does not exist until a document has one)    |
| `word/_rels/document.xml.rels` | Relationship from the document to `comments.xml`          |
| `[Content_Types].xml`          | Declares the content type of `comments.xml`               |

Do not edit the extracted directory and hand it back as the deliverable; a `.docx` is the zip
archive, not the directory. See Repacking below for turning the edits back into a valid file.

## Tracked insertions and deletions

Word represents an inserted run by wrapping it in `<w:ins>`, and a deleted run by wrapping it in
`<w:del>` with its text element changed from `<w:t>` to `<w:delText>`. Both elements require three
attributes:

| Attribute  | Meaning                                                                           |
|------------|-----------------------------------------------------------------------------------|
| `w:id`     | Unique integer within the document; increment past any `w:id` already in the file |
| `w:author` | Name shown in Word's reviewer list and in the change's tooltip                    |
| `w:date`   | ISO 8601 UTC timestamp, e.g. `2026-09-16T10:00:00Z`                               |

### Inserting text

Original paragraph:

```xml
<w:p>
  <w:r><w:t>The vendor will deliver the goods within 30 days.</w:t></w:r>
</w:p>
```

With "business" inserted before "days", split the run at the insertion point and wrap the new text
in `<w:ins>`:

```xml
<w:p>
  <w:r><w:t xml:space="preserve">The vendor will deliver the goods within 30 </w:t></w:r>
  <w:ins w:id="101" w:author="Reviewer Name" w:date="2026-09-16T10:00:00Z">
    <w:r><w:t xml:space="preserve">business </w:t></w:r>
  </w:ins>
  <w:r><w:t>days.</w:t></w:r>
</w:p>
```

`xml:space="preserve"` is required whenever a run's text has a leading or trailing space, or Word
readers may collapse it.

### Deleting text

To delete "30" and replace it with "60", wrap the removed run in `<w:del>` and change its `<w:t>`
to `<w:delText>`, then insert the replacement immediately after in a `<w:ins>`:

```xml
<w:p>
  <w:r><w:t xml:space="preserve">The vendor will deliver the goods within </w:t></w:r>
  <w:del w:id="102" w:author="Reviewer Name" w:date="2026-09-16T10:00:00Z">
    <w:r><w:delText>30</w:delText></w:r>
  </w:del>
  <w:ins w:id="103" w:author="Reviewer Name" w:date="2026-09-16T10:00:00Z">
    <w:r><w:t>60</w:t></w:r>
  </w:ins>
  <w:r><w:t xml:space="preserve"> days.</w:t></w:r>
</w:p>
```

A run inside `<w:del>` must use `<w:delText>`; a `<w:t>` inside a `<w:del>` is invalid and some
Word versions will refuse to render the change as tracked.

`w:id` values must be unique within the document; before adding new ones, find the highest
existing `w:id` (searching all of `w:ins`, `w:del`, and `w:comment*` elements) and continue from
there.

## Comments

A comment needs three pieces, all consistent with each other by `w:id`.

**1. `word/comments.xml`** (create it if the document has no comments yet):

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:comment w:id="0" w:author="Reviewer Name" w:date="2026-09-16T10:00:00Z" w:initials="RN">
    <w:p><w:r><w:t>Confirm this figure with finance before sending.</w:t></w:r></w:p>
  </w:comment>
</w:comments>
```

**2. The commented range in `word/document.xml`**, marking the start and end of the text the
comment applies to, and a reference run at the end that Word renders as the comment balloon:

```xml
<w:p>
  <w:commentRangeStart w:id="0"/>
  <w:r><w:t>Revenue grew 12%</w:t></w:r>
  <w:commentRangeEnd w:id="0"/>
  <w:r>
    <w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>
    <w:commentReference w:id="0"/>
  </w:r>
</w:p>
```

**3. Wiring so Word discovers the new part:**

- `word/_rels/document.xml.rels` needs a relationship entry:

  ```xml
  <Relationship Id="rIdComments" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/>
  ```

- `[Content_Types].xml` needs an override so the part is recognized as comments, not generic XML:

  ```xml
  <Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>
  ```

Skipping either entry leaves `comments.xml` an orphaned part: Word opens the file without error but
never shows the comment.

## Repacking

A `.docx` with reordered, added, or recompressed zip entries can become unreadable by Word even
though every individual part is valid XML. Do not extract to a directory and then rezip the
directory (`zip -r out.docx unpacked/*`, `shutil.make_archive`, or similar): that produces a fresh
archive with its own entry order and adds directory entries the original never had.

Instead, update the existing archive in place: read every entry from the original zip, keep the
untouched ones byte-for-byte, and only replace the bytes of the parts that changed.

```python
import shutil
import zipfile

SOURCE = "contract.docx"
MODIFIED_PARTS = {
    "word/document.xml": new_document_xml_bytes,
    "word/comments.xml": new_comments_xml_bytes,
    "word/_rels/document.xml.rels": new_rels_xml_bytes,
    "[Content_Types].xml": new_content_types_xml_bytes,
}

shutil.copyfile(SOURCE, SOURCE + ".bak")

with zipfile.ZipFile(SOURCE, "r") as src:
    entries = src.infolist()
    original_bytes = {info.filename: src.read(info.filename) for info in entries}

with zipfile.ZipFile(SOURCE + ".tmp", "w", zipfile.ZIP_DEFLATED) as dst:
    for info in entries:
        data = MODIFIED_PARTS.get(info.filename, original_bytes[info.filename])
        dst.writestr(info, data)

shutil.move(SOURCE + ".tmp", SOURCE)
```

Writing with `dst.writestr(info, data)` (the original `ZipInfo`, not just the filename) keeps each
entry's compression type and metadata, and iterating `entries` in their original order keeps the
archive's structure exactly as Word produced it, changed only where it needed to change.

If `word/comments.xml` did not exist in the source document, add it to the archive with a new
`ZipInfo` in the same write pass rather than as a separate step, so the whole file is written once.
