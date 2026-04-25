#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import unicodedata
from pathlib import Path


ARTICLES = {"the", "a", "an"}
PARTICLES = {"da", "de", "del", "der", "di", "la", "le", "van", "von"}
MAX_TITLE_TOKENS = 18
MAX_STEM_CHARS = 180


def slug_tokens(value: str) -> list[str]:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return re.findall(r"[a-z0-9]+", value.lower())


def author_slug(author: str) -> str:
    tokens = slug_tokens(author.split(",", 1)[0])
    if not tokens:
        raise ValueError("author does not contain a usable name")
    surname = [tokens[-1]]
    index = len(tokens) - 2
    while index >= 0 and tokens[index] in PARTICLES:
        surname.insert(0, tokens[index])
        index -= 1
    return "_".join(surname)


def title_slug(title: str, *, full_title: bool) -> str:
    title_part = title if full_title else title.split(":", 1)[0]
    tokens = [token for token in slug_tokens(title_part) if token not in ARTICLES]
    if not tokens:
        tokens = [token for token in slug_tokens(title) if token not in ARTICLES]
    if not tokens:
        raise ValueError("title does not contain usable words")
    if not full_title:
        tokens = tokens[:MAX_TITLE_TOKENS]
    return "_".join(tokens)


def build_stem(author: str, year: str, title: str, *, full_title: bool) -> str:
    if not re.fullmatch(r"(?:19|20)\d{2}", year):
        raise ValueError("year must be four digits")
    stem = f"{author_slug(author)}_{year}_{title_slug(title, full_title=full_title)}"
    return stem[:MAX_STEM_CHARS].rstrip("_")


def stable_suffix(path: Path) -> str:
    return hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:8]


def target_path(path: Path, author: str, year: str, title: str) -> tuple[Path, str]:
    short_target = path.with_name(f"{build_stem(author, year, title, full_title=False)}.pdf")
    if short_target == path or not short_target.exists():
        return short_target, "short title"

    full_target = path.with_name(f"{build_stem(author, year, title, full_title=True)}.pdf")
    if full_target == path or not full_target.exists():
        return full_target, "short-title collision; used longer title"

    hashed_target = full_target.with_name(f"{full_target.stem}_{stable_suffix(path)}.pdf")
    return hashed_target, "longer-title collision; appended hash"


def clean_inspection_artifacts(*paths: Path) -> None:
    seen: set[Path] = set()
    for path in paths:
        inspect_dir = path.parent / ".pdf_inspect"
        if not inspect_dir.is_dir():
            continue
        for artifact in inspect_dir.glob(f"{path.stem}_page_*.png"):
            if artifact in seen:
                continue
            seen.add(artifact)
            artifact.unlink()
            print(f"removed inspection artifact: {artifact}")
        try:
            inspect_dir.rmdir()
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Rename one PDF from explicit metadata.")
    parser.add_argument("pdf")
    parser.add_argument("--author", required=True, help="First author/editor name or surname.")
    parser.add_argument("--year", required=True)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()

    path = Path(args.pdf).expanduser().resolve()
    if not path.exists() or path.suffix.lower() != ".pdf":
        raise SystemExit(f"not a PDF: {path}")

    try:
        target, reason = target_path(path, args.author, args.year, args.title)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if target == path:
        print(f"OK {path.name}: already normalized")
        clean_inspection_artifacts(path)
        return 0

    path.rename(target)
    print(f"RENAMED {path.name} -> {target.name} ({reason})")
    clean_inspection_artifacts(path, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
