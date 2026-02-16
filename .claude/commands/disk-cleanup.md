# Claude Command: Disk Cleanup

Perform disk optimization and cleanup on the Home Assistant instance via SSH. This command actively frees disk space — it is NOT read-only.

## What This Command Does

Connects to `root@homeassistant.local` via SSH and performs a series of disk cleanup actions: removes old log files, purges/repacks the recorder database, deletes old backups, vacuums journal logs, and prunes unused Docker images via supervisor repair. Reports disk usage before and after.

## Usage

```bash
# Full cleanup (all actions)
/disk-cleanup

# Dry run — report disk usage without changing anything
/disk-cleanup dry-run

# Specific cleanup targets
/disk-cleanup logs        # Old HA log files + journal vacuum
/disk-cleanup database    # Recorder purge + repack
/disk-cleanup backups     # Delete old backups
/disk-cleanup docker      # Supervisor repair (prunes unused images)
```

## SSH Access

All remote commands use: `ssh root@homeassistant.local '<command>'`

Commands that interact with the Supervisor API use:
```bash
curl -s [-X POST] http://supervisor/<endpoint> \
  -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
  -H "Content-Type: application/json"
```

**IMPORTANT:** Always use `dangerouslyDisableSandbox: true` for SSH commands since they connect to a remote host.

## Workflow Steps

### Step 0: Parse Arguments

1. Parse the focus argument (if provided):
   - `dry-run` → only report, skip all cleanup actions
   - `logs` → Step 2 only
   - `database` / `db` → Step 3 only
   - `backups` → Step 4 only
   - `docker` / `images` → Step 5 only
   - No argument → run all steps
2. Inform user which actions will be performed

### Step 1: Baseline Disk Usage

Run these commands **in parallel** via SSH:

```bash
# Overall disk usage
df -h / | tail -1

# Largest consumers in HA config
du -sh /homeassistant/* 2>/dev/null | sort -rh | head -15

# HA host disk info
ha host info --raw-json

# Backup list
ha backups list --raw-json
```

Present a summary table:

| Item | Size |
|------|------|
| Disk total / used / free | ... |
| Recorder DB | ... |
| Old log files | ... |
| Custom components | ... |
| Backups | ... |

**If dry-run:** Stop here and present the report.

### Step 2: Clean Old Log Files

Find and remove old/rotated Home Assistant log files:

```bash
# List old logs first
ls -lh /homeassistant/home-assistant.log.old \
       /homeassistant/home-assistant.log.1 \
       /homeassistant/home-assistant.log.fault 2>/dev/null

# Delete them (only files that exist and are >0 bytes)
rm -f /homeassistant/home-assistant.log.old \
      /homeassistant/home-assistant.log.1
```

Also attempt journal vacuum (may fail from within the SSH addon — that's OK):

```bash
journalctl --vacuum-size=100M 2>/dev/null || echo "Journal vacuum not available from this context"
```

Report bytes freed.

### Step 3: Purge & Repack Recorder Database

Call the recorder.purge service via the Supervisor API:

```bash
curl -s -X POST http://supervisor/core/api/services/recorder/purge \
  -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"keep_days": 5, "repack": true}'
```

**Note:** The repack runs asynchronously in the background. The DB file size won't change immediately. Inform the user that the repack may take several minutes to complete and that they can re-run `/disk-cleanup dry-run` later to verify.

### Step 4: Delete Old Backups

1. List backups: `ha backups list --raw-json`
2. If backups exist, present the list with dates and sizes
3. Ask user which to delete (or offer to delete all except the most recent)
4. Delete selected: `ha backups remove <slug>`
5. If no backups exist, report "No backups found"

### Step 5: Supervisor Repair (Docker Image Prune)

Run supervisor repair which prunes unused Docker images and layers:

```bash
curl -s -X POST http://supervisor/supervisor/repair \
  -H "Authorization: Bearer ${SUPERVISOR_TOKEN}"
```

**IMPORTANT:** This can take several minutes (2-5+) as it pulls fresh images after pruning old ones. Run with a long timeout (300s+). Inform the user this step takes the longest but typically frees the most space (often 1-3GB from old HA core and addon images).

### Step 6: Final Report

Run the same baseline commands from Step 1 to get new disk usage. Present a before/after comparison:

```
## Disk Cleanup Results

| Metric | Before | After | Freed |
|--------|--------|-------|-------|
| Disk used | X.XG | X.XG | X.XG |
| Disk free | X.XG | X.XG | +X.XG |
| Disk usage | XX% | XX% | -XX% |
| Recorder DB | XXXMB | XXXMB | * |

* DB repack runs async — check again in a few minutes
```

If disk usage is still above 80%, suggest additional actions:
- Check for large custom_components that could be removed
- Consider moving to external database (PostgreSQL)
- Consider adding external storage via USB
- Review addon list for unused addons

## Error Handling

- **SSH connection fails:** Inform user to check SSH addon is running and accessible
- **Supervisor API returns error:** Report the error, continue with other steps
- **Permission denied on file deletion:** Report and skip that file
- **Supervisor repair times out:** Inform user it's still running in background, suggest checking later

## Safety Notes

- This command **modifies** the system (deletes files, purges DB, prunes images)
- The recorder purge uses `keep_days: 5` — this matches the configured retention in `packages/bootstrap/config.yaml`
- Old log files (`.log.old`, `.log.1`) are safe to delete — HA doesn't need them
- Supervisor repair only removes unused/dangling Docker images — running containers are never affected
- Backups are only deleted with user confirmation
