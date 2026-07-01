---
summary: At config load HA renders templates with empty context; trigger/logbook entity_id and top vars break, target defers.
before_action:
  - About to use a field/variable in a script or automation entity_id
  - About to wait on a templated entity with wait_for_trigger
  - About to default a script field into a top-level variables var
on_symptom:
  - "Entity {{ x }} is neither a valid entity ID nor a valid UUID for dictionary value @ data['entity_id']. Got None"
  - "script or automation shows state=unavailable mode=None after reload (failed to setup sequence and has been disabled)"
  - "templated entity_id works in a service call but breaks in wait_for_trigger / logbook.log"
---

# HA script config-load template validation

HA validates a script/automation at **config load** by rendering its templates with an **empty
context** — fields, top-level `variables`, and per-step vars are all undefined then. Whether a
templated `entity_id` survives depends on *which* schema validates it: some defer the template,
some eagerly validate the rendered value (`None`) against the entity-id validator and fail, which
**disables the whole script** (`state=unavailable`, `mode=None`).

- **A `state`-platform trigger's `entity_id` is NOT templatable** — eagerly validated at load.
  `wait_for_trigger: {platform: state, entity_id: "{{ zone }}"}` fails with `Entity {{ zone }} is
  neither a valid entity ID nor a valid UUID ... @ data['entity_id']. Got None`. **Fix: use
  `wait_template`**, which takes a full template: `wait_template: "{{ is_state(zone, 'closed') }}"`
  (+ `timeout:`). (Cost 5 deploy cycles on `garden_open_zone_until_real_close`.)
- **`logbook.log`'s `data.entity_id` is eagerly validated too** — a templated value there renders
  `None` and fails identically. Omit it; name the entity in `message` instead.
- **A top-level `variables:` block is rendered at load with the empty context** — a defaulted
  indirection var (`zone_e: "{{ zone | default('valve.x') }}"`) still renders `None` (fields are
  undefined, and `default` only fires on *undefined*, not the `None` a missing field yields) and
  poisons every target that reads it. **Reference the field directly**, don't launder it through a
  top var.
- **CONTRAST — a service call's `target.entity_id: "{{ field }}"` DOES load** (field templates
  defer there). So `valve.open_valve` / `light.turn_on` with `target.entity_id: "{{ zone }}"` and a
  plain `fields: {zone: ...}` is fine. The breakage is trigger/logbook/top-var, not service targets.

## Diagnosing a "failed to setup sequence" load error

- **`system_log/list` retains STALE errors across reloads.** Call `system_log/clear` *before*
  `script.reload`, then read the log — otherwise an old error reads as still-failing and you chase
  a ghost.
- **Bisect with live probe scripts.** Scripts dir is `!include_dir_merge_named` (see garden
  `config.yaml`), so each file = one script. `scp` a minimal probe into
  `/config/packages/areas/outdoor/garden/scripts/` on the HA host (root SSH, key-based — see
  `tuya-local-sprinkler-zombie` for the SSH path), `script.reload`, read `system_log/list` over WS,
  add one construct per probe until it breaks. Faster than the push→pull→reload loop
  (`reload-after-push`); delete the probe when done.
