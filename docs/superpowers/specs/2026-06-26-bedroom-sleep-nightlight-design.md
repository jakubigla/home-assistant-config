# Bedroom Sleep Nightlight — Design

**Date:** 2026-06-26
**Area:** `packages/areas/first-floor/bedroom/`
**Status:** Approved, ready for implementation plan

## Problem

During sleep, a night trip to the ensuite is made in full darkness. The user
wants the bed stripe to glow faintly so they can walk to the ensuite, and again
to walk back, without ever turning on a real light or waking a partner.

## Behavior

Two phases in one automation.

### Outbound (heading to the ensuite)

Either bedside motion sensor fires while the room is dark and asleep → bed
stripe to 1% warm for a fixed 5 s pulse, then off. 5 s is enough to clear the
bed and reach the ensuite door; the door opening then hands off to the return
phase.

### Return (coming back from the ensuite)

The ensuite door opens → bed stripe to 1% warm, held a minimum of 5 s, then off
once **both** bedside motion sensors read no motion (you have climbed back in
and settled). A 2 min hard timeout forces it off regardless, so a stuck sensor
can never leave the stripe lit all night.

## Gate (all must hold at trigger time)

| Entity | Required state | Why |
|---|---|---|
| `binary_sensor.sleeping_time` | `on` | Sleep-time only — never daytime |
| `light.bedroom_non_bed` | `off` | leds + main + reflectors all off |
| `light.bed_stripe` | `off` | Outbound only — don't re-pulse an already-lit stripe |
| `light.bedroom_bed` | `off` | bedside reading lights off |
| `media_player.bedroom_tv` | `off` | TV off |
| `input_boolean.bedroom_movie_mode` | `off` | Not watching a movie |

The return phase uses the same gate **minus `light.bed_stripe`** — by the time
the door opens the outbound pulse has ended and the stripe is off, but a strict
`bed_stripe == off` check is unnecessary and would race the prior phase.

## Entities (live-verified 2026-06-26)

- Motion: `binary_sensor.bedroom_jakub_side_motion`,
  `binary_sensor.bedroom_sona_side_motion_occupancy`
  — **the two sides are named differently**; the Sona side is the `_occupancy`
  variant. Do not assume a symmetric `bedroom_sona_side_motion`; it does not
  exist (HA returns "Entity not found").
- `light.bed_stripe` — target
- `light.bedroom_non_bed` — group of leds + main + reflectors (everything
  except bed lights and the stripe)
- `light.bedroom_bed` — group of `light.bedroom_jakub` + `light.bedroom_sona`
- `binary_sensor.sleeping_time`
- `media_player.bedroom_tv`
- `input_boolean.bedroom_movie_mode`
- `binary_sensor.ensuite_door`

Light command at both ends:

```yaml
action: light.turn_on
data:
  brightness_pct: 1
  color_temp_kelvin: 2700
target:
  entity_id: light.bed_stripe
```

## Placement

New file: `packages/areas/first-floor/bedroom/automations/bedroom_sleep_nightlight.yaml`.

`bedroom_presence.yaml` is **not** modified. Its stated invariant is "NEVER
auto-on during sleeping_time"; this feature is the deliberate, isolated
exception. Keeping it in its own file preserves that invariant cleanly and keeps
each automation single-purpose.

## Automation shape

- `mode: restart`, `max_exceeded: silent`
- Two triggers:
  - `trip` — `binary_sensor.bedroom_jakub_side_motion` OR
    `binary_sensor.bedroom_sona_side_motion_occupancy` off→on
  - `return` — `binary_sensor.ensuite_door` off→on
- `choose` on trigger id:
  - **trip branch** — gate conditions → stripe 1%@2700K → `delay: 5s` →
    stripe off
  - **return branch** — gate conditions (minus bed_stripe) → stripe 1%@2700K →
    `delay: 5s` (minimum hold) → `wait_template` for both side sensors `off`
    with `timeout: 00:02:00` and `continue_on_timeout: true` → stripe off

`mode: restart`: a second motion event during the 5 s outbound pulse restarts
the pulse; the door opening mid-pulse cancels the run and the return branch
takes over. Off is unconditional at the end of both branches — the stripe is
never left lit by this automation.

The "both side sensors off" wait uses `wait_template`:

```yaml
wait_template: >
  {{ is_state('binary_sensor.bedroom_jakub_side_motion', 'off')
     and is_state('binary_sensor.bedroom_sona_side_motion_occupancy', 'off') }}
timeout: "00:02:00"
continue_on_timeout: true
```

`wait_template` checks state on entry. That is fine here because the wait is
preceded by the 5 s `delay` and is gated on motion you just walked through — if
both sides happen to already read off at entry, walking back to bed has finished
and immediate off is correct. If either is still on, it waits for the off edge.
(See
[wait-template-state-on-entry-race](../../../knowledge/ha-scripting/wait-template-state-on-entry-race.md)
— the race only bites when a state-wait follows a command that *changes* the
waited entity; here nothing this automation does drives the motion sensors.)

## Edge cases

- **Partner turns on a real light mid-sequence** — the next trigger's gate fails
  (`bedroom_non_bed`/`bedroom_bed` now on), so no new nightlight. An in-flight
  pulse finishes its short off; harmless at 1%.
- **Stuck bedside sensor on return** — 2 min timeout forces the stripe off.
- **HA restart mid-sequence** — the stripe may be left at 1%. The existing
  tier-2 `bedroom_vacancy_timeout` and the occupancy-latch logic sweep all
  bedroom lights (incl. `bed_stripe`) on vacancy. Acceptable: 1% is effectively
  invisible and self-corrects on next vacancy. No extra startup-sync branch
  needed for a transient 1% glow.
- **Stripe color from a prior scene** — every command forces `color_temp_kelvin:
  2700`, so the pulse is always warm regardless of the stripe's last color.

## Out of scope (YAGNI)

- No per-side directionality (knowing which side got up).
- No brightness ramp / fade — a flat 1% is enough.
- No startup-sync branch — transient 1% glow doesn't justify it.
- No new template sensors or input_booleans — pure automation off existing
  entities.

## Verification

- `just check` (HA config check) passes.
- Push → reload core config → check logs (per
  [reload-after-push](../../../knowledge/ops/reload-after-push.md)).
- Live trace: simulate side-motion during sleeping_time with all lights/TV off →
  confirm 5 s pulse. Trip `ensuite_door` → confirm hold-until-quiet + 2 min cap.
- No automated tests (HA YAML automation).

## Knowledge layer

No new leaf. Reuses known patterns (gate conditions, `mode: restart`,
`wait_for_trigger` timeout). The per-side motion-sensor naming asymmetry
(`bedroom_sona_side_motion_occupancy` vs `bedroom_jakub_side_motion`) is
recorded here in the spec; promote to a leaf only if it bites a second time.
