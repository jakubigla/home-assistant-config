# Combined 3-Sensor Drip Soil Gate — Design

**Date:** 2026-06-18
**Status:** Approved, pending implementation
**Area:** `packages/areas/outdoor/garden/`

## Problem

A single drip irrigation line runs through three flowerbeds, each with its own Tuya
Zigbee soil-moisture probe:

- `sensor.pergola_left_flowerbed_soil_moisture`
- `sensor.pergola_right_flowerbed_soil_moisture`
- `sensor.sona_flowerbed_soil_moisture`

Because one line waters all three beds at once, the skip/run decision must combine all
three into a single verdict.

The current drip skip sensor (`binary_sensor.garden_drip_should_skip` in
`templates/garden_should_skip_irrigation.yaml`) references `sensor.garden_soil_moisture`,
which **does not exist**. Its float guard `(soil | float(-1)) > 65` resolves to `-1`, so
the soil term is permanently `false` — soil never contributes to the skip decision today.

## Constraints / Known facts

- **sona is structurally wetter** — it has more drip emitters per bed, so it normally
  reads higher than the pergola beds. A naive MAX cap on all three would let sona alone
  permanently veto watering even when the pergola beds are dry.
- Tuya capacitive probes report relative `%` (0–100, ±3–5%), not calibrated VWC. Trend
  matters more than absolute value.
- Probes are outdoor Zigbee → expect occasional `unavailable` / `unknown` / pairing noise.
- Reference bands: <30% dry, 40–70% ideal, >85% saturated.

## Decisions (locked during brainstorming)

1. **Combining rule = hybrid "driest-wins + saturation cap".**
2. **sona handling = option B:** sona is included in the driest-wins trigger but **excluded
   from the saturation cap**. Sona can signal genuine drought but can never false-skip the
   pergola beds with its normal wetness.
3. **Thresholds:** `DRY = 50`, `SAT = 85`.
4. **Sensor failure = fail-safe A:** drop invalid probes, compute from the valid ones; if
   all three are invalid, the helper is `unknown` and the caller falls back to rain/season
   gating only.
5. **Integration = option A:** replace the dead `soil_wet` term in `garden_drip_should_skip`
   with the new combined-soil verdict; keep `not in_season`, `raining`, `rain_mm >= 3` as
   independent OR-terms.

## Architecture

All work lives in `packages/areas/outdoor/garden/templates/garden_should_skip_irrigation.yaml`.
No automation changes — `garden_seasonal_irrigation` already computes
`run_drip = drip_today and not drip_skip` and reads `binary_sensor.garden_drip_should_skip`.

### Component 1 — new `binary_sensor.garden_drip_soil_skip`

Combined soil verdict for the drip line.

```
PROBES = [pergola_left, pergola_right, sona]   # *_soil_moisture
CAP_PROBES = [pergola_left, pergola_right]      # sona EXCLUDED

valid(s)      = state not in ['unknown','unavailable','none',''] and is a number
valid_set     = [float(s) for s in PROBES if valid(s)]
cap_valid_set = [float(s) for s in CAP_PROBES if valid(s)]

# fail-safe: no valid probes at all → state = 'unknown'
if valid_set is empty: state = unknown

driest  = min(valid_set)
wettest = max(cap_valid_set) if cap_valid_set else (-1)   # no valid cap probe → cap can't trip

soil_skip = (driest >= DRY) or (wettest >= SAT)
```

- `driest >= 50` → thirstiest bed already moist → skip.
- `wettest >= 85` → a pergola bed is drowning → skip.
- sona dry pulls `driest` down → triggers a run. sona wet only raises `driest`/is irrelevant
  to the cap → never false-skips.

**Attributes (for debugging):**
- `driest` — min across valid probes
- `wettest` — max across valid cap probes (pergola L/R)
- `valid_count` — number of valid probes
- `reason` — one of `driest_moist`, `pergola_saturated`, `soil_dry_ok`, `no_valid_probes`

**Thresholds** declared once as Jinja vars at the top of the state template
(`{% set DRY = 50 %}`, `{% set SAT = 85 %}`) so they are tunable in one place.

### Component 2 — modified `binary_sensor.garden_drip_should_skip`

Replace the phantom `soil_wet` term:

```
{% set drip_soil_skip = is_state('binary_sensor.garden_drip_soil_skip', 'on') %}
{{ not in_season or is_raining or rain_mm >= 3 or drip_soil_skip }}
```

- `is_state(..., 'on')` is `false` when the helper is `unknown` (all probes dead) → soil
  ignored, rain/season still gate. This realises fail-safe A at the caller.
- `reason` attribute extended: add a `soil_skip` branch (surface the helper's own reason).

### Component 3 — legacy `binary_sensor.garden_should_skip_irrigation`

This alias currently mirrors the (broken) shared logic. Update it to mirror the **drip**
logic so the alias stays honest. **Lawn skip (`garden_lawn_should_skip`) is unchanged** —
no probe covers the lawn; it keeps rain/season gating only.

## Data flow

```
pergola_left  ─┐
pergola_right ─┼─> binary_sensor.garden_drip_soil_skip ─┐
sona          ─┘                                        │
binary_sensor.raining ──────────────────────────────────┤
sensor.garden_rain_accumulation ────────────────────────┼─OR─> garden_drip_should_skip
month (season May–Sep) ──────────────────────────────────┘            │
                                                                       v
                                          garden_seasonal_irrigation (run_drip = drip_today and not skip)
```

## Failure handling

| Scenario | Behavior |
|---|---|
| 1–2 probes dead | Compute `driest`/`wettest` from remaining valid probes |
| sona dead | driest from pergola L/R; cap unaffected (sona never in cap) |
| both pergola dead, sona alive | driest = sona; cap_valid empty → `wettest=-1` → cap can't trip (only drown-protection lost, drought-protection intact) |
| all 3 dead | helper = `unknown` → drip skip falls back to rain + season only |

Battery-low alerting is **out of scope** for this change (follow-up: reuse the
`garden_valve_offline_alert` pattern for probe batteries).

## Verification

1. **Dry-run via `/api/template`** before push — render the helper expression with:
   - live values (expect today: driest=82 → skip)
   - mocked one-dry (driest=35 → run)
   - mocked pergola-saturated (wettest=88 → skip)
   - mocked all-dead (→ unknown → fall back)
2. After push: `template.reload`, then confirm `binary_sensor.garden_drip_soil_skip` state +
   attributes, and that `garden_drip_should_skip` flips with it. (see **reload-after-push**)
3. No dashboard card involved; no Playwright needed for this change.

## Today's behavior sanity check

`L=82, R=84, sona=90` → valid_set all → `driest=82 ≥ 50` → **skip**.
`wettest=max(82,84)=84 < 85` → cap not tripped, but driest already skips. ✅ Beds soaked,
don't water — correct.

## Out of scope

- Probe battery-low alerts.
- Lawn soil gating (no lawn probe; mower would hit one).
- Per-sensor calibration offsets (rejected in favor of sona-cap-exclusion).
- ET / forecast-based smart gating (possible future via the `dynamic_adjust` hook).

## Knowledge-layer follow-up

The `garden-irrigation-schedule` leaf states skip gating uses `sensor.garden_soil_moisture`
and ">65%". After implementation, update that leaf: real probes are
`*_flowerbed_soil_moisture`, drip gate uses the 3-sensor hybrid (DRY=50/SAT=85, sona
excluded from cap), lawn still has no probe. Invoke `knowledge-author`.
