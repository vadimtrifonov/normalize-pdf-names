---
name: normalize-pdf-names
description: Rename PDFs using the work’s author, year, and title. Use to normalize PDF filenames.
---

# Normalize PDF Names

Run all commands from this skill directory.

## Inspect

Inspect first:

```bash
mise inspect file.pdf --pages 1
```

If page 1 is readable but missing needed evidence:

```bash
mise inspect file.pdf --pages 1-5 --sort false
```

If page text is split, out of order, or missing visible header details:

```bash
mise inspect file.pdf --pages 1-5 --sort true
```

If needed, inspect the next likely front-matter pages.
Render only when extracted text is missing or garbled. Rendered files go to `.pdf_inspect/` and are removed by `rename_pdf.py`.

```bash
mise inspect file.pdf --pages 1 --render
```

## Rename

Prefer journal publication year if clearly given.
After deciding first author, year, and title:

```bash
mise rename file.pdf \
  --author "First Author" \
  --year 1992 \
  --title "Title: Subtitle"
```

`rename_pdf.py` formats the filename as `first_author_surname_year_short_title.pdf`, strips standalone `the`, `a`, and `an`, and handles collisions.
