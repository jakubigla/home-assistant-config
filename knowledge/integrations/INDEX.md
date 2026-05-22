# integrations/

<!-- LEAVES:START -->
- [entity-source-not-in-repo](entity-source-not-in-repo.md) — Many entities come from integrations, not YAML — query live HA, don't grep the repo.
  - **before**: About to check whether an entity exists; About to confirm an entity id before using it
  - **symptom**: entity not found by grepping the repo; automation references an entity absent from any YAML
- [satel-entities](satel-entities.md) — Satel ETHM-1 at 192.168.100.7; entity names lack "satel" — query by config_entry_id.
  - **before**: About to find or control a Satel alarm entity; About to work with the alarm panel, garage door, or a motion/door zone
  - **symptom**: grep for satel returns no entities; cannot locate alarm or zone entity
<!-- LEAVES:END -->
