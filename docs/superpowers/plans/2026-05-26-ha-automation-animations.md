# ha-automation-animations Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a project skill that guides Claude to hand-author verified animated-SVG floor-plan diagrams of Home Assistant automations, one SVG per automation, embedded in area READMEs.

**Architecture:** The skill is a *method*, not a code generator. It ships `SKILL.md` (instructions + checklist + frontmatter triggers), a verified reference SVG (the bedroom presence-lighting animation), a copy-paste `defs.svg` (reusable glow/foot/lampcast filters + easing splines), and a `layout.schema.md` documenting the per-area geometry file. Per automation, Claude reads the automation YAML, fills/reuses the area's `layout.yaml`, hand-writes a SMIL-animated SVG modeled on the reference, then verifies it by serving over http and screenshotting each animation phase with Playwright.

**Tech Stack:** Markdown skill, SVG + SMIL animation, `python3 -m http.server` for local serving, Playwright MCP for render verification. No build step, no runtime deps.

**"Verification" in this plan:** This builds documentation/skill artifacts, not testable code. The TDD analogue is: define the success check first (what a correct render looks like), produce the artifact, then run the check (Playwright render at each phase) and confirm before committing. Each artifact task ends with a render-or-validate step + commit.

---

## File Structure

```
.claude/skills/ha-automation-animations/
  SKILL.md                       # Task 5 — method, checklist, frontmatter
  reference/
    presence-lighting.svg        # Task 1 — copied from the verified bedroom SVG
    defs.svg                      # Task 2 — reusable <defs> block + usage notes
    layout.schema.md             # Task 3 — layout.yaml field reference + bedroom example
    AUTHORING.md                 # Task 4 — the per-SVG authoring walkthrough + conventions

packages/areas/first-floor/bedroom/docs/
  presence-lighting.svg          # already committed (the reference origin)
  layout.yaml                    # Task 6 — bedroom geometry, back-filled
packages/areas/first-floor/bedroom/
  README.md                      # Task 7 — embed the SVG under "Lighting"
```

Responsibilities:
- `SKILL.md` — entry point: when to fire, the ordered checklist, links to reference files. Small, points outward.
- `reference/presence-lighting.svg` — the gold render. Claude reads it to mirror structure/colors/timing.
- `reference/defs.svg` — the only "reusable code": filters + gradients + easing keySplines, copy-pasted into each new SVG.
- `reference/layout.schema.md` — schema doc; keeps geometry input consistent across areas.
- `reference/AUTHORING.md` — the creative method (phases, layer conventions, the learned bugs) + the verification loop, kept out of SKILL.md so SKILL.md stays scannable.
- `bedroom/docs/layout.yaml` — first real layout, doubles as the worked example referenced by the schema doc.

---

## Task 1: Seed the reference SVG

**Files:**
- Create: `.claude/skills/ha-automation-animations/reference/presence-lighting.svg`
- Source: `packages/areas/first-floor/bedroom/docs/presence-lighting.svg` (already committed + verified)

- [ ] **Step 1: Define the success check**

The reference SVG must be byte-identical to the verified bedroom SVG, so the skill's "gold render" matches what was visually confirmed (person walks door→bed, PIR cone pulses, stripe glows on, vacant→off).

- [ ] **Step 2: Copy the verified SVG into the skill**

```bash
mkdir -p .claude/skills/ha-automation-animations/reference
cp packages/areas/first-floor/bedroom/docs/presence-lighting.svg \
   .claude/skills/ha-automation-animations/reference/presence-lighting.svg
```

- [ ] **Step 3: Verify the copy matches**

