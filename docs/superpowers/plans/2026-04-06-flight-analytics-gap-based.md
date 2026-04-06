# Flight Analytics: Gap-Based Quiet Windows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hour-bucketed quiet window detection with gap-based analysis using actual flight timestamps, and add a timeline visualization showing quiet periods per day-of-week.

**Architecture:** All changes in a single file (`flight-tracker/static/dashboard.html`). Replace `computeStats`'s quiet window logic with gap-based computation at 15-minute resolution. Replace the text-based quiet windows card with an SVG timeline. Update the hero stat.

**Tech Stack:** Vanilla JavaScript, inline SVG for timeline visualization, Chart.js (existing, unchanged)

---

### Task 1: Replace `computeStats` quiet window logic with gap-based computation

**Files:**
- Modify: `flight-tracker/static/dashboard.html:400-470`

The current `computeStats` function uses `findQuietWindows` which operates on hourly noise averages. Replace it with gap-based analysis that works on actual flight timestamps at 15-minute resolution.

- [ ] **Step 1: Replace `findQuietWindows` and quiet window computation inside `computeStats`**

Replace the `findQuietWindows` function (lines 425-448), the `quietWindows` call (line 451), and the `dayQuietWindows` computation (lines 457-468) with the new gap-based logic. The new code goes inside `computeStats`, after the existing `hourAvg`/`hourNoiseAvg` computation (which stays for the hourly chart).

Find this block (starting at line 425, ending at line 468):
```javascript
        function findQuietWindows(noiseArr) {
            const daytimeNoise = noiseArr.slice(6, 23);
            const sorted = [...daytimeNoise].sort((a, b) => a - b);
            const median = sorted[Math.floor(sorted.length / 2)] || 0;
            const threshold = Math.max(median, 0.001);
            const windows = [];
            let ws = null;
            for (let h = 6; h <= 22; h++) {
                if (noiseArr[h] <= threshold) {
                    if (ws === null) ws = h;
                } else {
                    if (ws !== null && (h - ws) >= 2) {
                        const avgNoise = noiseArr.slice(ws, h).reduce((a,b) => a+b, 0) / (h - ws);
                        const avgFlights = hourAvg.slice(ws, h).reduce((a,b) => a+b, 0) / (h - ws);
                        windows.push({ start: ws, end: h, avgNoise, avgFlights });
                    }
                    ws = null;
                }
            }
            if (ws !== null && (23 - ws) >= 2) {
                const avgNoise = noiseArr.slice(ws, 23).reduce((a,b) => a+b, 0) / (23 - ws);
                const avgFlights = hourAvg.slice(ws, 23).reduce((a,b) => a+b, 0) / (23 - ws);
                windows.push({ start: ws, end: 23, avgNoise, avgFlights });
            }
            return windows.sort((a, b) => a.avgNoise - b.avgNoise);
        }
        const quietWindows = findQuietWindows(hourNoiseAvg);

        const busiestHour = hourNoiseAvg.indexOf(Math.max(...hourNoiseAvg));

        const topRoutes = Object.entries(routes).sort((a,b) => b[1] - a[1]).slice(0, 5);

        const dayQuietWindows = {};
        const datesPerDow = Array.from({length: 7}, () => new Set());
        flights.forEach(f => {
            const dow = new Date(f.date).getDay();
            datesPerDow[dow].add(f.date);
        });

        for (let dow = 0; dow < 7; dow++) {
            const numDaysForDow = datesPerDow[dow].size || 1;
            const dowNoiseAvg = dayHourNoise[dow].map(n => n / numDaysForDow);
            dayQuietWindows[dow] = findQuietWindows(dowNoiseAvg);
        }
```

