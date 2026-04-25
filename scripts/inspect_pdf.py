#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import fitz


def parse_pages(value: str, page_count: int) -> list[int]:
    pages: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start, end = [int(item) for item in part.split("-", 1)]
            except ValueError as exc:
                raise ValueError(f"bad page range: {part}") from exc
            pages.update(range(start, end + 1))
        else:
            try:
                pages.add(int(part))
            except ValueError as exc:
                raise ValueError(f"bad page number: {part}") from exc
    selected = [page for page in sorted(pages) if 1 <= page <= page_count]
    if not selected:
        raise ValueError("no selected pages exist in PDF")
    return selected


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u00ad", "")
    value = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n.-")


def print_metadata(doc: fitz.Document) -> None:
    print("metadata:")
    for key in ("title", "author", "subject", "keywords", "creator", "producer", "creationDate", "modDate"):
        value = clean_text((doc.metadata or {}).get(key))
        if value:
            print(f"  {key}: {value}")


def print_page_text(doc: fitz.Document, page_number: int, *, sort: bool) -> None:
    text = doc.load_page(page_number - 1).get_text("text", sort=sort)
    print(f"\npage {page_number} text sort={str(sort).lower()}:")
    for line in (clean_text(line) for line in text.splitlines()):
        if line:
            print(line)


def render_page(doc: fitz.Document, pdf_path: Path, page_number: int, out_dir: Path, dpi: int) -> None:
    scale = dpi / 72
    pix = doc.load_page(page_number - 1).get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    out = out_dir / f"{pdf_path.stem}_page_{page_number:03d}.png"
    pix.save(out)
    print(f"rendered: {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect PDF metadata, text, and optionally rendered pages.")
    parser.add_argument("pdf")
    parser.add_argument("--pages", default="1", help="Pages like 1, 1-5, or 1,5.")
    parser.add_argument("--sort", choices=("false", "true", "both"), default="both")
    parser.add_argument("--render", action="store_true", help="Also render selected pages to PNG.")
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    if args.dpi <= 0:
        raise SystemExit("--dpi must be greater than 0")

    path = Path(args.pdf).expanduser().resolve()
    if not path.exists() or path.suffix.lower() != ".pdf":
        raise SystemExit(f"not a PDF: {path}")

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else path.parent / ".pdf_inspect"
    if args.render:
        out_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise SystemExit(f"cannot open PDF: {exc}") from exc

    with doc:
        try:
            pages = parse_pages(args.pages, doc.page_count)
        except ValueError as exc:
            raise SystemExit(f"invalid --pages: {exc}") from exc

        print(f"pdf: {path}")
        print(f"pages: {doc.page_count}")
        print_metadata(doc)
        for page in pages:
            if args.sort in ("false", "both"):
                print_page_text(doc, page, sort=False)
            if args.sort in ("true", "both"):
                print_page_text(doc, page, sort=True)
            if args.render:
                render_page(doc, path, page, out_dir, args.dpi)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
