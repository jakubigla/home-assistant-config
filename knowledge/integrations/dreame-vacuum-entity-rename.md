---
summary: "dreame_vacuum rename: config-entry title won't retro-rename IDs; reload entry after; segments re-map on device swap."
before_action:
  - About to rename a dreame_vacuum robot's entity IDs to be vendor-agnostic
  - About to replace the physical robot vacuum and reuse its clean-segment scripts
  - About to rename many HA entity IDs at once via the WS entity registry
on_symptom:
  - "vacuum (or all its entities) went unavailable right after an entity_id rename"
  - "vacuum_clean_segment script cleans the wrong room after a device swap"
  - "renamed the config-entry title but existing entity_ids kept the old prefix"
---

- **The config-entry title sets the entity_id prefix only at first entity creation.** Renaming the
  title later (`config_entries/update`) does NOT retroactively rename existing entity_ids — rename
  each id individually via WS `config/entity_registry/update` (`entity_id` + `new_entity_id`). A
  fresh pairing whose entry is titled "Ground Floor" comes up already as `vacuum.ground_floor`.

- **After a batch entity_id rename the `dreame_vacuum` device goes UNAVAILABLE until you reload its
  config entry.** The integration re-binds entities to the new ids only on reload:
  `POST /api/config/config_entries/entry/<entry_id>/reload` (returns `{"require_restart":false}`).
  Registry rename alone (WS) leaves every entity unavailable.

- **Swapping the physical robot re-maps room segment IDs — update clean-segment scripts.** IDs live
  in the robot's firmware map, not HA. Read the live map from `state_attr('vacuum.<x>','rooms')`
  and fix each `dreame_vacuum.vacuum_clean_segment` `segments:` — a stale id silently cleans the
  wrong room (2026-07-24 L10→r5039a swap: kitchen 2→4, mudroom 8→5).

- **Registry rename is live immediately (WS), config files are not — they go live only when the
  HA-tracked git branch has them.** Land the config edit on whatever branch HA serves (verify —
  see [[project_ha_pull_branch]] — don't assume `main`) so the running config and the renamed
  registry stay consistent; otherwise the old config references now-dead entity ids. Reload +
  Playwright-check per [[reload-after-push]] and [[playwright-validate-dashboards]].

- Sensor sets differ by model: r5039a exposes `sensor.<x>_detergent_status` / `_mop_pad` (status
  `installed` only) — no consumable-life `%`, unlike the L10's `_detergent_left` / `_mop_pad_left`.
  Dashboard cells reading the `_left` sensors go blank after the swap; drop or re-point them.