Run: `diff packages/areas/first-floor/bedroom/docs/presence-lighting.svg .claude/skills/ha-automation-animations/reference/presence-lighting.svg && echo MATCH`
Expected: `MATCH` (no diff output)

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/ha-automation-animations/reference/presence-lighting.svg
git commit -m "feat(skill): seed ha-automation-animations reference SVG"
```

---

## Task 2: Extract reusable defs.svg

**Files:**
- Create: `.claude/skills/ha-automation-animations/reference/defs.svg`

- [ ] **Step 1: Define the success check**

A standalone snippet holding exactly the reusable `<defs>` from the reference (glow filter, foot radial gradient, lampcast radial gradient) plus the canonical easing keySplines string and the color palette as comments. Copy-pasteable into any new SVG without edits.

- [ ] **Step 2: Write the file**

````markdown path=.claude/skills/ha-automation-animations/reference/defs.svg
<!--
  Reusable building blocks for HA automation animations.
  Copy the <defs> block verbatim into a new SVG. Reference IDs: glow, foot, lampcast.

  PALETTE
    bg          #0f1420      walls       #161d2c   wall-stroke #2b3850
    person      #7fd1ff      person-edge #cdeeff
    warm light  #ffd17a      light-off   #3a2f15
    pir cone    #2e7d32      label       #46566e   sub-label   #3c4a60
    title       #cdd9e8      subtitle    #5a6b80

  EASING (calcMode="spline")
    ease-in-out per segment:  0.4 0 0.6 1
    walk (ease-out arrival):  0.3 0 0.4 1   ;  linear hold: 0 0 1 1

  TIMING — single loop, dur="10s", repeatCount="indefinite".
    Share ONE keyTimes vocabulary across layers so phases stay in sync, e.g.
      walk-in 0.05-0.30 · light-on 0.34 · dwell -0.78 · vacancy fade 0.78-0.86 · reset 0.95-1
-->
<defs>
  <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
    <feGaussianBlur stdDeviation="5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <radialGradient id="foot" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#7fd1ff" stop-opacity="0.55"/>
    <stop offset="100%" stop-color="#7fd1ff" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="lampcast" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#ffd17a" stop-opacity="0.4"/>
    <stop offset="100%" stop-color="#ffd17a" stop-opacity="0"/>
  </radialGradient>
</defs>
````

- [ ] **Step 3: Verify it is valid XML**

Run: `cd .claude/skills/ha-automation-animations/reference && sed -n '/<defs>/,/<\/defs>/p' defs.svg | python3 -c "import sys,xml.dom.minidom as m; m.parseString('<svg xmlns=\"http://www.w3.org/2000/svg\">'+sys.stdin.read()+'</svg>'); print('VALID')"`
Expected: `VALID`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/ha-automation-animations/reference/defs.svg
git commit -m "feat(skill): add reusable defs + palette/easing notes"
```

---

## Task 3: Write layout.schema.md

**Files:**
- Create: `.claude/skills/ha-automation-animations/reference/layout.schema.md`

- [ ] **Step 1: Define the success check**

Documents every `layout.yaml` field, states units (meters), explains scaling to viewBox, and includes the full bedroom example so an author can copy-adapt. No TBDs.

- [ ] **Step 2: Write the file**

````markdown path=.claude/skills/ha-automation-animations/reference/layout.schema.md
# layout.yaml schema

One `layout.yaml` per area, in `packages/areas/{floor}/{area}/docs/`. Geometry is
**shared across all of that area's automation SVGs** — author it once, reuse it.

Coordinates are in **meters**, origin top-left, x→right, y→down (matches a top-down
floor plan). The author of the SVG maps meters to the `viewBox` (suggested scale:
~100 svg-units per meter, plus a margin band for the title and labels).

## Fields

| Key | Type | Meaning |
|-----|------|---------|
| `area` | string | Package key (e.g. `bedroom`). |
| `rooms[]` | list | Room rectangles. `{id, x, y, w, h, label?}`. First is the main room. |
| `furniture[]` | list | Static objects. `{id, room, x, y, w, h, label?}`. Coords relative to the area origin. |
| `sensors[]` | list | `{id, type, room, x, y, label?}`. `type` ∈ `pir`, `mmwave`, `door`, `contact`. Drives cone shape + color. |
| `lights[]` | list | `{id, room, x, y, w?, h?, kind, label?}`. `kind` ∈ `strip`, `bulb`, `group`. The animation target. |
| `door` | obj | `{room, x, w, side}`. `side` ∈ `top`/`bottom`/`left`/`right`. Person enters here. |
| `paths{}` | map | Named walk paths. Value = ordered list of points; a point is either a sensor/door `id` (string) or `{x, y}` (meters). |

## Example — bedroom

