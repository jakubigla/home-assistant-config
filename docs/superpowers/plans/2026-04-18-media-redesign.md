# Media Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static Quick-Play chip row on the tablet Media view with two dynamic rows (5 most-recently-played playlists, 3 most-played tracks) backed by Music Assistant library data. Tapping a tile plays on `media_player.living_room_mass` so it appears on the existing mass-player-card. Fix 3 pre-existing `music_play_*` scripts that reference a non-existent entity.

**Architecture:** Two trigger-based template sensors poll `music_assistant.get_library` every 15 min and on HA start, exposing results as an `items` attribute. A new generic `script.music_play_by_uri` fires `music_assistant.play_media` on a fixed target (`media_player.living_room_mass`). Mushroom template chips read sensor attributes and tap into the script. The 3 existing `music_play_*` scripts are repaired to target the correct `{area}_mass` entity instead of the non-existent `mass_{area}_tv`.

**Tech Stack:** Home Assistant YAML (template platform, scripts), Music Assistant integration, Mushroom cards (custom Lovelace). Verification via HA dev-tools, REST API (curl), and Playwright browser automation.

**Spec:** `docs/superpowers/specs/2026-04-18-media-redesign-design.md`

---

## File Structure

Files to create:
- `packages/misc/scripts/music_play_by_uri.yaml` — new generic play-by-uri script (fixed target).
- `packages/misc/templates/sensors/mass_top_playlists.yaml` — trigger template, 5 most-recently-played playlists.
- `packages/misc/templates/sensors/mass_top_tracks.yaml` — trigger template, 3 most-played tracks.

Files to modify:
- `packages/misc/scripts/music_play_discover_weekly.yaml` — fix target entity.
- `packages/misc/scripts/music_play_random_playlist.yaml` — fix target entity + `config_entry_id` source.
- `packages/misc/scripts/music_play_last_played.yaml` — fix target entity + `config_entry_id` source.
- `dashboards/tablet/media.yaml` — replace 3-chip grid with two `horizontal-stack` rows (5 playlist chips + 3 track chips).

Nothing is removed. Nothing else is touched.

---

## Task 1: New `script.music_play_by_uri`

**Purpose:** Generic "play this URI on the living-room MA player" script. Used by all 8 new chip tiles. Has an empty-URI guard so disabled `—` tiles cannot trigger a doomed `play_media` call.

**Files:**
- Create: `packages/misc/scripts/music_play_by_uri.yaml`

- [ ] **Step 1: Confirm target entity is real**

Run:
```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/states/media_player.living_room_mass" \
  | python3 -m json.tool | head -5
```

Expected: JSON response with `entity_id: media_player.living_room_mass` (state may be `idle` or `unavailable`, both are fine).

If `{"message":"Entity not found."}` is returned, stop — MA integration is not configured. Notify user before proceeding.

- [ ] **Step 2: Create the script file**

Create `packages/misc/scripts/music_play_by_uri.yaml`:

```yaml
---
alias: music_play_by_uri
description: "Play a specific Music Assistant URI on the living room player"
icon: mdi:play-circle
fields:
  uri:
    description: "Music Assistant URI of the item to play"
    example: "spotify://playlist/abc123"
    required: true
    selector:
      text:
  media_type:
    description: "Type of media (playlist, track, album, artist)"
    example: "playlist"
    required: true
    selector:
      select:
        options:
          - playlist
          - track
          - album
          - artist
sequence:
  - condition: template
    value_template: "{{ uri | default('', true) | length > 0 }}"
  - action: music_assistant.play_media
    target:
      entity_id: media_player.living_room_mass
    data:
      media_id: "{{ uri }}"
      media_type: "{{ media_type }}"
      enqueue: replace
```

- [ ] **Step 3: Lint**

Run:
```bash
uv run pre-commit run --files packages/misc/scripts/music_play_by_uri.yaml
```

Expected: all hooks pass (yamllint + end-of-files + trim-trailing-whitespace).

- [ ] **Step 4: Commit and push**

```bash
git add packages/misc/scripts/music_play_by_uri.yaml
git commit -m "$(cat <<'EOF'
feat(media): add generic music_play_by_uri script

Fixed-target playback on media_player.living_room_mass. Consumed by
new playlist/track tiles on the tablet Media view. Guards against
empty URI so disabled tiles can't trigger a doomed play_media call.
EOF
)"
git push
```

