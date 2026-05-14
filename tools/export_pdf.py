#!/usr/bin/env python3
"""
export_pdf.py — Export prose scenes to PDF via Pandoc.

Usage:
    py tools/export_pdf.py <output.pdf>

Requires: pandoc + xelatex (via MiKTeX).
"""

import re
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Typography config
# ---------------------------------------------------------------------------

FONT       = "Palatino Linotype"   # system font; swap to e.g. "Georgia"
FONTSIZE   = "11pt"
LINESTRETCH = "1.2"               # 1.0 = tight, 1.25 = comfortable, 1.4 = spacious
MARGIN     = "1.5cm"

PANDOC_ARGS = [
    "--pdf-engine=xelatex",
    "--standalone",
    "-V", "papersize=a5",
    "-V", f"geometry:margin={MARGIN}",
    "-V", f"fontsize={FONTSIZE}",
    "-V", f"linestretch={LINESTRETCH}",
    "-V", f"mainfont={FONT}",
    "-V", "lang=sv",
]

# Scene separator injected between scenes (raw LaTeX, centered * * *)
SCENE_BREAK = (
    "\n\n```{=latex}\n"
    "\\medskip\\begin{center}*\\quad*\\quad*\\end{center}\\medskip\n"
    "```\n\n"
)

# ---------------------------------------------------------------------------
# Scene discovery
# ---------------------------------------------------------------------------

DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{4}\s*[-—]\s*")


def strip_prefix(name: str) -> str:
    return DATE_PREFIX.sub("", name).strip() or name


def collect_scenes() -> list[tuple[str, Path]]:
    """Return [(chapter_label, scene_path)] sorted by filesystem order."""
    prose_root = ROOT / "prose"
    if not prose_root.exists():
        return []
    result = []
    for path in sorted(prose_root.rglob("*.md")):
        result.append((strip_prefix(path.parent.name), path))
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


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------

def build_markdown(selected: list[tuple[str, Path]]) -> str:
    """Combine scenes into a single markdown string.

    Inserts a chapter heading (# Title) before the first scene of each
    chapter, and a * * * separator between scenes.
    """
    parts = []
    current_chapter = None

    for chapter, path in selected:
        # Chapter heading on chapter change
        if chapter != current_chapter:
            current_chapter = chapter
            parts.append(f"# {chapter}\n\n")

        # Scene separator (not before the very first scene)
        if parts and not parts[-1].startswith("# "):
            parts.append(SCENE_BREAK)

        parts.append(path.read_text(encoding="utf-8").strip())

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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

    chapter_from = selected[0][0]
    chapter_to   = selected[-1][0]
    label = chapter_from if chapter_from == chapter_to else f"{chapter_from} → {chapter_to}"
    print(f"\nExporting {len(selected)} scene(s) [{label}] → {output.name} ...")

    combined = build_markdown(selected)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                     encoding="utf-8", delete=False) as tmp:
        tmp.write(combined)
        tmp_path = tmp.name

    try:
        cmd = ["pandoc", tmp_path, "-o", str(output)] + PANDOC_ARGS
        result = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"\nPandoc error:\n{result.stderr}")
        sys.exit(1)

    print(f"Saved: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
