---
summary: ZBDongle-E as Zigbee router — web flasher leaves NCP fw; flash router .gbl via CLI, rts_dtr reflash, CLI rejoin.
before_action:
  - About to flash or pair a Sonoff ZBDongle-E as a Zigbee router / repeater
  - About to add or relocate a Zigbee router to strengthen the mesh
on_symptom:
  - "permit join is on but the dongle never joins"
  - "Sonoff Dongle Flasher says complete but the stick still probes as EZSP / coordinator"
  - "router paired fine, then Z2M pings time out after it was moved or power-cycled"
  - "universal-silabs-flasher: enter_bootloader ... TimeoutError"
  - "No converter available for 'light_indicator_level' on 'router_...'"
---

# ZBDongle-E as a Zigbee router

- **Don't trust the Sonoff web flasher.** It reported "complete" on both sticks and left
  coordinator firmware on them (EZSP 8.0.2 / 7.4.4). An NCP can't join, so permit join sees nothing.
  Always probe first: `uvx --from universal-silabs-flasher universal-silabs-flasher --device
  /dev/cu.usbserial-XXXX probe`.
- **Flash the router image from the CLI.** File: `Dongle-E/Router/Z3RouterUSBDonlge_EZNet6.10.3_V1.0.0.gbl`
  in github `itead/Sonoff_Zigbee_Dongle_Firmware`. `... flash --firmware router.gbl` (~40 s, enters
  the bootloader from EZSP by itself). Verify: `--probe-methods router:115200 probe` →
  `ApplicationType.ROUTER, version 6.10.3`. It joins within seconds of boot if permit join is open;
  Z2M identifies it as "ZBDongle-E with router firmware".
- **Reflashing FROM router firmware needs `--bootloader-reset rts_dtr`.** The router app has no
  launch-bootloader command; without the flag the flasher dies with `enter_bootloader TimeoutError`.
- **A router that reports joined but nobody hears = stale membership. Leave + reset it.** Talk to
  the router CLI over serial (pyserial, 115200, send `cmd\r\n`): `info` (network state 02 = joined,
  nodeID), `plugin counters print` (Mac Rx/Tx, `NWK Decrypt Failures`), `network leave`, then
  `reset` with permit join open → clean rejoin. Z2M drops the DB entry on the leave but keeps the
  `configuration.yaml` friendly_name, so it re-attaches under the same name.
- **Works on a PC USB port but dead on every USB charger → reflash round-trip.** NCP
  `Dongle-E/NCP_7.4.4/*.gbl` then router again (`rts_dtr` for the first hop). Tokens persist, the
  stick keeps its membership, and afterwards it runs on a charger. (Stick that had been through the
  web flasher's EZSP 8.0.2, 2026-09-23.)
- **Reachability test:** `/get` is unsupported on this model. Publish to `zigbee2mqtt/<name>/set`
  `{"read":{"cluster":"genBasic","attributes":["zclVersion"]}}` — a reply means two-way is fine, a
  `Publish 'set' 'read' ... failed` timeout means it's off the air. Isolate charger vs spot vs
  stick by swapping two sticks between positions.
- **Pair next to the coordinator, name it, then move it.** No re-pair after a move; routes
  reconverge within a minute. Name = physical spot (`router_attic_landing`), Z2M
  `bridge/request/device/rename` with `homeassistant_rename: true`.
- Model exposes only `light_indicator_level`; Z2M `bridge/request/networkmap` (see
  z2m-network-map) is the way to see who hears it.