Expected: push succeeds. HA auto-pulls within ~10s.

- [ ] **Step 5: Reload scripts on HA**

Run:
```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/services/script/reload"
```

Expected: `[]` response (empty array = success).

- [ ] **Step 6: Verify script appears**

Run:
```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/states/script.music_play_by_uri" \
  | python3 -m json.tool | head -10
```

Expected: JSON with `entity_id: script.music_play_by_uri` and `state: off` (or a recent `last_triggered`).

- [ ] **Step 7: Verify empty-URI guard (negative test)**

Run:
```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"uri":"","media_type":"playlist"}' \
  "http://homeassistant.local:8123/api/services/script/music_play_by_uri"
```

Expected: `[]` or `{}` response (no error, but because the condition fails, `music_assistant.play_media` is NOT called). Check `home-assistant.log` for the most recent entries — there should be no MA error about empty media_id. Then inspect state of `media_player.living_room_mass`:

```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/states/media_player.living_room_mass" \
  | python3 -c "import sys, json; s=json.load(sys.stdin); print('state:', s['state'])"
```

Expected: state unchanged from baseline (still `idle` or whatever it was).

---

## Task 2: New `sensor.mass_top_playlists`

**Purpose:** Trigger template sensor. Populates an `items` attribute with the 5 most-recently-played Music Assistant playlists. Refreshed every 15 min and on HA start.

**Files:**
- Create: `packages/misc/templates/sensors/mass_top_playlists.yaml`

- [ ] **Step 1: Confirm `music_assistant.get_library` returns playlists**

Run (one-off service call via REST — writes to Services API):
```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"config_entry_id":"<will-template-at-runtime>","media_type":"playlist","limit":2,"order_by":"last_played_desc"}' \
  "http://homeassistant.local:8123/api/services/music_assistant/get_library?return_response=true"
```

Note: the REST services endpoint may not accept `return_response=true` the same way dev-tools does. If this is awkward, use the HA UI instead:

1. Open http://homeassistant.local:8123/developer-tools/service
2. Service: `music_assistant.get_library`
3. Paste YAML:
   ```yaml
   config_entry_id: "{{ config_entry_id('media_player.living_room_mass') }}"
   media_type: playlist
   limit: 2
   order_by: last_played_desc
   ```
4. Click "Call Service" with "Response" toggled on.

Expected: response has an `items` array with playlist objects, each with at least `uri` and `name` fields. If this fails, ask the user whether MA is healthy before continuing.

- [ ] **Step 2: Create the sensor file**

Create `packages/misc/templates/sensors/mass_top_playlists.yaml`:

```yaml
---
# Music Assistant — 5 most-recently-played playlists.
#
# Refreshes every 15 min and on HA start via trigger template.
# Consumed by the 5 playlist chips on dashboards/tablet/media.yaml.
trigger:
  - platform: time_pattern
    minutes: "/15"
  - platform: homeassistant
    event: start
action:
  - action: music_assistant.get_library
    data:
      config_entry_id: "{{ config_entry_id('media_player.living_room_mass') }}"
      media_type: playlist
      limit: 5
      order_by: last_played_desc
    response_variable: result
sensor:
  - name: MA Top Playlists
    unique_id: mass_top_playlists
    icon: mdi:playlist-music
    state: "{{ (result['items'] | default([])) | length }}"
    attributes:
      items: "{{ result['items'] | default([]) }}"
```

- [ ] **Step 3: Lint**

```bash
uv run pre-commit run --files packages/misc/templates/sensors/mass_top_playlists.yaml
```

Expected: all hooks pass.

- [ ] **Step 4: Commit and push**

```bash
git add packages/misc/templates/sensors/mass_top_playlists.yaml
git commit -m "$(cat <<'EOF'
feat(media): add mass_top_playlists trigger template sensor

Polls music_assistant.get_library every 15 min (and on HA start)
for the 5 most-recently-played playlists. Exposes results on an
items attribute for consumption by the tablet Media tiles.
EOF
)"
git push
```

- [ ] **Step 5: Restart HA (trigger templates need a full restart to register)**

Run:
```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/services/homeassistant/restart"
```

Expected: empty response. HA takes ~30-60s to come back up.

Poll until HA is up (API returns 200):
```bash
until source .env && curl -sf -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/" > /dev/null; do sleep 5; done; echo "HA is up"
```

- [ ] **Step 6: Verify sensor populated**

