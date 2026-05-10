#!/usr/bin/env python3
"""
prose_gen.py — Interaktiv prosagenerering för Kanalen

Användning:
    py tools/prose_gen.py
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def load_client():
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv(ROOT / ".env")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        sys.exit("Fel: OPENAI_API_KEY saknas i .env")
    return OpenAI(api_key=key)


def get_models():
    primary = os.getenv("PRIMARY_MODEL", "gpt-4.5")
    fast    = os.getenv("FAST_MODEL",    "gpt-4.5-mini")
    return primary, fast


# ---------------------------------------------------------------------------
# Scene discovery
# ---------------------------------------------------------------------------

def find_outline_files() -> list[Path]:
    outline_dir = ROOT / "outline"
    if not outline_dir.exists():
        return []
    return sorted(outline_dir.glob("*.md"))


def parse_scenes_from_outline(outline_path: Path) -> list[dict]:
    """Extract all scene cards from an outline file."""
    text = outline_path.read_text(encoding="utf-8")
    parts = re.split(r"(?=^## Scen \d)", text, flags=re.MULTILINE)
    scenes = []
    for part in parts:
        m = re.match(r"^## Scen (\d+)\s*[—–-]\s*(.+?)$", part, re.MULTILINE)
        if not m:
            continue
        number = int(m.group(1))
        title  = m.group(2).strip()
        tp = re.search(r"\*\*Tidpunkt:\*\*\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", part)
        if tp:
            date, hhmm = tp.group(1), tp.group(2)
            tidpunkt   = f"{date} {hhmm}"
            file_stem  = f"{date} {hhmm.replace(':', '')}"
        else:
            tidpunkt  = "okänd tidpunkt"
            file_stem = None
        pov_m = re.search(r"\*\*POV:\*\*\s*(.+?)$", part, re.MULTILINE)
        pov   = pov_m.group(1).strip() if pov_m else None
        scenes.append({
            "outline":   outline_path,
            "number":    number,
            "title":     title,
            "tidpunkt":  tidpunkt,
            "file_stem": file_stem,
            "pov":       pov,
            "card_text": part.strip(),
        })
    return scenes


def find_prose_file(file_stem: str | None) -> Path | None:
    """Return existing prose file matching YYYY-MM-DD HHmm prefix, or None."""
    if not file_stem:
        return None
    prose_root = ROOT / "prose"
    if not prose_root.exists():
        return None
    for candidate in prose_root.rglob("*.md"):
        if candidate.stem.startswith(file_stem):
            return candidate
    return None


def collect_all_scenes() -> list[dict]:
    """Return flat list of all scenes across all outline files, with prose status."""
    all_scenes = []
    for outline in find_outline_files():
        for scene in parse_scenes_from_outline(outline):
            prose_file = find_prose_file(scene["file_stem"])
            scene["prose_file"] = prose_file
            if prose_file:
                mtime = datetime.fromtimestamp(prose_file.stat().st_mtime)
                scene["prose_mtime"] = mtime.strftime("%Y-%m-%d %H:%M")
            else:
                scene["prose_mtime"] = None
            all_scenes.append(scene)
    return all_scenes


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------

def chapter_title(outline_path: Path) -> str:
    m = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[-—]\s*", "", outline_path.stem)
    return m


def print_scene_list(scenes: list[dict]):
    current_outline = None
    for i, s in enumerate(scenes, 1):
        if s["outline"] != current_outline:
            current_outline = s["outline"]
            print(f"\n  {chapter_title(current_outline)}")
        if s["prose_mtime"]:
            status = f"✓  (uppdaterad {s['prose_mtime']})"
        else:
            status = "–  ej genererad"
        print(f"  {i:>2}.  Scen {s['number']} — {s['title']:<40}  [{s['tidpunkt']}]  {status}")


def prompt_scene_choice(scenes: list[dict]) -> dict:
    while True:
        try:
            raw = input("\nVälj scen (nummer): ").strip()
            idx = int(raw) - 1
            if 0 <= idx < len(scenes):
                return scenes[idx]
            print(f"     Ange ett tal mellan 1 och {len(scenes)}.")
        except (ValueError, EOFError):
            print("     Ogiltigt val.")


def confirm(prompt: str) -> bool:
    ans = input(prompt).strip().lower()
    return ans in ("j", "ja", "y", "yes", "")


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

def collect_background_files() -> list[dict]:
    result = []
    for folder in ["characters", "world", "research"]:
        folder_path = ROOT / folder
        if not folder_path.exists():
            continue
        for f in sorted(folder_path.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            heading = next(
                (line.lstrip("#").strip() for line in content.splitlines() if line.startswith("#")),
                f.stem,
            )
            result.append({"path": str(f.relative_to(ROOT)), "heading": heading})
    return result


def select_files(client, fast_model: str, scene_card: str, all_files: list[dict]) -> list[Path]:
    file_list = "\n".join(f"  {f['path']}: {f['heading']}" for f in all_files)
    prompt = (
        f"Scenkort:\n{scene_card}\n\n"
        f"Tillgängliga projektfiler:\n{file_list}\n\n"
        "Returnera ett JSON-objekt med nyckeln \"files\" innehållande en lista av filsökvägar "
        "som är relevanta för den här scenen. Inkludera karaktärsfiler för nämnda personer, "
        "platsfiler för nämnda platser, och research-filer som kan vara till nytta."
    )
    resp = client.chat.completions.create(
        model=fast_model,
        messages=[
            {"role": "system", "content": "Du är en filväljare för ett romanprojekt. Svara enbart med JSON."},
            {"role": "user",   "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data  = json.loads(resp.choices[0].message.content)
    paths = data.get("files", [])
    return [ROOT / p for p in paths if (ROOT / p).exists()]


def extract_chapter_context(scene: dict) -> str:
    """Return chapter preamble + all earlier scene cards from the same outline file."""
    text = scene["outline"].read_text(encoding="utf-8")
    parts = re.split(r"(?=^## Scen \d)", text, flags=re.MULTILINE)

    preamble = parts[0].strip() if parts else ""

    earlier = []
    for part in parts[1:]:
        m = re.match(r"^## Scen (\d+)", part)
        if m and int(m.group(1)) < scene["number"]:
            earlier.append(part.strip())

    blocks = []
    if preamble:
        blocks.append(f"### Kapitelöversikt\n{preamble}")
    if earlier:
        blocks.append("### Tidigare scenkort i samma kapitel\n\n" + "\n\n---\n\n".join(earlier))
    return "\n\n".join(blocks)


def load_prose_context(scene: dict, all_scenes: list[dict]) -> str:
    """Load prose from: (1) immediately preceding scene, (2) most recent scene with same POV.
    Deduplicates if they happen to be the same file."""
    current_idx = next(
        (i for i, s in enumerate(all_scenes)
         if s["outline"] == scene["outline"] and s["number"] == scene["number"]),
        None,
    )

    to_load = {}  # file_stem -> (label, prose_file)

    # 1. Immediately preceding scene (any POV)
    if current_idx and current_idx > 0:
        prev = all_scenes[current_idx - 1]
        if prev["prose_file"]:
            to_load[prev["file_stem"]] = (
                f"Föregående scen — Scen {prev['number']}: {prev['title']} (POV: {prev['pov']})",
                prev["prose_file"],
            )

    # 2. Most recent scene with same POV
    if scene["pov"]:
        same_pov = [
            s for s in all_scenes[:current_idx]
            if s["pov"] == scene["pov"] and s["prose_file"]
        ]
        if same_pov:
            latest = same_pov[-1]
            if latest["file_stem"] not in to_load:
                to_load[latest["file_stem"]] = (
                    f"Senaste scen med samma POV ({latest['pov']}) — Scen {latest['number']}: {latest['title']}",
                    latest["prose_file"],
                )

    parts = []
    for label, prose_file in to_load.values():
        content = prose_file.read_text(encoding="utf-8")
        parts.append(f"[{label}]\n{content}")
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

def derive_output_path(scene: dict) -> Path:
    if not scene["file_stem"]:
        sys.exit("Fel: kan inte härleda filnamn — Tidpunkt saknas i scenkortet.")
    file_name  = f"{scene['file_stem']} - {scene['title']}.md"
    chapter_date = scene["outline"].stem[:10]
    prose_root   = ROOT / "prose"
    prose_root.mkdir(exist_ok=True)
    candidates = [d for d in prose_root.iterdir() if d.is_dir() and d.name.startswith(chapter_date)]
    if candidates:
        chapter_folder = candidates[0]
    else:
        outline_title = chapter_title(scene["outline"])
        first_stem    = scene["file_stem"]
        chapter_folder = prose_root / f"{chapter_date} {first_stem[11:]} - {outline_title}"
        chapter_folder.mkdir(parents=True, exist_ok=True)
    return chapter_folder / file_name


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_prose(client, primary_model: str, scene: dict,
                   context_files: list[Path], claude_md: str,
                   chapter_context: str, prose_context: str) -> str:
    file_blocks = [f"### {f.name}\n{f.read_text(encoding='utf-8')}" for f in context_files]

    system_parts = ["# Stilriktlinjer och projektregler\n" + claude_md]
    if file_blocks:
        system_parts.append("# Projektfiler — bakgrundsmaterial\n" + "\n\n".join(file_blocks))
    if chapter_context:
        system_parts.append("# Kapitelkontext — översikt och tidigare scenkort\n" + chapter_context)
    if prose_context:
        system_parts.append("# Prosareferens — tidigare scener för kontinuitet och röst\n" + prose_context)

    user = (
        "Generera prosan för följande scen. Skriv på svenska. "
        "Ungefär 2000 ord. Följ scenkortet och stilriktlinjerna strikt. "
        "Inga rubrikrader, inga metakommentarer — svara enbart med prosan.\n\n"
        "OBS: Om prosareferenser ingår i kontexten används de för stilmatchning och narrativ "
        "kontinuitet — inte som indikation på att scenerna är direkt sammanhängande i tid. "
        "Mycket kan ha hänt mellan referensscenen och denna scen; utgå från scenkortets "
        "tidpunkt och situation, inte från att det är en direkt fortsättning.\n\n"
        + scene["card_text"]
    )

    resp = client.chat.completions.create(
        model=primary_model,
        messages=[
            {"role": "system", "content": "\n\n".join(system_parts)},
            {"role": "user",   "content": user},
        ],
        temperature=0.85,
        max_completion_tokens=6000,
    )
    return resp.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\n=== Kanalen — Prosagenerering ===\n")

    scenes = collect_all_scenes()
    if not scenes:
        sys.exit("Inga scener hittades. Kontrollera att /outline innehåller .md-filer.")

    print("Tillgängliga scener:")
    print_scene_list(scenes)

    scene = prompt_scene_choice(scenes)
    print(f"\nVald: Scen {scene['number']} — {scene['title']}  [{scene['tidpunkt']}]")

    output_path = derive_output_path(scene)

    client = load_client()
    primary_model, fast_model = get_models()

    print(f"\nSamlar bakgrundsfiler...")
    all_files = collect_background_files()

    print(f"Väljer relevanta filer med {fast_model}...")
    selected = select_files(client, fast_model, scene["card_text"], all_files)
    print(f"  Valda ({len(selected)}): {[f.name for f in selected]}")

    print("\nLaddar kontext...")
    chapter_context = extract_chapter_context(scene)
    prose_context   = load_prose_context(scene, scenes)
    claude_md       = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    if prose_context:
        labels = [l.split(" —")[0] for l in re.findall(r"\[(.+?)\]", prose_context)]
        print(f"  Prosareferenser: {labels}")

    print(f"Genererar prosa med {primary_model}... ", end="", flush=True)
    prose = generate_prose(client, primary_model, scene, selected, claude_md, chapter_context, prose_context)
    print("klar.")

    output_path.write_text(prose, encoding="utf-8")
    print(f"\nSparad: {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
