# Knowledge

Frontmatter-routed how-to layer. Leaves live under `areas/`, `integrations/`, `ops/`, `tooling/`.
The `knowledge-router` skill routes intent here; `knowledge-author` writes leaves.

## Scenarios

### Pushing a config change
About to push and need the change live on HA.
Load: `ops/reload-after-push.md`, `ops/never-push-main.md`.

### Querying or controlling HA over the network
About to curl/websocat HA or find an entity.
Load: `ops/sandbox-homeassistant-local.md`, `integrations/entity-source-not-in-repo.md`.

### Working with the Satel alarm
About to find or control an alarm panel, zone, or garage door.
Load: `integrations/satel-entities.md`, `integrations/entity-source-not-in-repo.md`.

### Editing an area package
About to add or edit a room automation, device, or light group.
Load: `areas/occupancy-state-machine.md`.

### Editing a dashboard
About to add/redesign a Lovelace view or card.
Load: `tooling/dashboard-url-hyphen.md`, `tooling/playwright-validate-dashboards.md`, `tooling/mushroom-visibility-gotcha.md`.

<!-- LEAVES:START -->
### areas/
See `areas/INDEX.md`.
### integrations/
See `integrations/INDEX.md`.
### ops/
See `ops/INDEX.md`.
### tooling/
See `tooling/INDEX.md`.
<!-- LEAVES:END -->