```yaml
area: bedroom
rooms:
  - {id: bedroom,  x: 0,   y: 0,   w: 4.1, h: 4.0}
  - {id: ensuite,  x: 4.2, y: 0,   w: 1.4, h: 2.2, label: ensuite}
  - {id: wardrobe, x: 4.2, y: 2.4, w: 1.4, h: 1.4}
furniture:
  - {id: bed, room: bedroom, x: 0.3, y: 0.3, w: 1.5, h: 0.9, label: bed}
sensors:
  - {id: pir,    type: pir,    room: bedroom, x: 2.0, y: 3.9, label: "PIR (entrance)"}
  - {id: mmwave, type: mmwave, room: ensuite, x: 0.7, y: 0.8, label: mmWave}
lights:
  - {id: stripe, room: bedroom, x: 0.3, y: 1.9, w: 1.5, kind: strip, label: "bed stripe"}
door: {room: bedroom, x: 1.6, w: 0.7, side: bottom}
paths:
  enter_to_bed: [door, {x: 1.5, y: 1.9}]
```

## Notes
- Add only what an animation will show. A room with no animated covers needs no window entry.
- One area, many SVGs: `presence-lighting.svg` and `humidifier.svg` both read this same file.
- If geometry is unknown, ask the user for room size + furniture/sensor/door positions
  rather than guessing — geometry cannot be inferred from automation YAML.
````

- [ ] **Step 3: Verify the embedded YAML parses**

Run: `cd .claude/skills/ha-automation-animations/reference && awk '/^```yaml$/{f=1;next}/^```$/{f=0}f' layout.schema.md | uv run python -c "import sys,yaml; yaml.safe_load(sys.stdin); print('YAML OK')"`
Expected: `YAML OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/ha-automation-animations/reference/layout.schema.md
git commit -m "feat(skill): document layout.yaml schema with bedroom example"
```

---

## Task 4: Write AUTHORING.md (the method + conventions + verify loop)

**Files:**
- Create: `.claude/skills/ha-automation-animations/reference/AUTHORING.md`

- [ ] **Step 1: Define the success check**

Captures the full authoring method end-to-end: how to read an automation into phases, the layer conventions (person/sensor/light/status), the learned bugs, and the mandatory Playwright verification loop with the exact gotchas (file: blocked, absolute screenshot path, reload-to-reset-t0). No TBDs; every gotcha is stated, not implied.

- [ ] **Step 2: Write the file**

````markdown path=.claude/skills/ha-automation-animations/reference/AUTHORING.md
# Authoring an automation animation

## 1. Read the automation into phases

Open the target automation YAML. Map trigger → condition → action to a timeline:

> walk in · sensor pulse · light on · dwell · (timeout) light off

Most presence-lighting automations share that shape. Covers = sun event → cover slides.
Humidifier = humidity drops → fan ramps. Pick 3–5 phases; keep the loop ~8–12s.

## 2. Build the static scene from layout.yaml

Read the area's `docs/layout.yaml` (see `layout.schema.md`). Draw, in order:
frame + title → room rectangles → furniture → light elements (off state) → sensors +
labels → door. Scale meters→viewBox (~100 units/m + a ~60-unit top band for the title).
Paste the `<defs>` block from `defs.svg`.

## 3. Add the animation layer

| Layer | How |
|-------|-----|
| Person | Blue dot (`#7fd1ff`) + radial `url(#foot)` glow, grouped. `animateMotion` along the walk path with `keySplines` ease-out arrival. Group `opacity` 0 while "outside" before/after. |
| Sensor trigger | Cone/zone polygon, `fill` PIR-green. Breathing `opacity` pulse (e.g. `0;0;0.40;0.12;0.40;0`) timed to entry — never a hard on/off flash. |
| Light on | Target element `fill` → `#ffd17a` with `calcMode="spline"`; add a `url(#lampcast)` ellipse over the room for spill; wrap the light in `filter="url(#glow)"`. |
| Status word | N stacked `<text>` rows at the SAME x/y, ONE visible per phase via opacity keyTimes. |

Share **one keyTimes vocabulary** across every `<animate>` so layers line up.

## Learned bugs (do not repeat)

- **tspan overlap:** status words as `<tspan>` sharing one text anchor render on top of
  each other. Use separate stacked `<text>` elements, one visible per phase.
- **Label inside a box:** status/labels placed at coordinates that fall inside a room box
  collide visually. Keep status in the top band (y≈40).
- **animateMotion snap:** without `keyPoints`+`keySplines`, the dot teleports between
  segments. Provide both, with a held segment (`0 0 1 1`) for the dwell.

