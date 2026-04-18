# Media Dashboard Redesign

**Date:** 2026-04-18
**Scope:** `dashboards/tablet/media.yaml` — replace static "Quick-Play" chip row with dynamic rows backed by Music Assistant library data. Fix 3 pre-existing scripts that reference a non-existent entity.

## Goals

- Show the **5 most-recently-played playlists** and the **3 most-played tracks** as tap-to-play tiles on the tablet Media view.
- Tapping a tile plays the selected item on `media_player.living_room_mass` so it appears in the existing mass-player-card on the left of the page.
- Keep the rest of the Media view (`mass-player-card`, TV player, voice search, Scene System) unchanged.
- Restore the 3 existing `music_play_*` scripts to working order — they currently reference the non-existent `media_player.mass_living_room_tv`.

## Non-goals

- Cover-art thumbnails on tiles (chip-style only for v1).
- Strict "last 30 days" ranking for tracks (uses all-time play count instead).
- Changes to the Scene System section.
- Refactoring `sensor.media_player_id_by_occupancy` to return area strings directly.

## Background

- `dashboards/tablet/media.yaml` currently has three sections: Playback (mass-player-card, left), Now Playing & Quick-Play (middle — TV player + 3 static chips + voice search), Scene System (right).
- Three scripts (`music_play_discover_weekly`, `music_play_random_playlist`, `music_play_last_played`) target `media_player.mass_{{ base.split('.')[1] }}` which resolves to `media_player.mass_living_room_tv` or `media_player.mass_bedroom_tv` — neither entity exists. The real Music Assistant entities are `media_player.living_room_mass` and `media_player.bedroom_mass` (suffix, not prefix).
- The mass-player-card on the Media view is hardcoded to `media_player.living_room_mass`, so for the new tiles to show their playback on that card, the play target must be that same entity.

## Architecture

Three layers:

```
┌──────────── Data layer ─────────────┐
│ sensor.mass_top_playlists           │  refreshed every 15 min + on HA start
│ sensor.mass_top_tracks              │  via trigger template + get_library
│   attribute .items = [{name,        │
│                        artists,     │
│                        uri, ...}]   │
└──────────────────────────────────────┘
             │
             │ state_attr(...)[N]
             ▼
┌──────────── View layer ──────────────┐
│ dashboards/tablet/media.yaml         │
│   Section "Playback"   — unchanged   │
│   Section "Now Playing & Quick-Play" │
│     • TV player card  — unchanged    │
│     • NEW: 5 playlist chips          │
│     • NEW: 3 track chips             │
│     • voice search     — unchanged   │
│   Section "Scene System" — unchanged │
└──────────────────────────────────────┘
             │
             │ tap_action → script.music_play_by_uri({uri, media_type})
             ▼
┌──────────── Action layer ────────────┐
│ script.music_play_by_uri             │  fixed target
│   → music_assistant.play_media       │  media_player.living_room_mass
└──────────────────────────────────────┘
```

## Components

### New — `sensor.mass_top_playlists` (trigger template)

- **Location:** `packages/misc/templates/sensors/mass_top_playlists.yaml` (alongside `media_player_id_by_occupancy.yaml`).
- **Triggers:** `time_pattern` every 15 min + `homeassistant` start event.
- **Action:** `music_assistant.get_library` with `media_type: playlist, limit: 5, order_by: last_played_desc, config_entry_id: {{ config_entry_id('media_player.living_room_mass') }}`. Response captured into `response_variable: result`.
- **State:** `{{ result['items'] | length }}` (scalar count — easy to eyeball in dev-tools).
- **Attribute `items`:** the full response array. Each item has at least `uri` and `name`; tracks also include `artists[]` and `image` on MA builds that support it.

### New — `sensor.mass_top_tracks` (trigger template)

- Same pattern as above, with `media_type: track, limit: 3, order_by: play_count_desc`.

### New — `script.music_play_by_uri`

- **Location:** `packages/misc/scripts/music_play_by_uri.yaml`.
- **Fields:** `uri` (required string), `media_type` (required string, values: `playlist`, `track`).
- **Guard:** first step is a `condition: template` that aborts the script if `uri` is empty — prevents disabled `—` tiles (or any other caller with a blank URI) from firing a doomed `play_media` call.
- **Action:** `music_assistant.play_media` on `media_player.living_room_mass` with `media_id: {{ uri }}, media_type: {{ media_type }}, enqueue: replace`.
- **Fixed target:** always the living room, never occupancy-routed. This is the deliberate contract — the new tiles are a living-room remote, and the mass-player-card on the same page reflects that.

### Modified — 3 existing `music_play_*` scripts

- `music_play_discover_weekly.yaml`, `music_play_random_playlist.yaml`, `music_play_last_played.yaml`.
- Replace `media_player.mass_{{ base.split('.')[1] }}` with a template that derives the area from the occupancy sensor's value and appends `_mass`:
  - `base` is `media_player.living_room_tv` or `media_player.bedroom_tv`.
  - Strip the `_tv` suffix → `living_room` / `bedroom` → append `_mass` → `media_player.living_room_mass` / `media_player.bedroom_mass`.
- Also update the `config_entry_id` templates that reference the non-existent `media_player.mass_living_room_tv` — they should resolve against `media_player.living_room_mass` instead.

### Modified — `dashboards/tablet/media.yaml`

- Remove the existing 3-chip `grid` inside the "Now Playing & Quick-Play" section.
- Insert two `horizontal-stack` rows in its place:
  - Row 1 — 5 playlist chips, indices 0..4 into `sensor.mass_top_playlists.items`.
  - Row 2 — 3 track chips, indices 0..2 into `sensor.mass_top_tracks.items`.
