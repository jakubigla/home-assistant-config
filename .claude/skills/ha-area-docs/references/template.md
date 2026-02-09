# README Template

Use this structure when generating area documentation. Omit sections that have no content.
Write in a functional, human-readable style — explain behavior, not YAML structure.

---

```markdown
# {Area Name}

> {One-line summary of what this room does automatically}

**Package:** `{key}` | **Path:** `packages/areas/{floor}/{area}/`

## How It Works

{Narrative description of the room's automatic behavior. Group by theme if the room has
multiple concerns (lighting, climate, covers, media). Use subsections (###) for each theme
if there are 2+ distinct behaviors. For simple rooms with just one behavior, no subsections needed.}

### {Theme: e.g., Lighting}

{Describe how lighting works in this room — what triggers it, what controls brightness,
how presence/darkness interact. Mention delays and thresholds in natural language.
Include switch/button mappings as a table if applicable.}

### {Theme: e.g., Climate}

{Describe climate control — humidity targets, fan speeds, time-of-day logic, etc.}

### {Theme: e.g., Covers}

{Describe cover/curtain behavior — when they open/close, seasonal logic, etc.}

## Gotchas

- {Non-obvious behavior, edge case, or design decision worth knowing}
- {Things that might surprise someone editing the automations}
- {Important interactions between automations in this package}

## Entities

{Compact reference of the key entities this package defines or uses. Group logically.}

**Lights:** `light.{group}` ({N} bulbs: `light.a`, `light.b`, ...)
**Sensors:** `binary_sensor.{name}` — {what it detects, one-line}
**State:** `input_boolean.{name}` — {purpose}
**Scripts:** `script.{name}` — {what it does}

## Dependencies

{Entities from other packages referenced by this area's automations/templates.}

- `{entity_id}` — {what it is, which package it comes from}

## File Index

| File | Purpose |
|------|---------|
| `config.yaml` | {Brief description} |
| `automations/{name}.yaml` | {Brief description} |
| `lights/{name}.yaml` | {Brief description} |
| `templates/binary_sensors/{name}.yaml` | {Brief description} |
```