Replace with:
```javascript
        const busiestHour = hourNoiseAvg.indexOf(Math.max(...hourNoiseAvg));
        const topRoutes = Object.entries(routes).sort((a,b) => b[1] - a[1]).slice(0, 5);

        // --- Gap-based quiet window detection ---
        // Group flights by date, sorted by time
        const byDate = {};
        flights.forEach(f => {
            if (!f.date || !f.time_local) return;
            if (!byDate[f.date]) byDate[f.date] = [];
            byDate[f.date].push(f.time_local);
        });

        // Convert "HH:MM:SS" or "HH:MM" to minutes since midnight
        function timeToMin(t) {
            const parts = t.split(':');
            return parseInt(parts[0]) * 60 + parseInt(parts[1] || 0);
        }

        // Round down to nearest 15-min slot (returns minutes)
        function toSlot(min) {
            return Math.floor(min / 15) * 15;
        }

        // Daytime boundaries in minutes
        const DAY_START = 6 * 60;   // 06:00
        const DAY_END = 22 * 60;    // 22:00
        const SLOT_COUNT = (DAY_END - DAY_START) / 15; // 64 slots

        // For each date, mark which 15-min slots had flights
        const datesPerDow = Array.from({length: 7}, () => []);
        // slotQuiet[dow][slotIdx] = count of days where that slot was flight-free
        const slotQuietCount = Array.from({length: 7}, () => Array(SLOT_COUNT).fill(0));

        Object.entries(byDate).forEach(([date, times]) => {
            const dow = new Date(date).getDay();
            datesPerDow[dow].push(date);

            // Mark slots that have flights
            const busySlots = new Set();
            times.forEach(t => {
                const min = timeToMin(t);
                if (min >= DAY_START && min < DAY_END) {
                    busySlots.add(Math.floor((min - DAY_START) / 15));
                }
            });

            // Count quiet slots for this day
            for (let s = 0; s < SLOT_COUNT; s++) {
                if (!busySlots.has(s)) {
                    slotQuietCount[dow][s]++;
                }
            }
        });

        // Compute quiet probability per slot per DOW
        // slotProb[dow][slotIdx] = fraction of days that slot was quiet
        const slotProb = Array.from({length: 7}, (_, dow) => {
            const numDaysForDow = datesPerDow[dow].length || 1;
            return slotQuietCount[dow].map(c => c / numDaysForDow);
        });

        // Determine dynamic quiet threshold: slot is "quiet" if flight-free >50% of days
        // With sparse data (<3 days), require >75%
        function quietThreshold(numDays) {
            return numDays < 3 ? 0.75 : 0.5;
        }

        // Merge consecutive quiet slots into windows for a given DOW
        function findGapWindows(probs, numDays) {
            const thresh = quietThreshold(numDays);
            const windows = [];
            let wsSlot = null;
            let probSum = 0;
            let slotCount = 0;

            for (let s = 0; s <= SLOT_COUNT; s++) {
                if (s < SLOT_COUNT && probs[s] >= thresh) {
                    if (wsSlot === null) wsSlot = s;
                    probSum += probs[s];
                    slotCount++;
                } else {
                    if (wsSlot !== null) {
                        const startMin = DAY_START + wsSlot * 15;
                        const endMin = DAY_START + s * 15;
                        const durationMin = endMin - startMin;
                        windows.push({
                            startMin,
                            endMin,
                            durationMin,
                            avgProb: probSum / slotCount,
                            sparse: numDays < 3
                        });
                    }
                    wsSlot = null;
                    probSum = 0;
                    slotCount = 0;
                }
            }
            return windows;
        }

        // Compute all gaps across all observed dates to find median gap duration
        const allGapDurations = [];
        Object.entries(byDate).forEach(([date, times]) => {
            const mins = times.map(timeToMin).filter(m => m >= DAY_START && m < DAY_END).sort((a, b) => a - b);
            // Gap from day start to first flight
            if (mins.length > 0) {
                allGapDurations.push(mins[0] - DAY_START);
                // Gaps between consecutive flights
                for (let i = 1; i < mins.length; i++) {
                    allGapDurations.push(mins[i] - mins[i - 1]);
                }
                // Gap from last flight to day end
                allGapDurations.push(DAY_END - mins[mins.length - 1]);
            } else {
                allGapDurations.push(DAY_END - DAY_START);
            }
        });
        const sortedGaps = [...allGapDurations].filter(d => d > 0).sort((a, b) => a - b);
        const medianGap = sortedGaps.length > 0 ? sortedGaps[Math.floor(sortedGaps.length / 2)] : 30;
        // Minimum window: at least median gap, but no less than 15 min
        const minWindowMin = Math.max(medianGap, 15);

        // Build dayQuietWindows with gap-based detection
        const dayQuietWindows = {};
        for (let dow = 0; dow < 7; dow++) {
            const raw = findGapWindows(slotProb[dow], datesPerDow[dow].length);
            dayQuietWindows[dow] = raw.filter(w => w.durationMin >= minWindowMin)
                .sort((a, b) => b.durationMin - a.durationMin);
        }

        // Overall best quiet window (longest across all DOWs)
        const allWindows = [];
        for (let dow = 0; dow < 7; dow++) {
            dayQuietWindows[dow].forEach(w => allWindows.push({ ...w, dow }));
        }
        const bestQuiet = allWindows.sort((a, b) => b.durationMin - a.durationMin)[0] || null;
```

