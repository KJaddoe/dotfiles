# Form filling walkthrough

## Discover the fields first

`reader.get_fields()` returns a dictionary keyed by each field's internal name, with a
`pypdf.generic.Field` object as the value. Never fill a field by the label printed next to it on
the page; that label is not stored anywhere the PDF format treats as the field's identity, and a
form's designer is free to name the field something unrelated.

```python
from pypdf import PdfReader

reader = PdfReader("application.pdf")
fields = reader.get_fields()

for name, field in fields.items():
    print(f"{name}: type={field.field_type} value={field.value!r}")
```

`field.field_type` is one of three values, and each implies a different fill shape:

| Value  | Meaning                        | Fill with                                                |
|--------|--------------------------------|----------------------------------------------------------|
| `/Tx`  | Text field                     | A plain string                                           |
| `/Btn` | Checkbox or radio button group | The field's export value (see below), not `True`/`False` |
| `/Ch`  | Choice field (dropdown/list)   | One of the field's `/Opt` option strings                 |

A `/Btn` field can be either a single checkbox or a set of mutually exclusive radio buttons; both
share the same field type, and both are filled the same way: with an export value string, not a
boolean.

## Checkboxes and radio buttons need the export value, not a boolean

A checkbox has no inherent "true" or "false" string; the PDF spec lets the form's author choose
whatever name the checked state uses. That name lives in the checkbox widget's `/AP` (appearance)
dictionary, under `/N` (the normal appearance), as a key alongside `/Off`:

```python
reader = PdfReader("application.pdf")
page = reader.pages[0]

for annot in page["/Annots"]:
    widget = annot.get_object()
    if widget.get("/FT") == "/Btn":
        states = list(widget["/AP"]["/N"].keys())
        print(widget["/T"], "states:", states)
```

For a plain checkbox this prints something like `subscribe states: ['/Off', '/Yes']`; the export
value to write is whatever appears alongside `/Off` (`/Yes` here, but a form can name it anything,
such as `/On` or `/1`). For a radio button group, each button in the group typically shares one
`/On`-style value per button, and setting the group's field to that value selects that button while
clearing the others in the same group.

Pass that export value, as a string, in the mapping given to `update_page_form_field_values()`:

```python
writer.update_page_form_field_values(writer.pages[0], {"subscribe": "/Yes"})
```

Writing `{"subscribe": True}` does not fail loudly; it simply does not match any of the checkbox's
known appearance states, so the checkbox renders unchecked (or unchanged) in the saved file.

## Set NeedAppearances so viewers actually render the values

By default, a PDF viewer is allowed to reuse a field's cached appearance stream instead of
regenerating it from the value pypdf just wrote. On many viewers this means a filled field looks
blank until the user clicks into it, because the cached appearance (built for the old, empty value)
never gets rebuilt automatically. Setting the `/NeedAppearances` flag on the document's `AcroForm`
dictionary tells every conforming viewer to regenerate every field's appearance from its current
value when the document opens, so the filled text and checkboxes are visible immediately.

```python
writer = PdfWriter()
writer.append(reader)
writer.set_need_appearances_writer(True)
```

Call this once per `PdfWriter`, before or after `update_page_form_field_values()`; it sets a flag on
the writer's `AcroForm` object, not on an individual field.

## Choice fields

A `/Ch` field's valid values are listed in its `/Opt` array (or, for the raw field dict from
`get_fields()`, under the `_States_`-style option lists pypdf exposes). Fill it the same way as a
text field, `update_page_form_field_values(page, {field_name: option_string})`, but only with a
string that actually appears in `/Opt`; a value outside that list does not raise an error, it just
leaves the field showing nothing selected.

## When pypdf cannot fill a form cleanly

`pypdf` fills standard AcroForm fields well. A form built as XFA (Adobe's XML Forms Architecture,
common in some government and enterprise PDF generators) stores its field data in an embedded XML
packet that pypdf does not fill; the AcroForm fields on an XFA-hybrid document can end up out of
sync with the XFA data the viewer actually renders. For that case, `PyPDFForm` is a fallback library
purpose-built for form filling, including some XFA and more complex widget layouts pypdf does not
handle. Reach for it only after confirming `update_page_form_field_values()` genuinely fails or
produces a mismatched result, not as a default replacement for pypdf.
