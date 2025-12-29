# Quickstart: Wall Tablet Dashboard

**Feature**: 002-wall-tablet-dashboard
**Date**: 2025-12-28

## Prerequisites

1. **Home Assistant** version 2024.3 or later (for Sections layout support)
2. **HACS** (Home Assistant Community Store) installed
3. **Tablet** with modern browser (Chrome, Safari, Firefox)

## Installation Steps

### Step 1: Install Required Custom Cards via HACS

1. Open Home Assistant → HACS → Frontend
2. Search and install:
   - **Mushroom** (required)
   - **card-mod** (recommended for font sizing)
   - **browser-mod** (optional for tablet features)
3. Restart Home Assistant after installation

### Step 2: Register Dashboard in configuration.yaml

Add to `configuration.yaml`:

```yaml
lovelace:
  mode: yaml
  resources:
    - url: /homeassistant/www/community/lovelace-mushroom/mushroom.js
      type: module
    - url: /homeassistant/www/community/lovelace-card-mod/card-mod.js
      type: module
  dashboards:
    wall-tablet:
      mode: yaml
      filename: dashboards/tablet.yaml
      title: Tablet
      icon: mdi:tablet
      show_in_sidebar: true
      require_admin: false
```

### Step 3: Create Dashboard File

Create `dashboards/tablet.yaml` with the sections layout structure from `data-model.md`.

### Step 4: Validate Configuration

```bash
# Lint YAML
yamllint dashboards/tablet.yaml

# Check Home Assistant configuration
# (via Developer Tools → Check Configuration in HA UI)
```

### Step 5: Configure Tablet

1. Open dashboard URL: `http://homeassistant.local:8123/wall-tablet`
2. Configure tablet browser:
   - Enable fullscreen/kiosk mode
   - Disable screen timeout (or use motion sensor wake)
   - Bookmark the dashboard URL

## Quick Test Checklist

- [ ] Dashboard loads without errors
- [ ] All 8 sections visible without scrolling
- [ ] Person cards show correct home/away status
- [ ] Light toggles work (tap to toggle)
- [ ] Camera shows live feed
- [ ] Text readable from 2 meters away

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cards not loading | Clear browser cache, verify HACS resources |
| Dashboard not found | Check `lovelace:` section in configuration.yaml |
| Entity unavailable | Verify entity_id in Developer Tools → States |
| Camera not streaming | Check camera integration settings |

## File Locations

| File | Purpose |
|------|---------|
| `configuration.yaml` | Dashboard registration |
| `dashboards/tablet.yaml` | Dashboard layout and cards |
| `specs/002-wall-tablet-dashboard/` | Design documentation |
