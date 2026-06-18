# Tool: macOS document conversion (docx / md / pdf with images)

Reusable pipeline for turning Markdown/HTML into shareable docs on this mac. No client specifics.

## Key gotcha
- **`textutil` drops images.** `textutil -convert docx in.html -output out.docx` produces a valid docx but
  with **no embedded images** (no `word/media/` in the result). Fine for text/tables, useless when figures
  must be inline. Verify with `unzip -l out.docx | grep media`.

## Image-rich output → use headless Chrome (installed; pandoc/libreoffice/wkhtmltopdf are NOT by default)
```
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --no-pdf-header-footer --print-to-pdf="out.pdf" "file:///abs/path/in.html"
```
Chrome embeds images referenced by **absolute `file://`** URLs. Relative `src="mockups/x.png"` won't resolve
in headless — rewrite to `file:///abs/.../mockups/x.png` before rendering.

## Markdown → PDF (with inline images)
- `python3 -m pip install markdown` (not preinstalled). Convert with extensions `tables,fenced_code,sane_lists,toc`.
- Concatenate sections, wrap in a `<style>` with `@page{size:A4;margin:...}` and `section{page-break-before:always}`
  for clean page breaks; style `table`/`img`/`blockquote`.
- Rewrite relative image `src` to absolute `file://`, write `_combined.html`, then run the Chrome command above.
- For GitHub issues, keep the Markdown as canonical (images render once attached/committed); PDF is the
  human-review copy.

## Other handy one-liners
- Read a `.docx` as text: `textutil -convert txt in.docx -output out.txt`
- Extract images embedded in a `.docx` (it's a zip): `unzip -o in.docx 'word/media/*'`
- docx → docx-with-images **does** work via pandoc if you `brew install pandoc` first.
