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
import time
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


# reasoning_effort deliberately not used: gains are marginal for creative prose
# and internal reasoning tokens add cost without clear quality benefit.
# Prompt quality and context richness are the right levers here.


def _extract_content(resp) -> str:
    """Safely extract text content from a chat completion response."""
    choice  = resp.choices[0]
    reason  = choice.finish_reason
    message = choice.message

    # Refusal (gpt-5.x)
    if getattr(message, "refusal", None):
        raise RuntimeError(f"Model refused the request: {message.refusal}")

    # finish_reason diagnostics
    if reason == "content_filter":
        raise RuntimeError("Response blocked by content filter (finish_reason=content_filter).")
    if reason == "length":
        print("\n  ⚠  Output truncated (finish_reason=length) — consider raising max_completion_tokens.")

    content = message.content

    # Newer API versions may return a list of content blocks
    if isinstance(content, list):
        parts = [block.text if hasattr(block, "text") else str(block) for block in content]
        content = "".join(parts)

    if not content or not content.strip():
        raise RuntimeError(
            f"Empty response from model (finish_reason={reason}). "
            "Check API quota, model name, and whether the prompt triggers safety filters."
        )

    return content.strip()


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

_stats: list[dict] = []   # accumulated across all calls in a session


def record_stat(label: str, model: str, elapsed: float, usage) -> dict:
    """Record one API call and return its stat dict."""
    stat = dict(label=label, model=model, elapsed=elapsed,
                tok_in=usage.prompt_tokens, tok_out=usage.completion_tokens)
    _stats.append(stat)
    return stat


def print_stat(stat: dict):
    print(f"  [{stat['label']}] {stat['elapsed']:.1f}s  "
          f"↑{stat['tok_in']:,} ↓{stat['tok_out']:,} tokens")


def print_summary():
    if not _stats:
        return
    total_tok_in  = sum(s["tok_in"]  for s in _stats)
    total_tok_out = sum(s["tok_out"] for s in _stats)
    total_elapsed = sum(s["elapsed"] for s in _stats)
    print(f"\n{'─'*45}")
    print(f"  Totalt  {total_elapsed:.1f}s  "
          f"↑{total_tok_in:,} ↓{total_tok_out:,} tokens")
    print(f"{'─'*45}")


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
            status = f"✓  (updated {s['prose_mtime']})"
        else:
            status = "-  not generated"
        print(f"  {i:>2}.  Scen {s['number']} — {s['title']:<40}  [{s['tidpunkt']}]  {status}")


def confirm(prompt: str) -> bool:
    ans = input(prompt).strip().lower()
    return ans in ("y", "yes", "")


def prompt_existing_action(scene: dict) -> str:
    """Return 'abort', 'regenerate', 'revise', or 'continuity'."""
    print(f"\n  Prose exists (updated {scene['prose_mtime']})")
    print("  1. Keep existing prose (abort)")
    print("  2. Regenerate")
    print("  3. Revise")
    print("  4. Update continuity only")
    while True:
        ans = input("  Choice [1/2/3/4]: ").strip()
        if ans in ("1", ""):
            return "abort"
        if ans == "2":
            return "regenerate"
        if ans == "3":
            return "revise"
        if ans == "4":
            return "continuity"
        print("  Enter 1, 2, 3 or 4.")


def prompt_instructions(label: str) -> str:
    """Prompt for multiline instructions. Blank line finishes input (may return empty string)."""
    print(f"\n{label} (avsluta med blank rad):")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

