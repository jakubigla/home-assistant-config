# Flight Analytics: Gap-Based Quiet Window Detection

## Problem

The current analytics page buckets flights into 1-hour slots and finds "quiet windows" as consecutive hours below median noise. This loses precision — a flight at 10:01 and next at 11:59 marks both hours 10 and 11 as busy, hiding ~2h of actual quiet time.

## Goal

Answer "when should I go outside?" by finding actual quiet gaps between flights, aggregated into typical patterns per day-of-week.

## Design

### Algorithm

1. **Per-date gap computation:** For each date in the dataset, sort flights by `time_local`. Compute gaps between consecutive flights within the daytime window (06:00–22:00), including the gap from 06:00 to the first flight and from the last flight to 22:00.

2. **Discretize to 15-minute slots:** Round flight times down to nearest 15-min boundary (10:01 → 10:00, 10:17 → 10:15). This gives useful precision without false exactness.

3. **Build quiet probability per slot:** Group dates by day-of-week. For each 15-min slot in the 06:00–22:00 range (64 slots), compute what fraction of days-of-that-type had no flights during that slot. E.g., "on Mondays, the 10:15–10:30 slot is flight-free 80% of the time."

4. **Determine quiet threshold from data:** A slot is "quiet" if it's flight-free on more than half the observed days for that day-of-week. If data is sparse (few days), use a higher bar to avoid false confidence.

5. **Merge consecutive quiet slots into windows:** Adjacent quiet slots form a single window. Record the window's average quiet probability (confidence).

6. **Dynamic minimum window length:** Compute the median gap duration across all observed gaps. Only display windows longer than this median — so the dashboard highlights *notably* quiet periods, not every routine pause between flights.

### Dashboard Changes

#### Remove
- Hour-based quiet window detection (`findQuietWindows` function)
- "Quietest window" hero stat (hour-based)

#### Modify
- **Hero stat:** Replace with best overall quiet window (longest window with highest quiet probability), showing time range and confidence percentage
- **"Quietest Garden Windows by Day" card:** Replace text-based hour ranges with a **timeline visualization** — horizontal bars for each day-of-week, 06:00–22:00 axis, quiet periods shown as green segments with opacity proportional to confidence. This makes patterns immediately visible.

#### Keep (unchanged)
- Noise by Hour chart (still useful as general context)
- Weekly Noise Heatmap
- Top Routes table
- Noisiest Time stat
- Worst Flights table
- All filters (period, day type, altitude exponent)
- Noise scoring formula
- Flights tab (entirely unchanged)

### Timeline Visualization Detail

Each day-of-week row is a horizontal bar spanning 06:00–22:00 (16 hours). The bar is divided into 15-min segments:
- **Quiet segments:** Filled green (`#4ade80`), opacity = quiet probability (0.5–1.0 mapped to 0.4–1.0 opacity)
- **Non-quiet segments:** Dark background (matching card bg)
- **Hour labels** along the top axis
- **Hovering** a quiet window shows: time range, duration, quiet probability %, avg flights during that slot

### Data Flow

```
CSV flights
  → filter by period/day-type (existing)
  → group by date, sort by time_local
  → compute per-date gaps (15-min resolution)
  → group dates by day-of-week
  → compute quiet probability per 15-min slot per DOW
  → derive threshold + merge into windows
  → render timeline + hero stat
```

### Edge Cases

- **Days with zero flights:** All daytime slots count as quiet for that day (which they are)
- **Days with one flight:** Two gaps — 06:00→flight and flight→22:00
- **Sparse data (<3 days for a DOW):** Show windows but with a "limited data" indicator
- **No quiet windows found:** Show "No consistent quiet periods detected"

## Scope

- Single file change: `flight-tracker/static/dashboard.html`
- Pure JavaScript — no backend changes needed
- All computation happens client-side on the existing CSV data
