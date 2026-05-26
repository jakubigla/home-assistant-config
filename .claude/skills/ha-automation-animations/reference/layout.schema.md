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