- [ ] **Step 2: Update the return statement of `computeStats`**

Find:
```javascript
        return { hourCounts, hourAvg, hourNoiseAvg, dayHourCounts, dayHourNoise, numDays, totalFlights: flights.length, quietWindows, dayQuietWindows, busiestHour, topRoutes };
```

Replace with:
```javascript
        return { hourCounts, hourAvg, hourNoiseAvg, dayHourCounts, dayHourNoise, numDays, totalFlights: flights.length, dayQuietWindows, bestQuiet, busiestHour, topRoutes, slotProb, datesPerDow, minWindowMin, DAY_START, DAY_END, SLOT_COUNT };
```

- [ ] **Step 3: Commit**

```bash
git add flight-tracker/static/dashboard.html
git commit -m "refactor: replace hour-bucketed quiet windows with gap-based detection"
```

---

### Task 2: Add `formatMinutes` helper and update hero stat

**Files:**
- Modify: `flight-tracker/static/dashboard.html:483` (formatHour area)
- Modify: `flight-tracker/static/dashboard.html:487-521` (render function hero stat)

- [ ] **Step 1: Add `formatMinutes` helper next to existing `formatHour`**

Find:
```javascript
    function formatHour(h) { return `${h.toString().padStart(2,'0')}:00`; }
```

Replace with:
```javascript
    function formatHour(h) { return `${h.toString().padStart(2,'0')}:00`; }
    function formatMinutes(totalMin) {
        const h = Math.floor(totalMin / 60);
        const m = totalMin % 60;
        return `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}`;
    }
```

- [ ] **Step 2: Update hero stat to use gap-based `bestQuiet` from stats**

Find:
```javascript
        const bestQuiet = stats.quietWindows.sort((a,b) => (b.end - b.start) - (a.end - a.start))[0];
```

Replace with (remove the line entirely — `bestQuiet` is now part of stats):
```javascript
        const bestQuiet = stats.bestQuiet;
```

Then find the hero stat card that renders `bestQuiet`:
```javascript
                <div class="stat">
                    <div class="value ${bestQuiet ? 'quiet' : ''}">${bestQuiet ? formatHour(bestQuiet.start) + ' - ' + formatHour(bestQuiet.end) : 'N/A'}</div>
                    <div class="label">Quietest window${bestQuiet ? ' (' + bestQuiet.avgFlights.toFixed(1) + ' flights/h, noise ' + bestQuiet.avgNoise.toFixed(3) + ')' : ''}</div>
                </div>
```