## 4. Accessibility + resilience (always include)

- `viewBox` only, no hardcoded width/height.
- `role="img"`, a `<title>` and `<desc>`.
- `<style>@media (prefers-reduced-motion: reduce){ svg * { animation:none !important; } }</style>`

## 5. Verify (MANDATORY — do not skip)

Playwright cannot open `file:` URLs, so serve over http.

```bash
cd packages/areas/{floor}/{area}/docs
printf '<!doctype html><meta charset=utf-8><body style="background:#222"><img src="NAME.svg"></body>' > _preview.html
python3 -m http.server 8741   # run in background; note its cwd = this dir
```

Then with Playwright MCP:
1. `browser_navigate` → `http://localhost:8741/_preview.html` (path is relative to the
   server's cwd, which is the docs dir).
2. `browser_navigate` again to **reset the animation clock to t=0**.
3. For each phase: `browser_wait_for` the phase offset, then `browser_take_screenshot`
   with an **ABSOLUTE filename** (relative paths land in an unpredictable dir).
4. `Read` each screenshot. Confirm: all elements present, the light actually changes
   color, the sensor pulses, the person walks the path, the status word matches the
   phase, nothing overlaps or clips.
5. If wrong, fix the SVG and re-verify. Only when correct:

```bash
rm -f _preview.html *.png        # remove temp preview + screenshots
# kill the background http.server
```

## 6. Embed in the README

Under the matching "How It Works" subsection, add:

```html
<!-- svg:keep -->
<img src="docs/NAME.svg" alt="Animated diagram: <one-line behavior>">
<!-- /svg:keep -->
```

The `svg:keep` markers flag the block so a future `/ha-area-docs` regen preserves it.
(Auto-preservation in ha-area-docs is a separate follow-up; the markers are the contract.)
````

- [ ] **Step 3: Verify no placeholder tokens slipped in**

Run: `grep -nE "TBD|TODO|FIXME|fill in|\.\.\.$" .claude/skills/ha-automation-animations/reference/AUTHORING.md && echo "FOUND PLACEHOLDER — fix" || echo CLEAN`
Expected: `CLEAN`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/ha-automation-animations/reference/AUTHORING.md
git commit -m "feat(skill): add authoring method, learned bugs, verify loop"
```

---

## Task 5: Write SKILL.md

**Files:**
- Create: `.claude/skills/ha-automation-animations/SKILL.md`

- [ ] **Step 1: Define the success check**

Has YAML frontmatter (`name`, `description` with triggers) like the repo's other skills, a one-screen ordered checklist, and links the reference files by relative path. SKILL.md stays scannable — the detailed method lives in AUTHORING.md.

- [ ] **Step 2: Inspect an existing project skill for frontmatter shape**

Run: `sed -n '1,12p' .claude/skills/ha-area-docs/SKILL.md 2>/dev/null || find .claude/skills -name SKILL.md | head`
Expected: see the `name:`/`description:` frontmatter convention to mirror.

- [ ] **Step 3: Write the file**

````markdown path=.claude/skills/ha-automation-animations/SKILL.md
---
name: ha-automation-animations
description: Create animated SVG floor-plan diagrams of Home Assistant automations for area READMEs. Use when the user asks to "animate an automation", "add an animation to the README", "show how an automation works visually", "visualize presence/lighting/covers", or to diagram a room's automation behavior. One automation = one animated SVG, embedded in the area's README.
---

# HA automation animations

Hand-author a verified animated **SVG floor-plan** showing how one HA automation behaves
(top-down room: person walks in, sensors pulse, lights glow, timeout off). One automation
= one SVG, stored in `{area}/docs/` and embedded in the area README.

This skill is a **method**, not a generator. Read the automation, design the animation,
hand-write the SVG modeled on the reference, then verify it renders correctly.

## Reference files (read these first)

- `reference/presence-lighting.svg` — the gold render. Mirror its structure, palette, timing.
- `reference/defs.svg` — copy-paste `<defs>` (glow/foot/lampcast) + palette + easing notes.
- `reference/layout.schema.md` — the per-area `layout.yaml` geometry schema + bedroom example.
- `reference/AUTHORING.md` — full method, layer conventions, learned bugs, the verify loop.

## Checklist (create a TodoWrite item per step)

1. **Identify** the target area + automation. Read the automation YAML.
2. **Geometry:** open `{area}/docs/layout.yaml`. If missing, create it per `layout.schema.md`
   — ask the user for room size + furniture/sensor/door positions; never guess geometry.
3. **Author** the SVG per `AUTHORING.md`: phases → static scene → animation layer →
   a11y/reduced-motion. Paste `defs.svg`. Model on `presence-lighting.svg`.
4. **Verify (mandatory):** serve over http + Playwright screenshot each phase + Read +
   confirm (full loop in `AUTHORING.md` §5). Fix and re-verify until correct.
5. **Embed** in the README under the matching "How It Works" subsection, wrapped in
   `<!-- svg:keep -->` markers (`AUTHORING.md` §6).
6. **Clean up** temp preview files + server, then commit the SVG + README + any new layout.yaml.

## Notes
- SMIL only (GitHub renders SVG via `<img>` — no CSS/JS). `viewBox`, no width/height.
- Push to deploy is NOT needed for README SVGs (they render from the repo on GitHub),
  but follow the repo's normal branch/PR rules for the commit.
````

- [ ] **Step 4: Verify frontmatter parses**

Run: `awk '/^---$/{c++;next} c==1{print} c==2{exit}' .claude/skills/ha-automation-animations/SKILL.md | uv run python -c "import sys,yaml; d=yaml.safe_load(sys.stdin); assert d['name']=='ha-automation-animations' and 'description' in d; print('FRONTMATTER OK')"`
Expected: `FRONTMATTER OK`

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/ha-automation-animations/SKILL.md
git commit -m "feat(skill): add ha-automation-animations SKILL.md entry point"
```

---

## Task 6: Back-fill bedroom layout.yaml

**Files:**
- Create: `packages/areas/first-floor/bedroom/docs/layout.yaml`

- [ ] **Step 1: Define the success check**

A real `layout.yaml` for the bedroom matching the geometry implied by the already-built
`presence-lighting.svg` (bed top-left, PIR at entrance, mmWave in ensuite, stripe under
bed, door bottom-center). Parses as YAML and conforms to the schema. NOTE: exact meter
dimensions should be confirmed with the user against the real room; the example values
below are the documented placeholders from the schema and MUST be confirmed before this
task is marked complete.

- [ ] **Step 2: Confirm real dimensions with the user**

Ask the user for the bedroom's real dimensions and bed/sensor/door positions (the spec
calls out that geometry is hand-fed and cannot be guessed). Use their numbers; if they
defer, use the schema example values and note it inline as approximate.

