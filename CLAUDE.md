# Historical Fiction Project

This repository contains a historical fiction / literary novel project.

The project is intentionally structured similarly to a software project:
- modular files
- explicit world state
- reusable research
- scene-based workflow
- incremental refinement

## Arbetsflöde — ingen worktree

All redigering sker direkt i huvudkatalogen (`D:\Dropbox\Kanalen - en roman`). Använd **inte** git worktrees eller isolerade grenar för detta projekt. Skäl: projektets filer är få och lätta att följa, och worktrees skapar förvirring om vilken version som är aktuell. Alla ändringar committas direkt på `master`.

Non-code tasks are expected and central to this repository.

---

# Overall Goals

The primary goals are:
- historical realism
- psychological realism
- subtle dialogue
- consistent worldbuilding
- continuity across scenes
- avoidance of modern tone or excessive exposition

The prose should generally favor:
- implication over explanation
- observation over narration
- restrained emotional expression
- concrete sensory details
- understated political and social tension

---

# Project Structure

## /research

Contains historical research and factual background material.

Typical contents:
- municipal politics
- social structures
- class markers
- architecture
- logistics
- transport
- historical events
- language usage
- wartime conditions

Research files may contain raw notes, summaries, extracted details, references, and speculative ideas. Treat research as supporting material, not immutable canon.

---

## /world

Contains canonical world descriptions.

Examples:
- locations
- institutions
- political structures
- fictional organizations
- recurring environmental details

Files in /world should generally be treated as higher-level canon.

---

## /characters

Contains character definitions.

Typical contents:
- background
- motivations
- social position
- speech patterns
- behavioral traits
- contradictions
- hidden motives

Character consistency is extremely important.

Avoid flattening characters into stereotypes.

---

## /timeline

Contains chronological information.

Important:
- maintain temporal consistency
- verify dates and sequencing
- avoid accidental timeline contradictions

---
## /outline

Each chapter is represented by a single .md document, in the same style as this, with an overarching description of the chapter and the intended individual scenes (~3-5 per chapter) clearly structured. You could say this is a chapter card with embedded scene cards. These are live documents, and we may incrementally refine them, add details etc, before generating or revising the scene prose.

### Naming convention — outline files

Chapter outline files are named with the same timestamp convention as prose folders (see below), e.g. `1942-08-14 - Ankomsten.md`. The timestamp anchors the chapter to its place in the story's chronology.

### Scene cards within outline files

Each scene card must specify:
- **Tidpunkt** — the scene's in-story date and time (YYYY-MM-DD HH:mm), used to derive the prose file name
- **POV** — which character's perspective the scene is told from (single POV per scene, held throughout)
- Goals, tone notes, factual anchors, unresolved tensions, and any other guidance for that scene

Time must progress monotonically across scenes and chapters. There are no flashbacks or non-linear time jumps.

## /prose

This folder has subfolders per chapter. Each subfolder is named with a timestamp prefix derived from the first scene's in-story date and time: `YYYY-MM-DD HHmm`, optionally followed by ` - ` and a title, e.g. `1942-08-14 0930 - Ankomsten`.

Each scene within a chapter folder is a Markdown file (UTF-8, no BOM). File names follow the same convention: `YYYY-MM-DD HHmm.md` or `YYYY-MM-DD HHmm - Scentitel.md`. Every paragraph is written as one line; paragraphs are separated by exactly one blank line (i.e. one LF after the paragraph line, then one LF for the blank line, then the next paragraph — never two blank lines between paragraphs). Markdown syntax should not appear in the prose itself — the `.md` extension is used purely to enable Pandoc-based export (see Build below).

Note: Colons are not valid in Windows file and folder names. Use `HHmm` (no colon) for all timestamps in paths.

Scenes should remain modular and focused.

Preferred scene length:
- approximately 2000 words; scene card instructions may override this

Each scene must:
- be told from a single character POV, held throughout (as declared in the scene card)

## Build