- Each chip is a `custom:mushroom-template-card` with `layout: vertical`, `fill_container: true`, and a `tap_action` that calls `script.music_play_by_uri`.
- Voice search card remains below both rows. Playback (mass-player-card) and Scene System sections untouched.

### Chip template shape

```yaml
- type: custom:mushroom-template-card
  primary: "{{ ((state_attr('sensor.mass_top_playlists', 'items') or [])[0].name) | default('—', true) }}"
  secondary: Playlist
  icon: mdi:playlist-music
  icon_color: >
    {% if (state_attr('sensor.mass_top_playlists', 'items') or []) | length > 0 %}green{% else %}disabled{% endif %}
  layout: vertical
  fill_container: true
  tap_action:
    action: perform-action
    perform_action: script.music_play_by_uri
    data:
      uri: "{{ (state_attr('sensor.mass_top_playlists', 'items') or [{}])[0].uri | default('', true) }}"
      media_type: playlist
```

Track chips use `icon: mdi:music-note`, `icon_color: blue`, and `secondary` sourced from `...items[N].artists[0].name` with the same `| default('—', true)` guard. Each of the 8 chips has its own index hardcoded (0..4 for playlists, 0..2 for tracks).

## Data flow

**Refresh cycle:**
- HA start event or 15-min tick → trigger template fires → `music_assistant.get_library` call → response stored on sensor state + `items` attribute → chips re-render automatically (they subscribe to the sensor via `state_attr`).

**Tap flow:**
1. User taps chip → `tap_action` reads the slot's URI from `state_attr`.
2. `script.music_play_by_uri` is called with `uri` + `media_type`.
3. Script calls `music_assistant.play_media` on `media_player.living_room_mass` with `enqueue: replace`.
4. MA plays on the Bravia; `media_player.living_room_mass` transitions to `playing`.
5. The mass-player-card (left of the page) is subscribed to that entity and updates automatically.

**Existing-script flow after fix:**
- Quick-play chip tap → existing script → reads `sensor.media_player_id_by_occupancy` → derives area → targets `media_player.{{ area }}_mass`. Occupancy-routed behaviour preserved, but the target entity is now the correct one.

**Concurrent writers:** both the new fixed-target tiles and the existing occupancy-routed quick-play scripts may target `media_player.living_room_mass` when you're downstairs. `enqueue: replace` means last tap wins. No explicit coordination needed.

## Error handling & edge cases

- **Sensor unavailable / state unknown** (MA offline, HA booting): every template uses `(state_attr(...) or [])` so missing/None items don't crash the card. Chips fall back to `primary: '—'` and `icon_color: disabled`.
- **Fewer items than slots** (library has <5 playlists or <3 tracks): same `or []` guard plus length check before indexing. Missing slots render as disabled `—` tiles with no-op taps (empty URI guard in script — the script conditions on `uri != ''` before calling `play_media`).
- **`music_assistant.get_library` call fails** mid-refresh: trigger templates skip the state update on action error. Sensor retains previous values until the next tick. Acceptable staleness.
- **Stale URI** (playlist deleted between refresh and tap): `music_assistant.play_media` surfaces an error notification. Not silently swallowed. No retry logic — YAGNI.
- **Target entity unavailable at tap time** (Bravia off, MA integration down): same error-surfacing behaviour. No graceful fallback.
- **Jinja `None` trap** (repo-wide gotcha): `| default('x')` does NOT catch `None`. All templates in this spec use `| default('—', true)` with the `true` second arg to catch all falsy values.

## Verification plan

**Pre-push:**
- `uv run pre-commit run --all-files`.
- Dev-tools → Template sanity check once sensors are loaded:
  - `{{ state_attr('sensor.mass_top_playlists', 'items') }}` returns a 5-element list.
  - `{{ state_attr('sensor.mass_top_tracks', 'items') }}` returns a 3-element list.

**Post-push:**
1. Push branch; HA auto-pulls within ~10s.
2. Reload YAML config or full HA restart (new trigger template sensors typically require a restart to register).
3. Log check: `grep -iE "mass_top_(playlists|tracks)|music_play_by_uri" home-assistant.log` — no template errors.
4. Dev-tools → States:
   - `sensor.mass_top_playlists.state` is a number; `.items` attribute populated.
   - `sensor.mass_top_tracks.state` is a number; `.items` attribute populated.
5. Playwright flow (via repo `ha-dashboards` verify recipe — force-refetch lovelace config via WebSocket, then navigate):
   - Navigate to `/wall-tablet/media`.
   - Screenshot: verify 5 playlist chips show real names, 3 track chips show title + artist.
   - Tap playlist chip #1 → wait 3s → screenshot → confirm mass-player-card (left) shows the playlist's now-playing state.
   - Tap any disabled `—` slot (if present) → confirm no crash.
6. Quick-play script sanity: trigger `script.music_play_discover_weekly` from dev-tools → confirm playback on `media_player.living_room_mass` (downstairs occupancy) or `media_player.bedroom_mass` (upstairs).

## Rollback

Single-commit (or small-commit) PR. `git revert` restores `dashboards/tablet/media.yaml` and the 3 `music_play_*` scripts to their prior state. The 2 new sensors and `music_play_by_uri` are additive — their removal is optional after a revert (they'll simply become unreferenced).

## Open questions

None. All architectural decisions made via brainstorming on 2026-04-18.