- [ ] **Step 3: Write the file**

```yaml
# Bedroom geometry — shared by all bedroom automation animations.
# Meters, origin top-left. Confirm against the real room (see plan Task 6 step 2).
area: bedroom
rooms:
  - {id: bedroom,  x: 0,   y: 0,   w: 4.1, h: 4.0}
  - {id: ensuite,  x: 4.2, y: 0,   w: 1.4, h: 2.2, label: ensuite}
  - {id: wardrobe, x: 4.2, y: 2.4, w: 1.4, h: 1.4}
furniture:
  - {id: bed, room: bedroom, x: 0.3, y: 0.3, w: 1.5, h: 0.9, label: bed}
sensors:
  - {id: pir,    type: pir,    room: bedroom, x: 2.0, y: 3.9, label: "PIR (entrance)"}
  - {id: mmwave, type: mmwave, room: ensuite, x: 0.7, y: 0.8, label: mmWave}
lights:
  - {id: stripe, room: bedroom, x: 0.3, y: 1.9, w: 1.5, kind: strip, label: "bed stripe"}
door: {room: bedroom, x: 1.6, w: 0.7, side: bottom}
paths:
  enter_to_bed: [door, {x: 1.5, y: 1.9}]
```

- [ ] **Step 4: Verify it parses and lints**

Run: `uv run python -c "import yaml; yaml.safe_load(open('packages/areas/first-floor/bedroom/docs/layout.yaml')); print('YAML OK')" && uv run yamllint packages/areas/first-floor/bedroom/docs/layout.yaml`
Expected: `YAML OK` then yamllint passes (no errors).

- [ ] **Step 5: Commit**

```bash
git add packages/areas/first-floor/bedroom/docs/layout.yaml
git commit -m "feat(bedroom): add layout.yaml geometry for automation animations"
```

