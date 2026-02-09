---
name: ha-area-docs
description: >
  Generate or update comprehensive README.md documentation for Home Assistant area/room packages.
  Use when the user asks to "document a room", "generate area docs", "create README for an area",
  "update room documentation", or any request to document HA area packages. Triggers on:
  document/docs for rooms, areas, packages, or floors.
---

# HA Area Documentation Generator

Generate a human-readable `README.md` at the root of each area package directory
(e.g., `packages/areas/first-floor/bedroom/README.md`).

## Workflow

1. **Identify target areas** — if user specifies a room, document that one. If "all" or unspecified,
   iterate over every area under `packages/areas/`.
2. **Read all YAML files** in the area package: `config.yaml`, `automations/*.yaml`, `lights/*.yaml`,
   `templates/**/*.yaml`, `scripts/*.yaml`, `media_players/*.yaml`, and any other subdirectories.
3. **Understand the behavior** — don't just list YAML fields. Understand how the room actually works
   from the user's perspective. What happens when you walk in? What do the switches do? When do
   covers close? What are the edge cases?
4. **Write `README.md`** at the area package root using the template in
   [references/template.md](references/template.md).
5. **Delete old automation READMEs** — remove any `automations/README.md` files since they are
   superseded by the new package-level README.

## What to Focus On

### Functional behavior (primary)

- What does this room do automatically? Describe the user experience, not the YAML.
- Group behaviors by theme (lighting, climate, covers, media) — explain each as a narrative.
- Call out design decisions: why a delay is 15 seconds instead of 5, why override exists, etc.
- Note gotchas, edge cases, and non-obvious interactions.

### Technical reference (secondary, condensed)

- Entity IDs inline where useful (in backticks), but don't list every trigger/condition/action.
- A compact file index at the end so people can find the right YAML to edit.
- Cross-area dependencies — what entities from other packages does this area use?

## What NOT to Do

- Do NOT list every trigger, condition, and action for each automation
- Do NOT include automation IDs or UUIDs
- Do NOT create per-automation detail sections with Triggers/Conditions/Actions breakdowns
- Do NOT use tables for automation summaries with ID/Mode columns
- Do NOT write verbose "example scenarios"
- Do NOT duplicate information — if a behavior is explained in the narrative, don't repeat it in a table

## Writing Style

- Write for a human who wants to understand how the room behaves, not debug YAML
- Use natural language paragraphs for behavior descriptions
- Use tables only for structured mappings (button → action, time → setting)
- Use bullet lists for quick-reference items
- Keep the whole README scannable — someone should grasp the room in 30 seconds
- Entity IDs in backticks, but only when referencing them adds value
- Be concise — a smaller README that captures the essence is better than a comprehensive one that nobody reads