Replace with:
```javascript
                <div class="stat">
                    <div class="value ${bestQuiet ? 'quiet' : ''}">${bestQuiet ? formatMinutes(bestQuiet.startMin) + ' - ' + formatMinutes(bestQuiet.endMin) : 'N/A'}</div>
                    <div class="label">Best quiet window${bestQuiet ? ' (' + Math.round(bestQuiet.durationMin) + ' min, ' + Math.round(bestQuiet.avgProb * 100) + '% quiet' + (bestQuiet.sparse ? ', limited data' : '') + ')' : ''}</div>
                </div>
```

- [ ] **Step 3: Commit**

```bash
git add flight-tracker/static/dashboard.html
git commit -m "feat: update hero stat to show gap-based best quiet window"
```

---

### Task 3: Replace quiet windows card with SVG timeline visualization

**Files:**
- Modify: `flight-tracker/static/dashboard.html:530-557` (quiet windows card)
- Modify: `flight-tracker/static/dashboard.html:8-42` (add CSS for timeline)

- [ ] **Step 1: Add CSS for the timeline visualization**

Find:
```css
        canvas { max-height: 300px; }
```

Replace with:
```css
        canvas { max-height: 300px; }

        /* Timeline visualization */
        .timeline-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
        .timeline-label { width: 36px; font-weight: 600; font-size: 0.85rem; flex-shrink: 0; }
        .timeline-bar-wrap { flex: 1; position: relative; height: 28px; background: #0f172a; border-radius: 4px; overflow: hidden; }
        .timeline-slot { position: absolute; top: 0; height: 100%; border-radius: 2px; }
        .timeline-slot:hover { outline: 1px solid #e2e8f0; z-index: 1; }
        .timeline-axis { display: flex; margin-left: 46px; margin-bottom: 8px; }
        .timeline-axis span { flex: 1; text-align: left; color: #64748b; font-size: 0.7rem; }
        .timeline-tooltip { position: absolute; background: #334155; color: #e2e8f0; padding: 6px 10px; border-radius: 6px; font-size: 0.75rem; white-space: nowrap; z-index: 10; pointer-events: none; transform: translateX(-50%); bottom: 34px; }
        .timeline-sparse { font-size: 0.7rem; color: #fbbf24; margin-left: 4px; }
        .timeline-legend { display: flex; gap: 16px; margin-top: 10px; font-size: 0.75rem; color: #94a3b8; }
        .timeline-legend-swatch { display: inline-block; width: 12px; height: 12px; border-radius: 2px; margin-right: 4px; vertical-align: middle; }
```

- [ ] **Step 2: Replace the quiet windows card HTML in the `render` function**

