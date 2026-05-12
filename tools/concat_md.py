#!/usr/bin/env python3
"""
concat_md.py — Concatenate all background .md files into one document.

Usage:
    py tools/concat_md.py <output_file>

Example:
    py tools/concat_md.py background.md
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ["characters", "world", "research", "plots"]
SEPARATOR = "\n\n---\n\n"


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: py tools/concat_md.py <output_file>")

    output_path = Path(sys.argv[1])
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    blocks = []
    file_count = 0

    for folder in FOLDERS:
        folder_path = ROOT / folder
        if not folder_path.exists():
            continue
        for f in sorted(folder_path.glob("*.md")):
            rel = f.relative_to(ROOT)
            content = f.read_text(encoding="utf-8").strip()
            blocks.append(f"<!-- {rel} -->\n\n{content}")
            file_count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(SEPARATOR.join(blocks) + "\n", encoding="utf-8")
    print(f"Wrote {file_count} files → {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
