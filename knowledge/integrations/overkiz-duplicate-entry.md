---
summary: One Overkiz gateway = ONE config entry (cloud); a second zeroconf local entry causes silent
  boot-order entity roulette.
before_action:
  - About to configure a discovered Somfy / Overkiz / Tahoma device in HA
  - About to debug Tahoma pergola covers or lights that work from the app but not from HA
on_symptom:
  - "Tahoma / pergola devices respond in the Tahoma app but not from HA"
  - "Platform overkiz does not generate unique IDs. ID io://... already exists - ignoring"
  - "Cannot connect to host gateway-XXXX-XXXX-XXXX.local:8443 (MDNS lookup failed)"
  - "pergola commands accepted (200) after an HA restart but nothing moves, no UI error"
---

# Overkiz/Tahoma: one gateway, one config entry

- **Keep exactly ONE overkiz entry for gateway 2331-4940-6522 — the CLOUD one
  (`jakub.igla@gmail.com`, entry `01KM375WD89AQJWE79BHC8AX4J`).** A second zeroconf local-API entry
  (`gateway-2331-4940-6522.local:8443`, added 2026-06-19, deleted 2026-07-18) registered the same
  devices; unique-ID collisions then hand each entity to whichever entry sets up first that boot
  ("Platform overkiz does not generate unique IDs … ignoring light.pergola_led_top" ×8 lights
  ×10 numbers).
- **Entities owned by the local entry fail SILENTLY** — service call returns 200, nothing moves,
  app works. mDNS `.local` resolution fails on this network (UDM), so the local API never connects
  ("MDNS lookup failed, Timeout while contacting DNS servers", 16 tries then gives up post-restart).
- **Zeroconf re-discovers the gateway — DISMISS the "Somfy/Overkiz discovered" offer.** Configuring
  it re-creates the duplicate. If local API is ever wanted: static DHCP lease, add by IP not
  `.local`, and delete the cloud entry instead — never run both.
- **Diagnose ownership, don't trust entry state:** both entries can show `loaded` while local is
  dead — loaded ≠ reachable. Check `/api/config/config_entries/entry?domain=overkiz` for entries,
  WS `config/entity_registry/list` for each entity's `config_entry_id`, and system_log for the
  unique-ID / MDNS errors. Round-trip proof: command an entity, watch state confirm back (~10 s
  cloud latency).
