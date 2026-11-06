---
summary: /api/error_log is 404 on this box, so a grep on it looks clean — read logs with `ha core logs` over SSH.
before_action:
  - About to check HA logs after a reload, restart or push
  - About to claim "no errors in the log"
on_symptom:
  - "curl $HA_URL/api/error_log returns 404: Not Found"
  - "grep of the HA error log finds nothing for an entity that clearly failed"
---

# Read HA logs over SSH, not /api/error_log

- **Use `ssh root@homeassistant.local 'ha core logs'`** (add-ons: `ha addons logs <slug>`, e.g.
  `45df7312_zigbee2mqtt`). `GET $HA_URL/api/error_log` answers `404: Not Found` here, so
  `curl ... | grep` prints nothing and passes for a clean log. (2026-11-06: several "log is clean"
  checks after a restart were this false negative.)
- **Sanity-check a "clean" result** by grepping the same stream for a line you know exists (a
  recurring warning), or look at the raw tail once.
- **Timestamps differ by source:** `ha core logs` and the Z2M log are local time (+01:00 / CET);
  automation traces and `last_triggered` are UTC.
- `ha core logs` is the whole log since boot; filter with `grep -E "ERROR|WARNING"` plus the
  entity or package name rather than reading it all.
