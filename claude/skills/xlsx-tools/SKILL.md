---
name: xlsx-tools
description: Use when creating, reading, editing, or analyzing Excel spreadsheets (.xlsx/.xlsm) - formulas, formatting, multiple sheets, or data extraction.
---

# Xlsx Tools

## Overview

`openpyxl` reads and writes `.xlsx`/`.xlsm` files directly against the underlying zip/XML format,
with no Excel or LibreOffice installation required.

## Critical gotcha: `data_only`

`load_workbook(path, data_only=True)` returns the last *cached* calculated value for a formula
cell, not a freshly computed one. That cache is written by whatever application last saved the
file after evaluating it; if the file was produced or last saved by a script rather than opened in
a real spreadsheet application, the cache is empty and every formula cell reads back as `None`.
`data_only=False` (the default) returns the formula string itself (e.g. `"=A2*B2"`) regardless of
any cached value.

`openpyxl` has no formula engine: it cannot calculate a result from a formula, only read one back
if something else already calculated it. Never claim a formula "works" or report its numeric
result based on reading it back with `openpyxl` alone; verify by opening the file in Excel or
LibreOffice, or by running the formula through a dedicated evaluation library.

## Reading and analyzing data

`load_workbook()` returns a workbook; `wb.sheetnames` lists its sheets by name, and
`wb[sheet_name]` selects one. Iterate rows with `ws.iter_rows()` or address a single cell with
`ws['A1'].value`.

```python
from openpyxl import load_workbook

wb = load_workbook("report.xlsx", data_only=True)
print(wb.sheetnames)

ws = wb["Sales"]
print(ws["B2"].value)

for row in ws.iter_rows(min_row=1, max_row=5, values_only=True):
    print(row)
```

## Creating a new spreadsheet

`Workbook()` starts a blank workbook with one default sheet. Build rows with `ws.append()` for
whole rows or `ws['A1'] = value` for individual cells, then `wb.save()`.

```python
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "Inventory"

ws.append(["Item", "Quantity", "Unit Price"])
ws.append(["Widget", 100, 2.50])
ws.append(["Gadget", 50, 9.99])

wb.save("inventory.xlsx")
```

## Editing existing files while preserving formatting

Load with `data_only=False` (the default) so formula cells round-trip as formula strings instead
of being silently replaced by a stale cached value or `None`. Modify individual cells directly by
reference (`ws['B2'] = 42`) and save back to the same path; cells you did not touch keep their
existing value, formula, and formatting.

```python
from openpyxl import load_workbook

wb = load_workbook("budget.xlsx")
ws = wb["Q1"]

ws["B2"] = 42
ws["C5"] = "Updated"

wb.save("budget.xlsx")
```

`openpyxl` preserves most cell formatting, styles, column widths, and formulas across a
load/save round-trip, but it can silently drop or corrupt advanced features on some files, such as
charts and some conditional formatting rules. Treat editing a file with rich formatting as a real
risk, not a hypothetical one, and open the saved file visually (Excel or LibreOffice) to confirm
nothing was lost whenever the source file has anything beyond plain cell values and basic styles.

## Writing formulas

Assign a formula string to a cell the same way you would assign any other value:

```python
ws["C2"] = "=A2*B2"
ws["C6"] = "=SUM(C2:C5)"
```

As with reading, `openpyxl` does not calculate these. The formula string is written into the file
as-is and will not show a computed result until the file is opened in a real spreadsheet
application, which then evaluates it and caches the result.

## Constraints

### MUST DO

- Use `data_only=False` (the default) when the goal is to preserve or edit formulas; using
  `data_only=True` on that same load silently discards the formula strings, returning only their
  cached value or `None`.
- Use `data_only=True` only when reading already-calculated results, and only from a file that has
  been opened and saved in a real spreadsheet application since its formulas last changed.
- Verify sheet names against `wb.sheetnames` before referencing one; never assume a sheet is named
  `Sheet1` or that the first sheet is the relevant one.

### MUST NOT DO

- Never claim a formula's numeric result is correct based on reading it back with `openpyxl`;
  state plainly that it is unverified without opening the file in a real spreadsheet application or
  running it through a formula-evaluation library.
- Don't overwrite an entire sheet (rebuilding it from scratch) when only a few cells changed;
  editing the specific cells in place preserves every value, formula, and style you didn't touch.
