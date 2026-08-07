---
summary: start/reload sync triggers re-run turn-ON branches — a plain reload switches lights on with nobody there.
before_action:
  - About to add a homeassistant.start or automation_reloaded trigger to an automation that turns lights on
  - About to reuse the occupancy-latch sync pattern on an automation that drives lights directly
on_symptom:
  - "lights turned on by themselves after a restart or config reload"
  - "several automations share an identical last_triggered second"
  - "TV LEDs or room LEDs came on mid-evening with the room empty and the TV off"
---

# A start/reload trigger re-runs the turn-ON logic

- **An automation whose branches are gated only on *state* will turn lights ON when a
  `homeassistant.start` / `automation_reloaded` trigger re-runs it — a plain config reload becomes a
  "switch the lights on" button.** The branch conditions are all true (someone present, `is_dark`
  on), so the reload legitimately matches the on-path. (`kitchen_presence` relit `light.kitchen_led`
  and `living_room_tv_playback` relit `light.living_room_tv_leds` on every reload once
  `binary_sensor.*_is_dark` went on for the evening.)
- **Fix: give the start/reload triggers an `id` (`sync`, `re_evaluate`) and gate every light-ON
  branch with `condition: not` on that id.** Leave turn-OFF paths ungated — a reload should be able
  to clear a stale ON but never create one.
  ```yaml
  - conditions:
      - condition: not
        conditions: [{condition: trigger, id: sync}]
      - # ...normal state conditions...
  ```
  Gate **every** on-branch: `living_room_tv_playback` needed it on three (playing / paused /
  idle-on); only its TV-off branch was already trigger-gated.
- **This is the inverse of [[occupancy-latch-startup-sync]] — do not blanket-apply that pattern.** A
  sync branch is right for an `input_boolean` latch (re-derive state, no side effect) and wrong for
  an automation that commands lights directly.
- **Reload signature: several unrelated automations sharing an identical `last_triggered` second is
  a reload, not a real trigger.** Check `sensor.uptime` to tell a reload from a restart. Don't
  attribute a light change to whatever real-world event happened nearby.
- **Diagnose with `trace/get` over the WS API** — it shows each branch's condition result and the
  service calls actually made, which state history can't. `/api/config/automation/config/<id>`
  returns 404 for YAML-package automations; the trace's `config` key carries the live trigger list.