Prose files are Markdown so they can be compiled to PDF, EPUB, or DOCX using [Pandoc](https://pandoc.org). Example — export a single chapter to PDF:

```
pandoc "prose/1942-08-14 0930 - Ankomsten/"*.md -o chapter1.pdf
```

For PDF output, Pandoc requires a LaTeX engine (e.g. MiKTeX). DOCX output works without LaTeX:

```
pandoc "prose/1942-08-14 0930 - Ankomsten/"*.md -o chapter1.docx
```

Files are concatenated in filesystem order, which matches the timestamp-prefixed naming convention.

---

# Cross-referencing

Files may reference other project files using standard Markdown links with paths relative to the referencing file. This is encouraged wherever a reader (human or AI) would benefit from following a pointer to supporting material.

Typical uses:
- A character file linking to relevant research: `[Järnvägstransport under kriget](../research/jarnvag.md)`
- A scene card linking to a world file for a location: `[Hamnen i Göteborg](../world/goteborg-hamn.md)`
- An outline chapter linking to a character: `[Arvid Stenmark](../characters/arvid-stenmark.md)`

Use a light prose marker to signal the reference in context, e.g.:

> *Se även [järnvägstransport under kriget](../research/jarnvag.md) för historisk bakgrund.*

Cross-references are informational — they suggest where to look for context or inspiration, not what conclusions to draw.

---

# Berättarröst

Romanen saknar berättarröst helt. Det finns ingen extern berättare som kommenterar, sammanfattar eller värderar.

Varje scen är strikt begränsad till POV-karaktärens omedelbara perception och tankar. Det innebär:

- Ingen berättare som vet mer än POV-karaktären vid det givna ögonblicket
- Inga förutskickanden ("Han visste inte att…", "Det skulle dröja länge innan…")
- Inga retrospektiva insikter formulerade utifrån ("Senare skulle han förstå…")
- Ingen sammanfattning av tid som gått utanför en karaktärs direkta upplevelse
- Ingen värdering eller tolkning av händelser som inte tillhör POV-karaktärens medvetande

Förfluten tid och mellanliggande skeenden når läsaren endast genom karaktärernas minnen, samtal och iakttagelser — aldrig genom berättarkommentar.

---

# Writing Style Guidelines

Avoid:
- overly modern phrasing
- explicit exposition
- melodrama
- excessive emotional labeling
- repetitive sentence rhythms
- cliché metaphors

Avoid these specific markers of generic AI prose:
- opening paragraphs that set the scene with atmospheric throat-clearing before anything happens
- sentences built on present-participial stacking ("Walking into the room, noticing the dust, feeling the weight of...")
- characters who reflect on their own emotions in complete, well-formed sentences
- abstract nouns used for emotional shorthand ("grief", "hope", "tension" named rather than shown)
- over-use of "however", "nevertheless", "yet" as pivots between thoughts
- symmetrical or overly balanced sentence pairs that resolve too neatly
- dialogue that exists only to deliver information neither character would need to say aloud
- endings that summarize the scene's emotional meaning for the reader
- consecutive paragraphs each carrying a metaphorical or symbolic charge — a plain, functional paragraph has its own weight; not every observation needs an undertone; let the prose breathe between stronger passages
- the syntactic construction "inte X utan Y" / "inte ... utan ..." repeated in nearby paragraphs; it is a useful pattern once, a tic when it recurs; vary the syntax actively
- the related pattern "det var inte ... det var ..." used more than once in close proximity

Prefer:
- subtle implication
- restrained dialogue
- social subtext
- physical observation
- realistic ambiguity
- historically plausible behavior
- To let dialogue imply motives rather than state them directly.

The target language is Swedish:
- *everything* generated related to novel content must be in Swedish, this includes but is not limited to the prose, character, location, plot, chapter and scene descriptions and states.

Språkliga riktlinjer:
- Svenskan ska vara lagom litterär i tonen.
- Undvik jämna, välformulerade meningar som löper utan friktion — verklig prosa har ojämnheter, överraskningar, meningar som bryts av eller tar en oväntad vändning. Välj det lite oväntade ordet framför det uppenbara, men med måtta.
- Gör aldrig direkt- eller ord-för-ord-översättningar av idiomatiska uttryck på andra språk.
- Håll dialogen i trovärdig stil, såväl tids- som (social-)klassmässigt.

Tilltal och register:
- Bruket av *du*, *ni* (pluralis majestatis eller artigt singularis) och titeltilltal (t.ex. "direktören", "fröken Lindqvist") ska vara historiskt korrekt med hänsyn till romanens tidsperiod, karaktärernas sociala ställning, relation till varandra och situationens formalitet.
- Som en generell riktlinje: under 1900-talets första hälft var *du* i direkt tilltal reserverat för nära relationer (familj, nära vänner, barn); *ni* användes till obekanta och i formella sammanhang; titeltilltal var norm uppåt i hierarkin och ofta även i neutral kontext.
- En underordnad tilltalade sällan en överordnad med förnamn. En överordnad kunde däremot *du*-a underordnade utan att det upplevdes som artigt.
- Var uppmärksam på att karaktärers sätt att tilltala varandra kan förändras som dramatisk markör — en övergång till *du* eller till formellare tilltal är alltid meningsbärande.
- Liknande hänsyn gäller val av ordförråd, fraser och syntax: undvik modernismer som inte hör hemma i perioden.

---

# Character Dialogue

Speech patterns matter.

Characters should:
- differ in rhythm and vocabulary
- reflect education and social class
- avoid sounding uniformly modern
- avoid sounding theatrical

Subtle social hierarchy is important.

---

# Historical Realism

Historical realism is more important than dramatic convenience.

If uncertain:
- preserve plausibility
- avoid anachronisms
- avoid modern ideological framing unless intentional

Small concrete details are valuable.

---

# AI Workflow Expectations

The human author remains the final creative authority.

Claude should primarily assist with:
- refinement
- restructuring
- continuity analysis
- stylistic consistency
- brainstorming
- scene expansion
- summarization
- research synthesis

Claude should avoid:
- making large uncontrolled rewrites
- inventing major canon changes without request
- replacing subtle prose with generic prose
- overexplaining themes

When revising text:
- preserve tone
- preserve ambiguity
- preserve character voice
- preserve pacing unless explicitly asked otherwise

---

# Revision Philosophy

Prefer incremental improvements over total rewrites.

When possible:
- suggest
- refine
- tighten
- reorganize locally

rather than replacing entire scenes.

---

# Continuity Rules

Continuity is important across:
- timeline
- weather/season
- character knowledge
- social relationships
- geography
- political context
- recurring objects/details

Check consistency before introducing new facts.

---

# Tone

The intended tone is generally:
- intelligent
- restrained
- observant
- historically grounded
- psychologically realistic
- socially aware
- subtly tense

The prose should rarely feel sensationalistic.

---

# Priority Order

When tradeoffs occur, prioritize:

1. Historical plausibility
2. Psychological realism
3. Character consistency
4. Tone consistency
5. Literary quality
6. Plot efficiency

---

# Practical Guidance

Before major edits:
- read relevant character files
- read relevant world files
- check timeline consistency

Before introducing new historical details:
- prefer existing project research
- avoid unsupported assumptions

When uncertain:
- ask questions
- propose alternatives
- avoid overconfident invention