def collect_background_files() -> list[dict]:
    result = []
    for folder in ["characters", "world", "research", "plots"]:
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
    t0   = time.time()
    resp = client.chat.completions.create(
        model=fast_model,
        messages=[
            {"role": "system", "content": "Du är en filväljare för ett romanprojekt. Svara enbart med JSON."},
            {"role": "user",   "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    print_stat(record_stat("file-select", fast_model, time.time() - t0, resp.usage))
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
# Continuity
# ---------------------------------------------------------------------------

def collect_continuity_context(scene: dict, all_scenes: list[dict]) -> str:
    """Return continuity extracts from all scenes preceding the current one."""
    cont_dir = ROOT / "continuity"
    if not cont_dir.exists():
        return ""
    current_idx = next(
        (i for i, s in enumerate(all_scenes)
         if s["outline"] == scene["outline"] and s["number"] == scene["number"]),
        None,
    )
    if not current_idx:
        return ""
    parts = []
    for s in all_scenes[:current_idx]:
        if not s["file_stem"] or not s["prose_file"]:
            continue
        for candidate in sorted(cont_dir.glob("*.md")):
            if candidate.stem.startswith(s["file_stem"]):
                content = candidate.read_text(encoding="utf-8").strip()
                parts.append(f"[Scen {s['number']}: {s['title']}]\n{content}")
                break
    return "\n\n---\n\n".join(parts)


def _target_words(scene: dict) -> int:
    """Parse declared scene length from card text, default 2000."""
    m = re.search(r'Längd.*?(\d[\s\d]{1,4})\s*ord', scene["card_text"])
    if m:
        try:
            return int(m.group(1).replace(" ", "").replace("\xa0", ""))
        except ValueError:
            pass
    return 2000


def extract_continuity(client, fast_model: str, scene: dict, prose: str) -> str:
    """Extract terse continuity factoids from prose via mini-model."""
    max_bullets = max(5, min(20, _target_words(scene) // 150 + 3))
    system = (
        "Du är en kontinuitetsassistent för ett romanprojekt. "
        "Din uppgift: extrahera exakt de faktapunkter som anges, i exakt det format som anges. "
        "Skriv inget annat."
    )
    prompt = (
        f"Scen: {scene['title']} ({scene['tidpunkt']})\n\n"
        "Uppgift: Extrahera konkreta faktapunkter för kontinuitet i framtida scener.\n\n"
        "Ta med:\n"
        "- Fysiska detaljer om namngivna bikaraktärer (kläder, röst, rörelse, specifika drag)\n"
        "- Platsdetaljer etablerade i scenen (färger, ljud, lukt, specifika föremål)\n"
        "- Konkreta vanor eller beteenden som visas\n\n"
        "Utelämna:\n"
        "- Psykologi och abstrakta karaktärsdrag\n"
        "- Plotinfo och händelseförlopp\n"
        "- Fakta uppenbara ur karaktärernas bakgrundsfiler\n\n"
        f"Utdataformat: {max_bullets} bullet points på svenska, varje punkt max 15 ord. "
        "Inga rubriker. Inga inledningar. Bara bullet points.\n\n"
        f"Prosa:\n{prose}"
    )
    t0   = time.time()
    resp = client.chat.completions.create(
        model=fast_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        temperature=0,
        max_completion_tokens=600,
    )
    print_stat(record_stat("continuity", fast_model, time.time() - t0, resp.usage))
    return _extract_content(resp)


def save_continuity(scene: dict, content: str) -> Path | None:
    """Save (overwrite) continuity extract for a scene."""
    if not scene["file_stem"]:
        return None
    cont_dir = ROOT / "continuity"
    cont_dir.mkdir(exist_ok=True)
    path = cont_dir / f"{scene['file_stem']} - {scene['title']}.md"
    path.write_text(
        f"# Kontinuitet — {scene['title']} ({scene['tidpunkt']})\n\n{content}\n",
        encoding="utf-8",
    )
    return path


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
                   chapter_context: str, prose_context: str,
                   continuity_context: str = "",
                   extra_instruction: str = "") -> str:
    file_blocks = [f"### {f.name}\n{f.read_text(encoding='utf-8')}" for f in context_files]

    system_parts = ["# Stilriktlinjer och projektregler\n" + claude_md]
    if file_blocks:
        system_parts.append("# Projektfiler — bakgrundsmaterial\n" + "\n\n".join(file_blocks))
    if chapter_context:
        system_parts.append("# Kapitelkontext — översikt och tidigare scenkort\n" + chapter_context)
    if continuity_context:
        system_parts.append("# Kontinuitetsfakta — detaljer etablerade i tidigare scener\n" + continuity_context)
    if prose_context:
        system_parts.append("# Prosareferens — tidigare scener för stilmatchning och röst\n" + prose_context)

    user = (
        "Generera prosan för följande scen. Skriv på svenska. "
        "Ungefär 2000 ord. Följ scenkortet och stilriktlinjerna strikt.\n\n"
        "UTDATAFORMAT — följ exakt:\n"
        "- Ren löptext utan markdown, rubriker eller metakommentarer\n"
        "- Repliker skrivs med citationstecken, på samma rad som dialogtaggarna (t.ex. sa hon, frågade han)\n"
        "- Varje stycke på en enda rad (inga radbrytningar inom ett stycke)\n"
        "- Exakt en blank rad mellan styckena (dvs. ett enda tomt radmellanrum: \\n\\n)\n"
        "- Inga dubbla blankrader, inga indragna rader, inga listor\n\n"
        "OBS: Om prosareferenser ingår i kontexten används de för stilmatchning och narrativ "
        "kontinuitet — inte som indikation på att scenerna är direkt sammanhängande i tid. "
        "Mycket kan ha hänt mellan referensscenen och denna scen; utgå från scenkortets "
        "tidpunkt och situation, inte från att det är en direkt fortsättning.\n\n"
        + scene["card_text"]
        + (f"\n\n--- EXTRA INSTRUKTIONER ---\n{extra_instruction}" if extra_instruction else "")
    )

    t0   = time.time()
    resp = client.chat.completions.create(
        model=primary_model,
        messages=[
            {"role": "system", "content": "\n\n".join(system_parts)},
            {"role": "user",   "content": user},
        ],
        temperature=0.85,
        max_completion_tokens=6000,
    )
    print_stat(record_stat("generate", primary_model, time.time() - t0, resp.usage))
    return _extract_content(resp)


def revise_prose(client, primary_model: str, scene: dict,
                 existing_prose: str, instruction: str,
                 claude_md: str, chapter_context: str,
                 continuity_context: str = "") -> str:
    """Targeted revision of existing prose. Skips background file selection."""
    system_parts = ["# Style guidelines\n" + claude_md]
    if chapter_context:
        system_parts.append("# Chapter context — overview and earlier scene cards\n" + chapter_context)
    if continuity_context:
        system_parts.append("# Continuity facts — details established in prior scenes\n" + continuity_context)
    system_parts.append("# Scene card — goals and constraints for this scene\n" + scene["card_text"])

    user = (
        "Below is the existing prose for this scene. Revise it according to the instructions that follow.\n\n"
        "OUTPUT FORMAT — follow exactly:\n"
        "- Plain text only: no markdown, no headings, no meta-comments\n"
        "- Each paragraph on a single line (no line breaks within a paragraph)\n"
        "- Exactly one blank line between paragraphs (i.e. a single empty line: \\n\\n)\n"
        "- No double blank lines, no indented lines, no lists\n\n"
        f"--- EXISTING PROSE ---\n{existing_prose}\n\n"
        f"--- REVISION INSTRUCTIONS ---\n{instruction}"
    )

    t0   = time.time()
    resp = client.chat.completions.create(
        model=primary_model,
        messages=[
            {"role": "system", "content": "\n\n".join(system_parts)},
            {"role": "user",   "content": user},
        ],
        temperature=0.7,
        max_completion_tokens=6000,
    )
    print_stat(record_stat("revise", primary_model, time.time() - t0, resp.usage))
    return _extract_content(resp)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def prompt_scene_choice(scenes: list[dict]) -> dict | None:
    """Return chosen scene, or None if user wants to quit."""
    while True:
        try:
            raw = input("\nSelect scene (number, or q to quit): ").strip()
            if raw.lower() == "q":
                return None
            idx = int(raw) - 1
            if 0 <= idx < len(scenes):
                return scenes[idx]
            print(f"     Enter a number between 1 and {len(scenes)}.")
        except (ValueError, EOFError):
            print("     Invalid choice.")


def main():
    print("\n=== Kanalen — Prose Generator ===\n")

    client = load_client()
    primary_model, fast_model = get_models()

    while True:
        scenes = collect_all_scenes()
        if not scenes:
            sys.exit("No scenes found. Check that /outline contains .md files.")

        print("Available scenes:")
        print_scene_list(scenes)

        scene = prompt_scene_choice(scenes)
        if scene is None:
            print_summary()
            print("Avslutar.")
            break

        print(f"\nSelected: Scen {scene['number']} — {scene['title']}  [{scene['tidpunkt']}]")

        # --- Determine action ---
        action = "generate"
        extra_instruction = ""
        if scene["prose_file"]:
            action = prompt_existing_action(scene)
            if action == "abort":
                continue
            if action == "revise":
                extra_instruction = prompt_instructions("Revideringsinstruktioner")
                if not extra_instruction:
                    print("Inga instruktioner — avbrutet.")
                    continue
            elif action != "continuity":
                extra_instruction = prompt_instructions("Extra instruktioner (valfritt)")
        else:
            extra_instruction = prompt_instructions("Extra instruktioner (valfritt)")

        output_path = derive_output_path(scene)

        # --- Continuity-only: no prose generation or revision ---
        if action == "continuity":
            existing_prose = scene["prose_file"].read_text(encoding="utf-8")
            print(f"\nExtracting continuity with {fast_model}... ", end="", flush=True)
            continuity = extract_continuity(client, fast_model, scene, existing_prose)
            cont_path  = save_continuity(scene, continuity)
            print("done.")
            if cont_path:
                print(f"Continuity: {cont_path.relative_to(ROOT)}")
            continue

        print("\nLoading context...")
        chapter_context    = extract_chapter_context(scene)
        continuity_context = collect_continuity_context(scene, scenes)
        claude_md          = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

        if continuity_context:
            n = continuity_context.count("\n# Kontinuitet")
            print(f"  Continuity: {max(1, n)} earlier scene(s) loaded.")

        try:
            if action == "revise":
                existing_prose = scene["prose_file"].read_text(encoding="utf-8")
                print(f"Revising with {primary_model}... ", end="", flush=True)
                prose = revise_prose(client, primary_model, scene,
                                     existing_prose, extra_instruction,
                                     claude_md, chapter_context, continuity_context)
            else:
                print(f"Collecting background files...")
                all_files = collect_background_files()
                print(f"Selecting relevant files with {fast_model}...")
                selected = select_files(client, fast_model, scene["card_text"], all_files)
                print(f"  Selected ({len(selected)}): {[f.name for f in selected]}")

                prose_context = load_prose_context(scene, scenes)
                if prose_context:
                    labels = [l.split(" —")[0] for l in re.findall(r"\[(.+?)\]", prose_context)]
                    print(f"  Prose references: {labels}")

                print(f"Generating prose with {primary_model}... ", end="", flush=True)
                prose = generate_prose(client, primary_model, scene, selected,
                                       claude_md, chapter_context, prose_context,
                                       continuity_context, extra_instruction)
        except RuntimeError as e:
            print(f"\n  FEL: {e}")
            continue

        print("done.")
        output_path.write_text(prose, encoding="utf-8")
        print(f"\nSaved: {output_path.relative_to(ROOT)}")

        print(f"Extracting continuity with {fast_model}... ", end="", flush=True)
        try:
            continuity = extract_continuity(client, fast_model, scene, prose)
        except RuntimeError as e:
            print(f"\n  Continuity-extraktion misslyckades: {e}")
            continue
        cont_path  = save_continuity(scene, continuity)
        print("done.")
        if cont_path:
            print(f"Continuity: {cont_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
