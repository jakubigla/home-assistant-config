# Bedroom occupancy-driven lights — design

**Date:** 2026-06-25
**Area:** `packages/areas/first-floor/bedroom`

## Problem

The bedroom lights automation (`bedroom_presence.yaml`) and whole-group auto-off
(`bedroom_vacancy_timeout.yaml`) both key off `binary_sensor.bedroom_entrance_presence`
(the FP2 entrance sensor). That sensor drops presence when you lie still in bed, so
"still in bed" is misread as "room vacant" — the auto-off timers can fire while the room
is occupied.

A new in-room mmWave sensor, `binary_sensor.bedroom_occupancy` ("Bedroom Presence
Occupancy"), reports true occupancy through stillness. This design makes occupancy the
truth source while staying **night-safe**: lights must never auto-on during sleep, and a
re-latch or HA restart at 3 a.m. must not wake the occupant.

## Sensors / entities (verified live)

| Entity | Role |
|---|---|
| `binary_sensor.bedroom_occupancy` | NEW in-room mmWave presence (sees stillness) |
| `binary_sensor.bedroom_entrance_presence` | FP2 entrance — fast on-edge, drops on stillness |
| `binary_sensor.sleeping_time` | global sleep gate |
| `binary_sensor.bedroom_is_dark` | darkness gate |
| `input_boolean.bedroom_movie_mode` | suppresses auto-on |
| `light.bed_stripe` | bedside strip — the auto-on light |
| `light.bedroom` (group), `light.bedroom_leds`, `light.bedroom_main`, `light.bedroom_reflectors` | whole-group auto-off targets |

## Architecture

A latch `input_boolean.bedroom_occupied` decouples downstream lighting from the noisy raw
sensors. Entry on either sensor; exit only when **both** are clear for a debounce window.
A watchdog clears a stuck latch. Two existing automations are rewired to read the latch
instead of the bare entrance sensor.

### Component 1 — `bedroom_occupancy_state_machine.yaml` (NEW)

Mirrors the proven `ensuite_occupancy_state_machine.yaml` pattern. `mode: restart`,
`max_exceeded: silent`.

- **New helper:** `input_boolean.bedroom_occupied` (in `config.yaml`)
- **Entry** (trigger id `entry`): `bedroom_entrance_presence` off→on **OR**
  `bedroom_occupancy` off→on → latch ON
- **Exit** (trigger id `exit`): both `bedroom_entrance_presence` AND `bedroom_occupancy`
  off for **60 s** → re-check both still off (mid-sequence condition gate) → latch OFF
- **Watchdog** (trigger id `watchdog`): latch ON for **30 min** + not(`bedroom_occupancy`
  on) → force latch OFF (covers HA restart / missed off-edge / sensor unavailable)

### Component 2 — `bedroom_presence.yaml` (REWIRE)

Trigger source becomes `input_boolean.bedroom_occupied` on/off instead of bare entrance.

- **On entry (latch OFF→ON):**
  - `sleeping_time` **OFF** + `bedroom_is_dark` on + `light.bedroom` off + movie off →
    `light.bed_stripe` 50 % / 2951 K (daytime path)
  - `sleeping_time` **ON** → **do nothing** (never auto-on at night)
- **On exit (latch ON→OFF) for 5 min** → `light.bed_stripe` off (tier 1, see below)

### Component 3 — `bedroom_vacancy_timeout.yaml` (REWIRE)

- Trigger: `input_boolean.bedroom_occupied` **off for 10 min** → turn off whole group
  (`light.bedroom_leds`, `light.bedroom_main`, `light.bedroom_reflectors`,
  `light.bed_stripe`). Condition re-checks latch still off.

### Untouched

`bedroom_lights_exclusivity.yaml` — manual-switch domain (bed vs non-bed mutual
exclusivity), orthogonal to presence.

## Auto-off tiers

Two-tier behaviour preserved, both now latch-gated:

| Tier | Trigger | Action |
|---|---|---|
| 1 | latch off for 5 min | `light.bed_stripe` off |
| 2 | latch off for 10 min | whole group off (leds, main, reflectors, bed_stripe) |

`mode: restart` (state machine) + duration triggers mean a re-latch before a timer
elapses cancels the pending off — no flicker.

## Truth matrix

### Latch transitions

| entrance | occupancy | duration | → latch |
|---|---|---|---|
| off→on edge | any | instant | ON |
| any | off→on edge | instant | ON |
| off | off | 60 s | OFF |
| either on | — | — | stays ON |
| ON, both off/unavail | — | 30 min | force OFF (watchdog) |

### On entry (latch OFF→ON)

| sleeping | is_dark | group off? | movie | action |
|---|---|---|---|---|
| off | on | yes | off | bed_stripe 50 % / 2951 K |
| off | on | yes | on | nothing (movie) |
| off | on | no | off | nothing (already lit) |
| off | off | yes | off | nothing (bright enough) |
| on | any | any | any | **nothing — never auto-on at night** |

### On exit (latch ON→OFF)

| since latch OFF | action |
|---|---|
| +5 min | bed_stripe off |
| +10 min | whole group off |
| re-latch before timer | timers cancel — nothing off |

### Safety cases

| scenario | latch | lights |
|---|---|---|
| in bed, mmWave drops < 60 s | stays ON | unchanged |
| in bed, mmWave drops > 60 s then re-detects | OFF→ON | sleep: nothing; day: bed_stripe |
| HA restart 3 a.m., occupancy on | re-latches ON | nothing (sleep gate) |
| HA restart, occupancy stuck on, room empty | ON | watchdog clears +30 min → off-timers run |
| night bathroom trip (walk in during sleep) | ON | nothing — dark walk (accepted tradeoff) |
| manual reflectors on, then leave | latch tracks | +10 min whole group off (incl. reflectors) |
| movie mode on, walk in | ON | nothing (movie blocks auto-on) |

## Accepted tradeoffs

- **Dark night-bathroom walk:** the never-auto-on-during-sleep rule means walking in
  during `sleeping_time` lights nothing. Chosen deliberately over a sleep + entrance-edge
  → bed_stripe 1 % exception, to eliminate any risk of a surprise night wake-up. Can be
  revisited later as an additive edge-gated path.

## Safety properties

- Still-in-bed → latch stays ON → no false auto-off.
- Sleep → no auto-on, even on re-latch or HA restart.
- mmWave stuck-on after restart → watchdog clears within 30 min.
- mmWave flap → 60 s exit debounce absorbs it.

## Files

- NEW `automations/bedroom_occupancy_state_machine.yaml`
- NEW `input_boolean.bedroom_occupied` in `config.yaml`
- EDIT `automations/bedroom_presence.yaml`
- EDIT `automations/bedroom_vacancy_timeout.yaml`

## Deploy

Feature branch (current `chore/june-features`), push, reload HA core config, check logs
(per the reload-after-push knowledge leaf). mmWave latch behaviour verified live where
possible.