---

## Task 7: Embed the SVG in the bedroom README

**Files:**
- Modify: `packages/areas/first-floor/bedroom/README.md` (the `### Lighting` subsection under `## How It Works`)

- [ ] **Step 1: Define the success check**

The bedroom README shows the animation inline under `### Lighting`, wrapped in
`svg:keep` markers, with descriptive alt text. The image path is relative to the README
(`docs/presence-lighting.svg`).

- [ ] **Step 2: Locate the insertion point**

Run: `grep -n "### Lighting" packages/areas/first-floor/bedroom/README.md`
Expected: the line number of the `### Lighting` heading (insert the embed immediately after it).

- [ ] **Step 3: Insert the embed after the `### Lighting` heading**

Use Edit to add, immediately after the `### Lighting` line:

```html

<!-- svg:keep -->
<img src="docs/presence-lighting.svg" alt="Animated floor plan: person enters the bedroom, PIR pulses, the bed stripe glows on while dark, then turns off after a 10-minute vacancy">
<!-- /svg:keep -->
```

- [ ] **Step 4: Verify the embed is present and well-formed**

Run: `grep -c "svg:keep" packages/areas/first-floor/bedroom/README.md` → expected `2` (open+close).
Run: `grep -n 'src="docs/presence-lighting.svg"' packages/areas/first-floor/bedroom/README.md` → expected one match.

- [ ] **Step 5: Visually confirm the README renders (GitHub-style)**

Render the README locally (or push the branch and open the file on GitHub) and confirm the
animation appears under Lighting and loops. Per repo convention, README SVGs render from the
repo on GitHub without an HA push; this is a docs change, no HA reload needed.

- [ ] **Step 6: Commit**

```bash
git add packages/areas/first-floor/bedroom/README.md
git commit -m "docs(bedroom): embed presence-lighting animation under Lighting"
```

---

## Task 8: Final skill smoke check

**Files:** none (validation only)

- [ ] **Step 1: Confirm the skill is discoverable + complete**

Run: `ls .claude/skills/ha-automation-animations .claude/skills/ha-automation-animations/reference`
Expected: `SKILL.md` + `reference/` containing `presence-lighting.svg`, `defs.svg`, `layout.schema.md`, `AUTHORING.md`.

- [ ] **Step 2: Confirm SKILL.md links resolve**

Run: `cd .claude/skills/ha-automation-animations && for f in reference/presence-lighting.svg reference/defs.svg reference/layout.schema.md reference/AUTHORING.md; do test -f "$f" && echo "OK $f" || echo "MISSING $f"; done`
Expected: four `OK` lines, no `MISSING`.

- [ ] **Step 3: Dry-run mention (no code)**

Confirm by reading SKILL.md that invoking it on a new area would: read layout.yaml (or create it), author per AUTHORING.md, verify via Playwright, embed with svg:keep, commit. No execution needed — this is a read-through sanity check that the method is self-contained.

---

## Self-Review

- **Spec coverage:** style (Task 1 ref + AUTHORING §3) ✓ · one-automation-per-SVG (SKILL + AUTHORING) ✓ · guided hand-authoring not generator (whole plan, no script) ✓ · layout.yaml meters (Task 3,6) ✓ · SMIL/viewBox/a11y (Task 4 §4, Task 5 notes) ✓ · mandatory verify (Task 4 §5, Task 5 step 4) ✓ · docs/ storage + inline embed (Task 7) ✓ · svg:keep collision marker (Task 4 §6, Task 7) ✓ · project skill name (Task 5) ✓ · bedroom adopted as reference + first embed (Tasks 1,6,7) ✓ · file:-blocked + absolute-screenshot-path gotchas (Task 4 §5) ✓.
- **Placeholders:** none — every file's content is given in full. Task 6 flags meter values as needing user confirmation (explicit step), not a silent TBD.
- **Consistency:** ref IDs `glow`/`foot`/`lampcast` consistent across defs.svg, AUTHORING, and the reference SVG. `svg:keep` marker spelled identically in Task 4 and Task 7. Port `8741` consistent with the verify loop used to build the reference.
- **Follow-ups (out of scope, noted in spec):** wire ha-area-docs to auto-preserve svg:keep; backfill other areas; optional knowledge leaf for the Playwright file:/screenshot gotcha.
