# Claude Command: Troubleshoot

Diagnose Home Assistant system health by running local configuration checks and remote system inspection via browser automation. Generates a markdown report with findings and recommendations.

## What This Command Does

Performs comprehensive Home Assistant health diagnostics combining local configuration validation with remote system inspection. Identifies issues with disk space, database health, entity availability, integration status, and error logs. Supports focused diagnostics for specific subsystems or full system analysis. Researches official Home Assistant documentation for relevant troubleshooting guidance based on issues found.

## Usage

```bash
# Full diagnostic (all checks)
/troubleshoot

# Focus on specific area
/troubleshoot disk         # Disk space and storage issues
/troubleshoot database     # Database size and recorder health
/troubleshoot entities     # Entity availability and states
/troubleshoot logs         # Error log analysis
/troubleshoot integrations # Integration status and failures
/troubleshoot local        # Only local checks (no browser needed)
/troubleshoot system       # System resources (disk, memory, CPU)
```

## Environment Setup

### Required Credentials

Read credentials from the `.env` file in the repository root:

```
HOMEASSISTANT_URL=http://homeassistant.local:8123
HOMEASSISTANT_USER=<username>
HOMEASSISTANT_PASSWORD=<password>
```

### Key URLs

- Home Assistant: `$HOMEASSISTANT_URL` (from .env)
- System Health: `$HOMEASSISTANT_URL/config/system`
- Developer Tools: `$HOMEASSISTANT_URL/developer-tools/state`
- Logs: `$HOMEASSISTANT_URL/config/logs`
- Integrations: `$HOMEASSISTANT_URL/config/integrations`

## Workflow Steps

### Step 0: Parse Arguments & Tool Check

1. Parse the focus argument (if provided) to determine scope
2. Map keywords to check categories:
   - `local` → skip remote checks entirely
   - `disk`/`storage` → local large files + remote disk usage
   - `database`/`db` → remote database inspection
   - `entities` → remote entity health
   - `logs`/`errors` → remote log analysis
   - `integrations` → remote integration status
   - `system`/`resources` → remote system metrics
   - No argument → run all checks
3. Verify Playwright MCP server is available (check for `mcp__playwright__*` tools)
4. If Playwright MCP not available and remote checks needed:
   - Inform user that browser automation requires Playwright MCP server
   - If focus is `local`, continue with local checks only
   - Otherwise, suggest checking MCP configuration and exit gracefully

### Step 1: Environment Validation

1. Read `.env` file from repository root
2. Verify required variables: `HOMEASSISTANT_URL`, `HOMEASSISTANT_USER`, `HOMEASSISTANT_PASSWORD`
3. Parse and validate the URL format
4. If focus is `local`, skip credential validation
5. Inform user of missing credentials and exit if critical ones missing for remote checks

### Step 2: Local Checks

Run these checks locally (no browser needed):

#### 2a: YAML Validation

1. Run `yamllint .` and capture output
2. Count errors vs warnings
3. List files with errors
4. Flag as issue if any errors found

#### 2b: Git Status

1. Run `git status --porcelain` to check uncommitted changes
2. Run `git branch --show-current` for current branch
3. Count modified/added/deleted files
4. Flag as info if uncommitted changes exist

#### 2c: Configuration Analysis

1. Use `find` to identify large files (>500KB) in packages/
2. Count total YAML files and lines
3. Identify largest configuration files
4. Flag if any file exceeds reasonable size

**If focus is `local`, skip to Step 9 (Generate Report)**

### Step 3: Browser Authentication

Use Playwright MCP to login to Home Assistant:

1. Navigate to `$HOMEASSISTANT_URL` using `mcp__playwright__browser_navigate`
2. Take a snapshot using `mcp__playwright__browser_snapshot` to analyze the page
3. Check if already authenticated (sidebar visible = skip login)
4. If on login page:
   - Fill username field
   - Fill password field
   - Click submit button
5. Wait for navigation and verify sidebar appears (successful login)

**Error Handling**:

- If already logged in (sidebar visible), proceed to next step
- If login fails after submit, report credentials issue and stop
- If HA unreachable, check URL and network connectivity
- If MFA/2FA prompt appears, inform user this isn't supported

### Step 4: System Resources Check

**Run if:** focus is `system`, `disk`, `storage`, or full diagnostic

Navigate to `/config/system` or use Developer Tools:

1. Take snapshot of system page
2. Extract:
   - **Disk usage**: total, used, free, percentage
   - **Memory usage**: total, used, percentage
   - **CPU**: current load or usage
   - **Home Assistant version**
   - **Uptime**
