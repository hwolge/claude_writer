#!/usr/bin/env python3
"""
export_pdf.py — Export prose scenes to PDF via Pandoc.

Usage:
    py tools/export_pdf.py <output.pdf>

Requires: pandoc + a LaTeX engine (xelatex via MiKTeX).
"""

import re
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PANDOC_ARGS = [
    "--pdf-engine=xelatex",
    "--standalone",
    "-V", "papersize=a4",
    "-V", "geometry:margin=3cm",
    "-V", "fontsize=12pt",
    "-V", "linestretch=1.4",
    "-V", "lang=sv",
]

DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{4}\s*[-—]\s*")


def strip_prefix(name: str) -> str:
    return DATE_PREFIX.sub("", name).strip() or name


def collect_scenes() -> list[tuple[str, Path]]:
    """Return [(chapter_label, file_path)] sorted by filesystem order."""
    prose_root = ROOT / "prose"
    if not prose_root.exists():
        return []
    result = []
    for f in sorted(prose_root.rglob("*.md")):
        result.append((strip_prefix(f.parent.name), f))
    return result


def print_scene_list(scenes: list[tuple[str, Path]]):
    current = None
    for i, (chapter, path) in enumerate(scenes, 1):
        if chapter != current:
            current = chapter
            print(f"\n  {chapter}")
        print(f"  {i:>2}.  {strip_prefix(path.stem)}")


def prompt_int(label: str, default: int, lo: int, hi: int) -> int:
    while True:
        raw = input(f"  {label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if lo <= val <= hi:
                return val
            print(f"     Enter a number between {lo} and {hi}.")
        except ValueError:
            print("     Invalid input.")


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: py tools/export_pdf.py <output.pdf>")

    output = Path(sys.argv[1])
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    if not shutil.which("pandoc"):
        sys.exit("Error: pandoc not found — install from https://pandoc.org")

    scenes = collect_scenes()
    if not scenes:
        sys.exit("No prose files found in /prose.")

    total = len(scenes)

    print("\n=== Kanalen — PDF Export ===\n")
    print("Available scenes:")
    print_scene_list(scenes)
    print()

    start = prompt_int(f"From scene (1–{total})", 1, 1, total)
    end   = prompt_int(f"To scene   (1–{total})", total, start, total)

    selected = scenes[start - 1 : end]
    files = [str(path) for _, path in selected]

    chapter_from = selected[0][0]
    chapter_to   = selected[-1][0]
    label = chapter_from if chapter_from == chapter_to else f"{chapter_from} → {chapter_to}"
    print(f"\nExporting {len(selected)} scene(s) [{label}] → {output.name} ...")

    cmd = ["pandoc"] + files + ["-o", str(output)] + PANDOC_ARGS
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"\nPandoc error:\n{result.stderr}")
        sys.exit(1)

    print(f"Saved: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
