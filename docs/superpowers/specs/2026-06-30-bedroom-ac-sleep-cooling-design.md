# Bedroom AC — Pre-cool + Night Ceiling-Hold (sleep cooling)

**Date:** 2026-06-30
**Supersedes:** `2026-06-26-bedroom-ac-cooldown-design.md` (evening cooldown ON/OFF logic)
**Area:** `packages/areas/first-floor/bedroom`

## Problem

The existing evening-cooldown automations (`bedroom_ac_cooldown_on`, `bedroom_ac_cooldown_off`) under-serve the real goal. Six days of history (2026-06-25 → 06-30) show:

- The ON window (21:00–23:00) was too narrow — most actual cooling happened at 01:00, 05:00, 14:00 from **manual** triggers, not the automation.
- End temps clustered at **24–25°C**, rarely reaching the `≤23°C` off-threshold. On low fan the AC frequently cannot reach 23°.
- Sessions 4, 6, 12 ran the full **3h safety cap** without reaching target — wasted runtime; session 6 cooled 0° over 3h.

### Root cause: the AC's own sensor lies while running

Comparing `climate.bedroom` `current_temperature` (AC built-in sensor, in the unit's airflow) against `sensor.bedroom_temperature` (overlay → `sensor.bedroom_fp300_temperature`, true room temp), step-interpolated on a 5-min grid:

| AC state | AC sensor vs room | n |
|---|---|---|
| OFF (idle) | **+0.4°C** (median +0.3) — slight warm bias | 1055 |
| COOL (running) | **−2.8°C** (median −2.6) — reads far colder | 300 |

While cooling, **297 of 300 samples** had the AC sensor reading colder than the room. The AC sits in its own cold output airflow, so its internal thermostat believes the room is ~2.6° colder than it actually is — it backs off the compressor early, and the **room never reaches target**. This explains the stalled sessions.

## Goals

1. **Pre-cool**: room already cool when the user enters to sleep.
2. **Night ceiling-hold**: room never above ~25–26°C while sleeping (`bed_time` window).
3. **Quiet while occupied**: low fan when someone is in the room (sleep).

## Core principle

**AC = dumb cooler. HA = the real thermostat.**

- The AC is parked at setpoint **18°C** so its compressor runs full-tilt whenever it is on, regardless of its cold-biased internal sensor.
- HA decides on/off from `sensor.bedroom_temperature` (real room temp), **never** from the AC's `current_temperature`.
- All triggers and thresholds use `sensor.bedroom_temperature`.

## Entities (verified live 2026-06-30)

| Entity | Role | Notes |
|---|---|---|
| `climate.bedroom` | The AC | fan_modes: `auto, quiet, low, medlow, medium, medhigh, high, strong`; setpoint range 16–31 |
| `sensor.bedroom_temperature` | Room temp (truth) | overlay → `sensor.bedroom_fp300_temperature`, 0.01° resolution |
| `binary_sensor.bedroom_occupancy` | Occupancy (state machine) | persists through stillness; used for fan selection. (`binary_sensor.bedroom_presence` does NOT exist — stale ref) |
| `binary_sensor.bed_time` | Bedtime window | ON 22:00 → wake (07:30 wkday / 11:00 wkend) |
| `binary_sensor.sleeping_time` | Sleep window | ON 23:00 → wake |

## Design — phases

### Phase 1: Pre-cool (conditional lead)

Get the room down before the user lies down.

- **Trigger / start:**
  - If room **> 28°C** → start at **21:00**
  - Else → start when `bed_time` turns ON (**22:00**)
- **Action:** set hvac `cool` → wait 2s → set temperature **18** (Tuya mode-first ordering preserved).
- **Fan:** presence-driven (see Fan logic). Empty room during pre-cool ⇒ `high` for fast knockdown.

### Phase 2: Night ceiling-hold (bang-bang on room sensor)

Active window: `bed_time` ON.

- **ON:** `sensor.bedroom_temperature` **≥ 26.5°C** for a few minutes → AC `cool`, setpoint 18.
- **OFF:** `sensor.bedroom_temperature` **≤ 24.5°C** for a few minutes → AC off.
- 2°C band (24.5–26.5) limits compressor restarts (the loud event) while holding the room mostly ≤26°, ceiling brushing 26.5 briefly.
- Replaces the old `≤23°C` off-trigger, which was unreachable on low fan.

### Phase 3: Morning off

- `bed_time` turns OFF (07:30 wkday / 11:00 wkend) → AC off. Clean scheduled shutoff.

## Fan logic (two-factor: phase + presence)

Driven by `binary_sensor.bedroom_occupancy`.

| Phase | Occupied | Empty |
|---|---|---|
| **Pre-cool** (start → user arrives) | `low` | `high` |
| **Hold** (`sleeping_time` ON) | `low` | `low` |

Rationale:
- Empty during pre-cool ⇒ `high`: nobody to disturb, fastest knockdown — the main win.
- During hold, **always `low`** regardless of presence. A brief toilet trip (occupancy drops then returns) must NOT bump the fan to high and wake the user on return. A genuinely empty bedroom at 3am is a rare edge not worth the timer complexity or wake risk.
- Fan changes apply to a running AC; when occupancy flips during cool, re-issue the appropriate `fan_mode`.

## Keep / change / drop

| Item | Action |
|---|---|
| `bedroom_ac_safety_timeout` (3h cap, mode restart) | **Keep** unchanged — hard backstop against stuck sensor |
| Tuya mode-first + 2s delay before setpoint | **Keep** in every cool action (setpoint won't stick otherwise) |
| `bedroom_ac_cooldown_on` (21–23h, >25 → 22°) | **Replace** with Phase 1 pre-cool |
| `bedroom_ac_cooldown_off` (≤23 → off) | **Replace** with Phase 2 off (≤24.5) |
| Parked setpoint | **Change** 22 → **18** |

## Out of scope (YAGNI)

- Outdoor-temp-aware lead time (start time is a simple 1-step room-temp test).
- Humidity / dry-mode integration (separate humidifier automations already exist).
- Bump-to-high-when-truly-empty during hold (deliberately dropped — option A).
- Window/cover state gating (covers already auto-close at sunset via separate automation).

## Open risks

- On the hottest nights (room starts ~30°), even setpoint-18 + low-fan hold may not pull the room below 25 — but it will get closest and hold the ceiling. Pre-cool (21:00 start when >28°) is the mitigation: knock it down before sleep, then hold.
- Bang-bang restart noise: the 2°C band plus low fan keeps restarts infrequent; if still disruptive, widen the band (off ≤24, on ≥27) as a tuning follow-up.