```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/states/sensor.mass_top_playlists" \
  | python3 -m json.tool
```

Expected:
- `state`: a number `"0"` to `"5"` (count of items returned).
- `attributes.items`: a list of dicts, each with `name`, `uri`, plus other MA fields.

If `state` is `"unknown"` after ~30s: the `homeassistant: start` trigger may have fired before MA was ready. Force a manual refresh:

```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id":"sensor.mass_top_playlists"}' \
  "http://homeassistant.local:8123/api/services/homeassistant/update_entity"
```

Then re-query the state. If still empty, inspect HA logs:

```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/error_log" | grep -i "mass_top_playlists" | tail -20
```

- [ ] **Step 7: Verify a representative item shape**

```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/states/sensor.mass_top_playlists" \
  | python3 -c "import sys, json; s=json.load(sys.stdin); print(json.dumps(s['attributes']['items'][0] if s['attributes']['items'] else {}, indent=2))"
```

Expected: a dict with `name` and `uri` keys at minimum. Record the exact key names used by MA (they may be `name` or `title`, `uri` or `media_id`). If key names differ from the spec, note the real keys — Task 5 chip templates may need to match.

---

## Task 3: New `sensor.mass_top_tracks`

**Purpose:** Same pattern as Task 2 but for the 3 most-played tracks.

**Files:**
- Create: `packages/misc/templates/sensors/mass_top_tracks.yaml`

- [ ] **Step 1: Confirm `order_by: play_count_desc` works for tracks**

