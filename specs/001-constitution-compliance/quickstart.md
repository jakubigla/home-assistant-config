# Quickstart: Constitution Compliance Refactoring

**Date**: 2025-12-28
**Feature**: 001-constitution-compliance

## Overview

This refactoring brings the Home Assistant configuration into full compliance with the project constitution. The changes are organized into 5 independent work streams that can be implemented in any order.

## Prerequisites

- Home Assistant configuration repository cloned
- yamllint installed (`pip install yamllint`)
- Access to Home Assistant UI for testing

## Implementation Order (Recommended)

### Phase 1: File Renames (Low Risk)
Simple file renames with no logic changes. Can be done first to establish naming compliance.

### Phase 2: Cube Relocation (Medium Risk)
Move cube automation to new misc package. Creates new package structure.

### Phase 3: Bedroom Movie Mode (Medium Risk)
Replace TV dependency with movie mode toggle. Modifies existing automation logic.

### Phase 4: Light Consolidation (Medium Risk)
Merge duplicate automations. Deletes files after consolidation.

### Phase 5: Bathroom Lighting (Low Risk)
Add/modify bathroom occupancy lighting. Independent of other changes.

---

## Quick Reference: File Changes

### CREATE These Files

```bash
# 1. New misc package
mkdir -p packages/misc/automations

# Create config.yaml
cat > packages/misc/config.yaml << 'EOF'
automation: !include_dir_list automations
EOF

# 2. Cube automation (move from bedroom)
mv packages/areas/bedroom/automations/cube_jakub.yaml \
   packages/misc/automations/misc_cube_control.yaml

# 3. Consolidated light exclusivity (create new)
# See data-model.md for full automation content

# 4. Bathroom occupancy lighting (create new)
# See data-model.md for full automation content
```

### RENAME These Files

```bash
# Bedroom
mv packages/areas/bedroom/automations/scene_switch_sona.yaml \
   packages/areas/bedroom/automations/bedroom_scene_switch_sona.yaml

mv packages/areas/bedroom/automations/scene_switch_jakub.yaml \
   packages/areas/bedroom/automations/bedroom_scene_switch_jakub.yaml

# Kitchen
mv packages/areas/kitchen/automations/cooking_mode_off.yaml \
   packages/areas/kitchen/automations/kitchen_cooking_mode_timeout.yaml

# Living Room
mv packages/areas/living_room/automations/tv.yaml \
   packages/areas/living_room/automations/living_room_tv_playback.yaml
```

### DELETE These Files (After Consolidation)

```bash
rm packages/areas/bedroom/automations/bedroom_switch_off_big_lights_when_bed_lights_on.yaml
rm packages/areas/bedroom/automations/bedroom_switch_off_bed_stripe_when_other_lights_on.yaml
# cube_jakub.yaml already moved, not deleted
```

### MODIFY These Files

1. **packages/areas/bedroom/config.yaml** - Add movie mode input_boolean
2. **packages/areas/bedroom/automations/bedroom_presence.yaml** - Replace TV conditions

---

## Validation Commands

```bash
# Validate YAML syntax
yamllint .

# Check Home Assistant configuration (requires HA CLI or container)
hass --script check_config -c .

# Verify naming convention compliance
find packages/areas -name "*.yaml" -path "*/automations/*" | \
  xargs -I{} basename {} | \
  grep -v "^[a-z_]*_[a-z_]*_[a-z_]*\.yaml$"
# Should return empty (no violations)
```

---

## Testing Checklist

### Bedroom Movie Mode
- [ ] Enter bedroom with movie mode OFF → Lights turn on
- [ ] Enter bedroom with movie mode ON → Lights stay off
- [ ] Toggle movie mode ON/OFF in UI → State changes correctly
- [ ] Movie mode + leave bedroom → Lights turn off (override doesn't block exit)

### Light Exclusivity
- [ ] Turn on bed lights → Other lights turn off
- [ ] Turn on main lights → Bed stripe turns off
- [ ] Both work in either direction

### Cube Controller
- [ ] Cube gestures still work after relocation
- [ ] Living room TV responds to cube
- [ ] Ground floor lights respond to cube

### Bathroom Occupancy
- [ ] Occupancy detected → Lights on
- [ ] Occupancy cleared → Lights off after delay
- [ ] Stay still in bathroom → Lights remain on

### General
- [ ] All files pass yamllint
- [ ] Home Assistant config validates
- [ ] No automation errors in HA logs

---

## Rollback Plan

If issues arise:

```bash
# Revert all changes
git checkout main -- packages/

# Or selectively revert specific files
git checkout main -- packages/areas/bedroom/automations/bedroom_presence.yaml
```

---

## Success Criteria Verification

| Criterion | How to Verify |
|-----------|---------------|
| SC-001: Bedroom lights within 2s | Time from entering bedroom to lights on |
| SC-002: 100% naming compliance | Run find command above, expect empty output |
| SC-003: Zero cross-area refs in areas | Grep for entity patterns in area automations |
| SC-004: 2→1 light automations | Count files in bedroom/automations |
| SC-005: Bathroom 30min stillness | Sit still in bathroom, verify lights stay |
| SC-006: yamllint passes | `yamllint .` returns exit code 0 |
| SC-007: Compliance 8.5/10 | Re-run constitution audit |