3. Flag issues:
   - CRITICAL: Disk >95%
   - HIGH: Disk >85% or Memory >90%
   - MEDIUM: Disk >75% or Memory >80%

### Step 5: Database Health Check

**Run if:** focus is `database`, `db`, `disk`, or full diagnostic

From system page or `/developer-tools/statistics`:

1. Extract:
   - **Database size** (MB/GB)
   - **Database type** (SQLite/PostgreSQL)
   - **Recorder status**
2. Flag issues:
   - HIGH: Database >2GB on SQLite
   - MEDIUM: Database >1GB
   - INFO: Database stats for reference

### Step 6: Entity Health Check

**Run if:** focus is `entities` or full diagnostic

Navigate to `/developer-tools/state`:

1. Take snapshot of states page
2. Extract:
   - **Total entity count**
   - **Unavailable entities** (state = "unavailable")
   - **Unknown state entities** (state = "unknown")
3. List sample of unavailable entities (up to 10)
4. Group unavailable by domain if possible
5. Flag issues:
   - HIGH: >10% entities unavailable
   - MEDIUM: >5% entities unavailable
   - MEDIUM: Any entities with unknown state

### Step 7: Integration & Log Analysis

**Run if:** focus is `integrations`, `logs`, `errors`, or full diagnostic

#### 7a: Integration Status

Navigate to `/config/integrations`:

1. Take snapshot
2. Count:
   - Total integrations
   - Failed integrations
   - Integrations needing attention
3. List failed integration names
4. Flag issues:
   - CRITICAL: Core integrations failed (MQTT, Zigbee2MQTT)
   - HIGH: Any integration failed

#### 7b: Error Log Analysis

Navigate to `/config/logs`:

1. Take snapshot of logs page
2. Count:
   - ERROR entries visible
   - WARNING entries visible
3. Extract last few distinct error messages
4. Look for patterns (connection refused, timeout, unavailable)
5. Flag issues:
   - HIGH: Many recent errors (>20 visible)
   - MEDIUM: Some errors (>5 visible)
   - LOW: Only warnings

### Step 8: Documentation Research

**Run if:** Any issues were found in previous steps

Use `WebFetch` to research relevant Home Assistant documentation at `https://www.home-assistant.io`:

1. **Based on issues found**, fetch relevant documentation pages:
   - Disk/storage issues: `https://www.home-assistant.io/integrations/recorder/#purge`
   - Database optimization: `https://www.home-assistant.io/integrations/recorder/`
   - Entity issues: `https://www.home-assistant.io/docs/configuration/state_object/`
   - Integration failures: `https://www.home-assistant.io/integrations/{integration_name}/`
   - Performance issues: `https://www.home-assistant.io/docs/backend/database/`

2. **Common documentation lookups**:

   | Issue Type | Documentation URL |
   |------------|-------------------|
   | Database too large | `/integrations/recorder/#purge` |
   | Recorder configuration | `/integrations/recorder/` |
   | Entity unavailable | `/docs/configuration/state_object/` |
   | High memory usage | `/docs/installation/performance/` |
   | Integration errors | `/integrations/{name}/` |
   | YAML syntax | `/docs/configuration/yaml/` |

3. **Extract from documentation**:
   - Recommended configuration options
   - Troubleshooting steps specific to the issue
   - Best practices and optimization tips
   - Any known issues or workarounds

4. **Include in recommendations**:
   - Link to relevant documentation pages
   - Summarize key troubleshooting steps
   - Provide example YAML configurations where applicable

**Example WebFetch calls**:

```
WebFetch(url="https://www.home-assistant.io/integrations/recorder/",
         prompt="Extract configuration options for reducing database size and purging old data")

WebFetch(url="https://www.home-assistant.io/docs/installation/performance/",
         prompt="Extract tips for improving Home Assistant performance and reducing memory usage")
```

### Step 9: Generate Report

Create markdown report `.reports/TROUBLESHOOT_REPORT.md`:

```markdown
# Home Assistant Troubleshooting Report

**Generated:** {timestamp}
**Focus:** {focus_area or "Full Diagnostic"}

---

## Summary

| Category | Status | Issues |
|----------|--------|--------|
| Local Config | {OK/Warning/Error} | {count} |
| System Resources | {OK/Warning/Critical} | {count} |
| Database | {OK/Warning/Error} | {count} |
| Entities | {OK/Warning/Error} | {count} |
| Integrations | {OK/Warning/Error} | {count} |
| Logs | {OK/Warning/Error} | {count} |

**Overall Health:** {Good/Fair/Poor/Critical}

---

## Issues Found

### Critical
{list of critical issues or "None"}

### High Priority
{list of high priority issues or "None"}

### Medium Priority
{list of medium priority issues or "None"}

### Low Priority / Info
{list of low priority issues or "None"}

---

## Detailed Findings

### Local Configuration
- **YAML Validation:** {pass/fail} ({error_count} errors, {warning_count} warnings)
- **Git Status:** {clean/uncommitted} ({file_count} files changed)
- **Large Files:** {list or "None"}

### System Resources
- **Disk:** {used}/{total} ({percent}%)
- **Memory:** {used}/{total} ({percent}%)
- **HA Version:** {version}
- **Uptime:** {uptime}

### Database Health
- **Size:** {size}
- **Type:** {type}
- **Status:** {status}

### Entity Health
- **Total Entities:** {count}
- **Unavailable:** {count} ({percent}%)
- **Unknown State:** {count}

**Sample Unavailable Entities:**
{list of up to 10 unavailable entities}

### Integration Status
- **Total:** {count}
- **Failed:** {count}

**Failed Integrations:**
{list or "None"}

### Recent Errors
**Error Count:** {count}
**Warning Count:** {count}

**Recent Error Messages:**
{list of distinct error messages}

---

## Recommendations

{actionable recommendations based on findings}

---

## Documentation References

{links to relevant Home Assistant documentation based on issues found}

---

*Report generated by /troubleshoot command*
```

### Step 10: Cleanup

1. Close browser session using `mcp__playwright__browser_close`
2. Confirm report saved to `.reports/TROUBLESHOOT_REPORT.md`
3. Present summary to user with key findings
4. Suggest next steps based on severity of issues found

## Error Handling

### Authentication Failures

- Verify `.env` credentials are correct
- Test HA URL manually in browser
- Check for MFA/2FA that may require additional handling

### Page Load Timeouts

- Increase wait times for slow systems
- Use explicit waits for key elements
- Retry navigation on timeout

### Missing Data

- If a metric can't be extracted, note as "Unable to determine"
- Continue with other checks
- Don't fail entire diagnostic for one missing metric

### Playwright MCP Unavailable

- For `local` focus: proceed with local checks only
- For other focuses: inform user and suggest checking MCP config
- Provide instructions to enable Playwright MCP

## Common Issues & Solutions

| Issue | Likely Cause | Recommendation |
|-------|--------------|----------------|
| Disk >90% | Old backups, large database | Delete old backups, purge DB |
| Database >2GB | Too many entities recorded | Exclude entities from recorder |
| Many unavailable entities | Integration down, devices offline | Check integrations, network |
| YAML errors | Syntax mistakes | Run `yamllint` and fix errors |
| Integration failed | Config issue, service down | Check integration logs, reconfigure |
| High memory | Too many integrations, add-ons | Disable unused, upgrade hardware |

## Example Output

### Healthy System

```
## Summary
| Category | Status | Issues |
|----------|--------|--------|
| Local Config | OK | 0 |
| System Resources | OK | 0 |
| Database | OK | 0 |
| Entities | OK | 0 |
| Integrations | OK | 0 |
| Logs | OK | 2 |

**Overall Health:** Good

## Issues Found
### Low Priority / Info
- 2 warnings in logs (non-critical)
- Git: 3 uncommitted changes
```

### System with Issues

```
## Summary
| Category | Status | Issues |
|----------|--------|--------|
| Local Config | Warning | 2 |
| System Resources | Critical | 1 |
| Database | Warning | 1 |
| Entities | Warning | 1 |
| Integrations | Error | 1 |
| Logs | Warning | 1 |

**Overall Health:** Poor

## Issues Found
### Critical
- Disk usage at 96% (18.2GB / 19GB) - immediate action required

### High Priority
- MQTT integration failed to load
- 47 entities unavailable (12%)

### Medium Priority
- Database size 4.2GB on SQLite
- 8 YAML syntax errors in configuration
```

## Notes

- This command is **read-only** - it gathers information but doesn't modify settings
- Browser session is closed after data collection
- Credentials are never displayed in the report
- Report overwrites previous `.reports/TROUBLESHOOT_REPORT.md` (not timestamped to avoid clutter)
- For Zigbee-specific issues, use `/zigbee-debug` command instead