Find the entire quiet windows card block:
```javascript
                <div class="card">
                    <h2>Quietest Garden Windows by Day</h2>
                    <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 12px;">
                        Consecutive 2h+ blocks with lowest noise score (below median)
                    </p>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        ${[1,2,3,4,5,6,0].map(dow => {
                            const windows = stats.dayQuietWindows[dow] || [];
                            const longestWindow = windows.sort((a,b) => (b.end - b.start) - (a.end - a.start))[0];
                            return `
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div style="width: 36px; font-weight: 600; color: ${dow === 0 || dow === 6 ? '#818cf8' : '#e2e8f0'}; font-size: 0.85rem;">${DAYS[dow]}</div>
                                    <div style="flex: 1; display: flex; gap: 6px; flex-wrap: wrap;">
                                        ${windows.length === 0
                                            ? '<span style="color: #64748b; font-size: 0.8rem;">No data yet</span>'
                                            : windows.map((w, i) => `
                                                <span style="background: ${i === 0 ? '#14532d' : '#1e293b'}; border: 1px solid ${i === 0 ? '#16a34a' : '#334155'}; border-radius: 6px; padding: 3px 8px; font-size: 0.8rem;">
                                                    ${formatHour(w.start)}-${formatHour(w.end)}
                                                    <span style="color: #64748b; font-size: 0.7rem;">${(w.end - w.start)}h &middot; ${w.avgFlights.toFixed(1)}/h</span>
                                                </span>
                                            `).join('')
                                        }
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
```

Replace with:
```javascript
                <div class="card">
                    <h2>Quietest Garden Windows by Day</h2>
                    <p style="color: #94a3b8; font-size: 0.8rem; margin-bottom: 12px;">
                        Green segments show times that are typically flight-free (based on ${stats.numDays} days of data, ${stats.minWindowMin}+ min gaps)
                    </p>
                    <div class="timeline-axis">
                        ${Array.from({length: 9}, (_, i) => `<span>${formatHour(6 + i * 2)}</span>`).join('')}
                    </div>
                    ${[1,2,3,4,5,6,0].map(dow => {
                        const windows = stats.dayQuietWindows[dow] || [];
                        const numDays = stats.datesPerDow[dow].length;
                        const totalMin = stats.DAY_END - stats.DAY_START;
                        return `
                            <div class="timeline-row">
                                <div class="timeline-label" style="color: ${dow === 0 || dow === 6 ? '#818cf8' : '#e2e8f0'};">${DAYS[dow]}${numDays < 3 ? '<span class="timeline-sparse" title="Limited data">*</span>' : ''}</div>
                                <div class="timeline-bar-wrap" data-dow="${dow}">
                                    ${numDays === 0
                                        ? '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#64748b;font-size:0.75rem;">No data</div>'
                                        : windows.map(w => {
                                            const left = ((w.startMin - stats.DAY_START) / totalMin * 100).toFixed(2);
                                            const width = (w.durationMin / totalMin * 100).toFixed(2);
                                            const opacity = (0.4 + 0.6 * w.avgProb).toFixed(2);
                                            const label = formatMinutes(w.startMin) + '-' + formatMinutes(w.endMin) + ' (' + Math.round(w.durationMin) + 'min, ' + Math.round(w.avgProb * 100) + '% quiet)';
                                            return `<div class="timeline-slot" style="left:${left}%;width:${width}%;background:rgba(74,222,128,${opacity});" title="${label}"></div>`;
                                        }).join('')
                                    }
                                </div>
                            </div>
                        `;
                    }).join('')}
                    <div class="timeline-legend">
                        <span><span class="timeline-legend-swatch" style="background:rgba(74,222,128,1.0);"></span>Very likely quiet (>80%)</span>
                        <span><span class="timeline-legend-swatch" style="background:rgba(74,222,128,0.55);"></span>Often quiet (~50%)</span>
                        <span>* Limited data (&lt;3 days)</span>
                    </div>
                </div>
```

- [ ] **Step 3: Commit**

```bash
git add flight-tracker/static/dashboard.html
git commit -m "feat: add timeline visualization for gap-based quiet windows"
```

---

### Task 4: Verify and clean up

**Files:**
- Modify: `flight-tracker/static/dashboard.html` (remove any dead CSS if present)

- [ ] **Step 1: Verify no references to old `quietWindows` (non-day) remain**

Search for `quietWindows` in the file (excluding `dayQuietWindows`). The old code had `stats.quietWindows` — ensure it's gone. The only references should be to `stats.dayQuietWindows` and `stats.bestQuiet`.

Run:
```bash
grep -n 'quietWindows' flight-tracker/static/dashboard.html | grep -v dayQuietWindows
```

Expected: No output (no remaining references to the old `quietWindows` property).

- [ ] **Step 2: Open dashboard in browser to visually verify**

Open the dashboard (either via HA add-on or locally) and verify:
- Hero stat shows the best quiet window with time range, duration, and confidence %
- Timeline visualization shows green segments for each day of week
- Hovering segments shows tooltip with details
- Hourly noise chart still renders correctly
- Heatmap still renders correctly
- Flights tab still works

- [ ] **Step 3: Verify with edge cases**

Check that the dashboard handles:
- Empty dataset (no CSV data) — should show "N/A" and "No data" gracefully
- Filtering to a day-type with no data — should show "No data" for all DOW rows

- [ ] **Step 4: Final commit if any cleanup was needed**

```bash
git add flight-tracker/static/dashboard.html
git commit -m "chore: clean up old hour-based quiet window references"
```
