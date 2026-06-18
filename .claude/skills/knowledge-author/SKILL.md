---
name: knowledge-author
description: >
  Use to capture knowledge into the knowledge/ layer — when the user says "capture this",
  "add a leaf for X", "document this gotcha", when a non-obvious gotcha/correction surfaces, when
  a procedure repeats 3+ times, or when knowledge-router finds no leaf for a load-bearing topic.
  Owns the relevance gate, dedup, frontmatter, INDEX rebuild, validation, and commit. Never patch
  leaves inline.
---

# Knowledge Author

Single write path for the knowledge layer. Everything routes through here — no inline leaf edits.

## Entry points

- **User intent:** "capture this", "add a leaf for X", "document this gotcha".
- **Continuous improvement:** non-obvious gotcha discovered, user correction received, or a
  procedure run 3+ times across sessions. Invoke by judgment.
- **Router handoff:** `knowledge-router` found no leaf for a load-bearing topic.

## Procedure

0. **Rent test (gate — reject before writing).** A leaf is loaded into context on every route that
   matches it; bloat is a tax paid by every future session. A leaf must beat scanning the repo.
   Capture ONLY if it passes all three:
   - **Non-discoverable by scan** — grep/reading the obvious file won't surface it
     (behavioral/timing/API quirk, a 3rd/4th place no grep reaches, a correction to a wrong
     assumption).
   - **Costs real time or a mistake** if unknown next time.
   - **Not rederivable in <3 tool calls** by reading the named file.

   If the knowledge is **a code change you just made**, the code is the record — do NOT also write a
   leaf. If it's rederivable by scanning, skip. When a candidate fails the gate, say so and capture
   nothing — a leaf that doesn't beat scanning is a net loss.

0b. **Boundary check (where it belongs — leaf vs always-on rules).** A leaf is loaded *on demand*
   (only when the router matches it). The project's agent-instructions file (CLAUDE.md / AGENTS.md /
   GEMINI.md) is loaded *every session, whole*. Route each fact by how often it's needed:
   - **Needed every session regardless of task** (reach-the-service rules, hard prohibitions,
     architecture map, constantly-used commands, conventions applied on most edits) → belongs in the
     always-on instructions file, NOT a leaf.
   - **Task-scoped** (a gotcha with a symptom, a multi-step procedure, per-integration/per-device
     specifics — anything a router would fetch reactively) → leaf.
   - **No fact lives full in both.** If it's already in the instructions file, don't also write a
     leaf (that's the duplication that bloats both). If a leaf is really an always-on rule, propose
     moving it to the instructions file instead of writing the leaf.

1. **Clarify intent.** One-line summary of the topic. New knowledge or a correction to an existing
   leaf?

2. **Dedup scan.** Read `knowledge/INDEX.md` (the flat table) and match intent against the
   **Triggers** column — `before:` (proactive) and `symptom:` (reactive). Candidates → load the top
   1–3 leaf bodies and ask the user: edit existing or write new? No candidates → proceed as new.
   **Never pick between overlapping candidates silently** — if the overlap is fuzzy, load the bodies
   and ask.

3. **Draft frontmatter, confirm with the user:**
   ```yaml
   ---
   summary: <one-line, ≤120 chars — what it covers, not why>
   canonical_path: <optional — only if this is supportive context for a named sibling>
   before_action:
     - About to <verb> <object>
   on_symptom:
     - "<error or state phrase the user might paste>"
   ---
   ```
   At least one trigger required. Triggers must NOT embed leaf paths. **Re-draft cap: 2.** After two
   rejections, ask the user to author the frontmatter directly — don't keep guessing.

4. **Write the body — condense, don't narrate.** The leaf is read on every matching route; write it
   to be read fast.
   - **Rule first, evidence parenthetical.** Lead each gotcha with the imperative rule in **bold**.
     The commit/incident that surfaced it is a terse aside, not the subject.
   - **One gotcha = one bullet.** Don't split a rule across bullets or pad with discovery
     chronology.
   - **Drop:** articles/filler, context the reader already has, blow-by-blow narrative, duplicated
     identifiers. **Keep** exact paths, entity ids, services, error strings.
   - **Budget:** ~70-line soft-cap, and hard-wrap body source at 100 chars (the validator warns on
     both). Wrapping is honest formatting — a 400-char one-liner games the line count and is
     unreadable in diffs. If condensing pushes a leaf past its peers, you're narrating — re-condense
     before commit. New facts justify lines; retelling does not.
   - Reference siblings by name, not path. New leaf → `knowledge/<bucket>/<kebab-topic>.md`. Edit →
     patch in place.

5. **Group the leaf** (new leaf). Buckets are subdirectories under `knowledge/`, discovered at build
   time — there is NO fixed set. List the existing dirs and group by fit: if the leaf clearly
   belongs with an existing group, put it there. **Don't force a fit** — if no existing bucket
   genuinely matches (or there are none yet), create a new directory whose name captures the
   grouping. The name is a kebab-case noun for the domain; let the leaf decide it, don't bias toward
   what already exists. New leaf path: `knowledge/<bucket>/<kebab-topic>.md`.

6. **Rebuild:** `just knowledge-index` regenerates the single `knowledge/INDEX.md` table from
   frontmatter. (Pre-commit also rebuilds + re-stages it, so the committed table can't drift — but
   run it now to review the row.)

7. **Validate:** `just knowledge-check` (frontmatter schema, table drift, skill pointers). Failure →
   surface the error, fix, re-run. Never commit broken.

8. **Commit:** `git add knowledge/ && git commit -m "feat(knowledge): <leaf-name> leaf"`. Body: 1–3
   lines on *why captured* (correction source, repeat count, gotcha origin). One commit per leaf.

## Red flags — stop and reconsider

| Thought | Reality |
|---------|---------|
| "This is worth recording just in case" | Run the rent test. Rederivable-by-scan or already-in-code → capture nothing. |
| "I'll also write a leaf for the fix I just made" | The code IS the record. A leaf that restates code is dead weight. |
| "This rule is important, I'll put it in a leaf" | Needed every session? It's an always-on rule → instructions file, not a leaf. No fact full in both. |
| "Topic feels unique — skip dedup" | The table scan is cheap. Skipping is how leaves duplicate. |
| "User didn't ask — I'll author silently" | Confirm intent + frontmatter first. Silent writes drift. |
| "Two candidate leaves overlap — I'll pick" | Ask the user. Never pick silently. |
| "User rejected frontmatter twice — try once more" | Re-draft cap is 2. After that, the user authors directly. |
| "I'll write the full story so it's clear" | Leaf loads every route. Rule first, evidence parenthetical. Condense. |
| "Validator warned on length — commit anyway" | Length warn = you're narrating. Re-condense, don't override. |
| "INDEX check failed — commit anyway" | Never. Fix the leaf or revert. |
| "Just one line — patch the leaf inline" | Route through this skill. Single write path = no drift. |