Via HA dev-tools (http://homeassistant.local:8123/developer-tools/service):

Service: `music_assistant.get_library`

Data:
```yaml
config_entry_id: "{{ config_entry_id('media_player.living_room_mass') }}"
media_type: track
limit: 2
order_by: play_count_desc
```

Expected: response `items` array populated, ordered by play count descending.

If `order_by: play_count_desc` errors (some MA builds may not expose it), fall back to `order_by: last_played_desc` and note the deviation in the commit message. Ranking will be "recently played" instead of "most played". Still useful, just different semantics than the spec.

- [ ] **Step 2: Create the sensor file**

Create `packages/misc/templates/sensors/mass_top_tracks.yaml`:

```yaml
---
# Music Assistant — 3 most-played tracks (all time).
#
# Refreshes every 15 min and on HA start via trigger template.
# Consumed by the 3 track chips on dashboards/tablet/media.yaml.
trigger:
  - platform: time_pattern
    minutes: "/15"
  - platform: homeassistant
    event: start
action:
  - action: music_assistant.get_library
    data:
      config_entry_id: "{{ config_entry_id('media_player.living_room_mass') }}"
      media_type: track
      limit: 3
      order_by: play_count_desc
    response_variable: result
sensor:
  - name: MA Top Tracks
    unique_id: mass_top_tracks
    icon: mdi:music-note
    state: "{{ (result['items'] | default([])) | length }}"
    attributes:
      items: "{{ result['items'] | default([]) }}"
```

- [ ] **Step 3: Lint**

```bash
uv run pre-commit run --files packages/misc/templates/sensors/mass_top_tracks.yaml
```

Expected: pass.

- [ ] **Step 4: Commit and push**

```bash
git add packages/misc/templates/sensors/mass_top_tracks.yaml
git commit -m "$(cat <<'EOF'
feat(media): add mass_top_tracks trigger template sensor

Polls music_assistant.get_library every 15 min (and on HA start)
for the 3 most-played tracks by all-time play count. Exposes
results on an items attribute for the tablet Media tiles.
EOF
)"
git push
```

- [ ] **Step 5: Restart HA**

```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/services/homeassistant/restart"

until source .env && curl -sf -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/" > /dev/null; do sleep 5; done; echo "HA is up"
```

- [ ] **Step 6: Verify sensor populated**

```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/states/sensor.mass_top_tracks" \
  | python3 -m json.tool
```

Expected: `state` is a number `"0"` to `"3"`; `attributes.items` is a list. Each item should have at least `name`/`title`, `uri`, and `artists` (an array with at least one `{name: ...}` dict).

Record the exact key names for `artists[].name` — Task 5 chip template depends on this shape.

---

## Task 4: Fix 3 existing `music_play_*` scripts

**Purpose:** Replace broken references to the non-existent `media_player.mass_{area}_tv` pattern with the correct `{area}_mass` pattern. Also fix `config_entry_id` lookups.

**Files:**
- Modify: `packages/misc/scripts/music_play_discover_weekly.yaml`
- Modify: `packages/misc/scripts/music_play_random_playlist.yaml`
- Modify: `packages/misc/scripts/music_play_last_played.yaml`

- [ ] **Step 1: Confirm baseline brokenness**

```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/services/script/music_play_last_played"
```

Expected: an error in the HA log about the target entity. Check:

```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/error_log" | grep -iE "mass_living_room_tv|music_play" | tail -10
```

Expected output mentions that the entity doesn't exist or the service call failed. This confirms the baseline. (If for some reason the script succeeded, still proceed with the fix — the current target is unambiguously wrong per our investigation.)

- [ ] **Step 2: Rewrite `music_play_discover_weekly.yaml`**

Replace the entire file `packages/misc/scripts/music_play_discover_weekly.yaml` with:

```yaml
---
alias: music_play_discover_weekly
description: "Play the Discover Weekly playlist on the occupancy-based player"
icon: mdi:playlist-star
sequence:
  - action: music_assistant.play_media
    target:
      entity_id: >
        {% set base = states('sensor.media_player_id_by_occupancy') %}
        {% set area = base.split('.')[1] | replace('_tv', '') %}
        media_player.{{ area }}_mass
    data:
      media_id: "Discover Weekly"
      media_type: playlist
      enqueue: replace
```

- [ ] **Step 3: Rewrite `music_play_random_playlist.yaml`**

Replace the entire file with:

```yaml
---
alias: music_play_random_playlist
description: "Play a random playlist from the Music Assistant library"
icon: mdi:shuffle-variant
sequence:
  - variables:
      target: "media_player.{{ states('sensor.media_player_id_by_occupancy').split('.')[1] | replace('_tv', '') }}_mass"

  - action: music_assistant.get_library
    data:
      config_entry_id: "{{ config_entry_id(target) }}"
      media_type: playlist
      limit: 1
      order_by: random
    response_variable: random_playlist

  - condition: template
    value_template: "{{ random_playlist['items'] | length > 0 }}"

  - action: music_assistant.play_media
    target:
      entity_id: "{{ target }}"
    data:
      media_id: "{{ random_playlist['items'][0].uri }}"
      media_type: playlist
      enqueue: replace
```

- [ ] **Step 4: Rewrite `music_play_last_played.yaml`**

Replace the entire file with:

```yaml
---
alias: music_play_last_played
description: "Play the last played playlist"
icon: mdi:history
sequence:
  - variables:
      target: "media_player.{{ states('sensor.media_player_id_by_occupancy').split('.')[1] | replace('_tv', '') }}_mass"

  - action: music_assistant.get_library
    data:
      config_entry_id: "{{ config_entry_id(target) }}"
      media_type: playlist
      limit: 1
      order_by: last_played_desc
    response_variable: last_played

  - condition: template
    value_template: "{{ last_played['items'] | length > 0 }}"

  - action: music_assistant.play_media
    target:
      entity_id: "{{ target }}"
    data:
      media_id: "{{ last_played['items'][0].uri }}"
      media_type: playlist
      enqueue: replace
```

- [ ] **Step 5: Lint**

```bash
uv run pre-commit run --files \
  packages/misc/scripts/music_play_discover_weekly.yaml \
  packages/misc/scripts/music_play_random_playlist.yaml \
  packages/misc/scripts/music_play_last_played.yaml
```

Expected: pass.

- [ ] **Step 6: Commit and push**

```bash
git add packages/misc/scripts/music_play_discover_weekly.yaml \
        packages/misc/scripts/music_play_random_playlist.yaml \
        packages/misc/scripts/music_play_last_played.yaml
git commit -m "$(cat <<'EOF'
fix(media): repair music_play_* scripts to use real MA entities

The previous target template 'media_player.mass_{area}_tv' resolved
to entities that do not exist (mass_living_room_tv, mass_bedroom_tv).
The real Music Assistant entities use the '{area}_mass' suffix
pattern: media_player.living_room_mass and media_player.bedroom_mass.
All three scripts now derive the correct target from the occupancy
sensor and resolve config_entry_id against the real entity.
EOF
)"
git push
```

- [ ] **Step 7: Reload scripts**

```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/services/script/reload"
```

- [ ] **Step 8: Smoke-test each fixed script**

Note playback baseline first:

```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/states/media_player.living_room_mass" \
  | python3 -c "import sys, json; s=json.load(sys.stdin); print('state:', s['state'], '| title:', s['attributes'].get('media_title','<none>'))"
```

Fire `music_play_last_played`:

```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/services/script/music_play_last_played"
sleep 5
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/states/media_player.living_room_mass" \
  | python3 -c "import sys, json; s=json.load(sys.stdin); print('state:', s['state'], '| title:', s['attributes'].get('media_title','<none>'))"
```

Expected: state transitions to `playing` with a real `media_title`. If it was already playing (occupancy downstairs), the title changes to match the fetched last-played playlist.

Then stop playback to keep side effects small:

```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id":"media_player.living_room_mass"}' \
  "http://homeassistant.local:8123/api/services/media_player/media_stop"
```

Repeat for `music_play_random_playlist` and `music_play_discover_weekly`. If any of them fails, check HA logs and fix before proceeding.

---

## Task 5: Update `dashboards/tablet/media.yaml`

**Purpose:** Replace the existing 3-chip `grid` inside the "Now Playing & Quick-Play" section with two `horizontal-stack` rows — 5 playlist chips + 3 track chips. Voice search and the TV player card remain.

**Files:**
- Modify: `dashboards/tablet/media.yaml` (lines 27-63 of the current file — the `grid` block)

- [ ] **Step 1: Capture baseline screenshot**

Use Playwright to screenshot `/wall-tablet/media` before any changes. Follow the repo's verify recipe (`.claude/skills/ha-dashboards/references/verify.md`): force-refetch the lovelace config via WebSocket, navigate, snapshot. Save as `media-before.png` at repo root.

- [ ] **Step 2: Read the current file**

Confirm the middle section structure matches the spec. You should see (approximately):

```yaml
- title: Now Playing & Quick-Play
  cards:
    - type: custom:mushroom-media-player-card
      entity: media_player.living_room_tv
      ...
    - type: grid
      columns: 3
      square: false
      cards:
        - type: custom:mushroom-template-card
          primary: Discover Weekly
          ...
        - type: custom:mushroom-template-card
          primary: Random Playlist
          ...
        - type: custom:mushroom-template-card
          primary: Last Played
          ...
    - type: custom:voice-music-search-card
```

- [ ] **Step 3: Replace the `grid` block with two horizontal-stacks**

In `dashboards/tablet/media.yaml`, inside the "Now Playing & Quick-Play" section, replace the entire `- type: grid` block (columns, square, the 3 quick-play chips) with the following two `horizontal-stack` blocks. The `custom:mushroom-media-player-card` (TV player) stays above; `custom:voice-music-search-card` stays below.

```yaml
      - type: horizontal-stack
        cards:
          - type: custom:mushroom-template-card
            primary: >
              {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
              {% if items | length > 0 %}{{ items[0].name }}{% else %}—{% endif %}
            secondary: Playlist
            icon: mdi:playlist-music
            icon_color: >
              {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
              {% if items | length > 0 %}green{% else %}disabled{% endif %}
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.music_play_by_uri
              data:
                uri: >
                  {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
                  {% if items | length > 0 %}{{ items[0].uri }}{% else %}{% endif %}
                media_type: playlist

          - type: custom:mushroom-template-card
            primary: >
              {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
              {% if items | length > 1 %}{{ items[1].name }}{% else %}—{% endif %}
            secondary: Playlist
            icon: mdi:playlist-music
            icon_color: >
              {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
              {% if items | length > 1 %}green{% else %}disabled{% endif %}
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.music_play_by_uri
              data:
                uri: >
                  {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
                  {% if items | length > 1 %}{{ items[1].uri }}{% else %}{% endif %}
                media_type: playlist

          - type: custom:mushroom-template-card
            primary: >
              {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
              {% if items | length > 2 %}{{ items[2].name }}{% else %}—{% endif %}
            secondary: Playlist
            icon: mdi:playlist-music
            icon_color: >
              {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
              {% if items | length > 2 %}green{% else %}disabled{% endif %}
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.music_play_by_uri
              data:
                uri: >
                  {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
                  {% if items | length > 2 %}{{ items[2].uri }}{% else %}{% endif %}
                media_type: playlist

          - type: custom:mushroom-template-card
            primary: >
              {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
              {% if items | length > 3 %}{{ items[3].name }}{% else %}—{% endif %}
            secondary: Playlist
            icon: mdi:playlist-music
            icon_color: >
              {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
              {% if items | length > 3 %}green{% else %}disabled{% endif %}
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.music_play_by_uri
              data:
                uri: >
                  {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
                  {% if items | length > 3 %}{{ items[3].uri }}{% else %}{% endif %}
                media_type: playlist

          - type: custom:mushroom-template-card
            primary: >
              {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
              {% if items | length > 4 %}{{ items[4].name }}{% else %}—{% endif %}
            secondary: Playlist
            icon: mdi:playlist-music
            icon_color: >
              {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
              {% if items | length > 4 %}green{% else %}disabled{% endif %}
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.music_play_by_uri
              data:
                uri: >
                  {% set items = state_attr('sensor.mass_top_playlists', 'items') or [] %}
                  {% if items | length > 4 %}{{ items[4].uri }}{% else %}{% endif %}
                media_type: playlist

      - type: horizontal-stack
        cards:
          - type: custom:mushroom-template-card
            primary: >
              {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
              {% if items | length > 0 %}{{ items[0].name }}{% else %}—{% endif %}
            secondary: >
              {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
              {% if items | length > 0 %}
                {{ (items[0].artists | default([]))[0].name | default('Unknown artist', true) }}
              {% else %}—{% endif %}
            icon: mdi:music-note
            icon_color: >
              {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
              {% if items | length > 0 %}blue{% else %}disabled{% endif %}
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.music_play_by_uri
              data:
                uri: >
                  {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
                  {% if items | length > 0 %}{{ items[0].uri }}{% else %}{% endif %}
                media_type: track

          - type: custom:mushroom-template-card
            primary: >
              {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
              {% if items | length > 1 %}{{ items[1].name }}{% else %}—{% endif %}
            secondary: >
              {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
              {% if items | length > 1 %}
                {{ (items[1].artists | default([]))[0].name | default('Unknown artist', true) }}
              {% else %}—{% endif %}
            icon: mdi:music-note
            icon_color: >
              {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
              {% if items | length > 1 %}blue{% else %}disabled{% endif %}
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.music_play_by_uri
              data:
                uri: >
                  {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
                  {% if items | length > 1 %}{{ items[1].uri }}{% else %}{% endif %}
                media_type: track

          - type: custom:mushroom-template-card
            primary: >
              {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
              {% if items | length > 2 %}{{ items[2].name }}{% else %}—{% endif %}
            secondary: >
              {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
              {% if items | length > 2 %}
                {{ (items[2].artists | default([]))[0].name | default('Unknown artist', true) }}
              {% else %}—{% endif %}
            icon: mdi:music-note
            icon_color: >
              {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
              {% if items | length > 2 %}blue{% else %}disabled{% endif %}
            layout: vertical
            fill_container: true
            tap_action:
              action: perform-action
              perform_action: script.music_play_by_uri
              data:
                uri: >
                  {% set items = state_attr('sensor.mass_top_tracks', 'items') or [] %}
                  {% if items | length > 2 %}{{ items[2].uri }}{% else %}{% endif %}
                media_type: track
```

**Important:**
- In Task 2/3 Step 7, you recorded the exact key names MA returns. If MA uses `title` instead of `name`, or if `artists` is shaped differently (e.g., a string, not a list), update the `primary`/`secondary` templates accordingly *before* committing. Do not push a dashboard YAML that references non-existent keys.

- [ ] **Step 4: Lint**

```bash
uv run pre-commit run --files dashboards/tablet/media.yaml
```

Expected: pass. Long ternary expressions may trigger 88-char warnings — use the multi-line `{% if %} ... {% else %} ... {% endif %}` form shown above, which stays under the limit.

- [ ] **Step 5: Commit and push**

```bash
git add dashboards/tablet/media.yaml
git commit -m "$(cat <<'EOF'
feat(dashboard): replace Media quick-play row with dynamic tiles

Two horizontal-stack rows on the tablet Media view:
- 5 chips bound to sensor.mass_top_playlists (recent playlists)
- 3 chips bound to sensor.mass_top_tracks (all-time top tracks)

Each chip reads title + artist from the backing sensor's items
attribute and taps through script.music_play_by_uri to play on
media_player.living_room_mass. Disabled tiles fall back to '—'
and a no-op tap.
EOF
)"
git push
```

- [ ] **Step 6: Wait for HA auto-pull**

HA pulls the branch within ~10s. Lovelace YAML changes don't need a reload — the frontend fetches on navigation. But to be sure cards pick up cleanly, force-refetch the config (see `.claude/skills/ha-dashboards/references/verify.md`).

---

## Task 6: End-to-end verification

**Purpose:** Confirm the live tablet Media view renders correctly, tapping plays, and the mass-player-card reflects playback.

**Files:**
- No code changes.

- [ ] **Step 1: Navigate to the Media view**

Via Playwright (see `.claude/skills/ha-dashboards/references/verify.md`):

1. Force-refetch the lovelace config via WebSocket (kills the browser cache).
2. Navigate to `http://homeassistant.local:8123/wall-tablet/media`.
3. Wait for the page to settle.

- [ ] **Step 2: Screenshot the full view**

Save as `media-after.png`. Compare visually against `media-before.png`:
- Left section: mass-player-card unchanged.
- Middle section top: TV player card unchanged.
- Middle section below TV: **row of 5 playlist chips** with real playlist names (or `—` if the library has fewer).
- Middle section below that: **row of 3 track chips** with real titles + artist subtitles.
- Middle section bottom: voice search card unchanged.
- Right section: Scene System unchanged.

- [ ] **Step 3: Browser console check**

Use `mcp__playwright__browser_console_messages` to confirm no red errors from Mushroom card templates. `TypeError: Cannot read properties of undefined` indicates a template hit an unguarded `[N]` on an empty array — fix the template and re-push.

- [ ] **Step 4: Tap a playlist chip and verify playback**

Capture the pre-tap state of `media_player.living_room_mass`:

```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/states/media_player.living_room_mass" \
  | python3 -c "import sys, json; s=json.load(sys.stdin); print('before:', s['state'], '|', s['attributes'].get('media_title','<none>'))"
```

Use `mcp__playwright__browser_click` on the first playlist chip (ref from `browser_snapshot`). Wait 5 seconds for MA to start playback.

Capture post-tap state:

```bash
source .env && curl -s -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  "http://homeassistant.local:8123/api/states/media_player.living_room_mass" \
  | python3 -c "import sys, json; s=json.load(sys.stdin); print('after:', s['state'], '|', s['attributes'].get('media_title','<none>'))"
```

Expected: state transitions to `playing`; `media_title` is populated.

- [ ] **Step 5: Screenshot the mass-player-card after playback**

Save `media-after-playing.png`. The mass-player-card on the left should show the track/playlist that's now playing, proving the fixed-target design works (tap → plays → card reflects it).

- [ ] **Step 6: Tap a track chip and repeat**

Same as Step 4 but on the first track chip. Expected: another transition, different title (unless the top-played track happened to be the first track of the playlist you just started). Stop playback afterwards:

```bash
source .env && curl -s -X POST -H "Authorization: Bearer $API_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id":"media_player.living_room_mass"}' \
  "http://homeassistant.local:8123/api/services/media_player/media_stop"
```

- [ ] **Step 7: Tap a disabled (`—`) slot if present, and confirm no crash**

If the library has fewer than 5 playlists or fewer than 3 tracks, there will be a disabled chip with `—`. Tap it. Expected:
- No browser console error.
- `media_player.living_room_mass` state unchanged.
- `home-assistant.log` does not record an MA error for an empty media_id (the script's `condition: template` aborts the sequence).

If the library is full (5/3 items), skip this step and note the untested edge case in the PR description.

- [ ] **Step 8: Clean up baseline artifacts (optional)**

```bash
rm -f media-before.png media-after.png media-after-playing.png
```

Or keep them for the PR description / review.

- [ ] **Step 9: Final commit (if any visual tweaks were made during verification)**

If you adjusted templates (e.g., swapped `name` → `title`, fixed `artists` shape), commit with a fix-up message:

```bash
git add dashboards/tablet/media.yaml
git commit -m "fix(dashboard): align media tile templates with MA item shape"
git push
```

If no changes were needed during verification, skip this step.

---

## Rollback plan

Each task is its own commit. Any failing task can be reverted in isolation:

```bash
git revert <commit-sha>
git push
```

To revert the whole feature at once, revert each commit from Task 1..5 in reverse order. The new sensors and `music_play_by_uri` script become unreferenced after the dashboard revert; leaving them in place is harmless, or they can be deleted in a follow-up.
