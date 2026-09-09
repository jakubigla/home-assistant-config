/* Flight tracker analytics — pure functions, no DOM.
 * Loaded by dashboard.html via <script> and by tests via require().
 */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.Analytics = factory();
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const DAY_START = 6 * 60;        // 06:00 — garden day
    const DAY_END = 22 * 60;         // 22:00
    const SLOT_MIN = 15;             // window start granularity
    const OFFLINE_GAP_MIN = 240;     // heuristic: >4h without a flight = add-on offline
    const EARLY_FIRST_MIN = 8 * 60;  // first flight before 08:00 -> assume observed from midnight
    const LATE_LAST_MIN = 21 * 60;   // last flight after 21:00 -> assume observed to midnight
    const MIN_OBSERVED_SEC = 1800;   // coverage.csv: hour counts if >= 30 min polled
    const MIN_HOUR_OVERLAP_MIN = 30; // heuristic: hour counts if >= 30 min inside an interval
    const MIN_DAYS = 3;              // fewer observed days = "limited data"

    function timeToMin(t) {
        const parts = String(t).split(':');
        return parseInt(parts[0], 10) * 60 + parseInt(parts[1] || '0', 10);
    }

    function formatMinutes(totalMin) {
        const h = Math.floor(totalMin / 60);
        const m = totalMin % 60;
        return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    }

    // 0 = Sunday, matching Date#getDay. Parse as UTC to avoid DST/timezone drift.
    function dowOf(date) {
        return new Date(date + 'T00:00:00Z').getUTCDay();
    }

    function dateMatches(date, period, dayType, today) {
        if (period !== 'all') {
            const cutoff = new Date((today || new Date().toISOString().slice(0, 10)) + 'T00:00:00Z');
            cutoff.setUTCDate(cutoff.getUTCDate() - parseInt(period, 10));
            if (date < cutoff.toISOString().slice(0, 10)) return false;
        }
        if (dayType !== 'all') {
            const dow = dowOf(date);
            const weekend = dow === 0 || dow === 6;
            if (dayType === 'weekend' ? !weekend : weekend) return false;
        }
        return true;
    }

    function noiseScore(alt, dist, exponent) {
        const a = parseFloat(alt);
        if (!a || a <= 0) return 0;
        const altScore = 1.0 / (a / 1000) ** exponent;
        const d = parseFloat(dist);
        const distFactor = (!d || d < 0) ? 1.0 : 1.0 / (1.0 + d);
        return altScore * distFactor;
    }

    function mergeIntervals(intervals) {
        const sorted = intervals.filter(([a, b]) => b > a).sort((x, y) => x[0] - y[0]);
        const out = [];
        for (const [a, b] of sorted) {
            const last = out[out.length - 1];
            if (last && a <= last[1]) last[1] = Math.max(last[1], b);
            else out.push([a, b]);
        }
        return out;
    }

    // Infer observed intervals for a day from its flight times alone (legacy data
    // recorded before coverage.csv existed).
    function heuristicIntervals(minutes) {
        const m = [...minutes].sort((a, b) => a - b);
        if (m.length === 0) return [];
        const start = m[0] <= EARLY_FIRST_MIN ? 0 : m[0];
        const end = m[m.length - 1] >= LATE_LAST_MIN ? 1440 : m[m.length - 1];
        const intervals = [];
        let segStart = start;
        for (let i = 1; i < m.length; i++) {
            if (m[i] - m[i - 1] > OFFLINE_GAP_MIN) {
                intervals.push([segStart, m[i - 1]]);
                segStart = m[i];
            }
        }
        intervals.push([segStart, end]);
        return mergeIntervals(intervals);
    }

    /**
     * Build per-date coverage: { date: { intervals: [[startMin, endMin], ...], source } }.
     * coverageRows come from coverage.csv ({date, hour, seconds}); dates missing there
     * fall back to the flight-derived heuristic.
     */
    function buildCoverage(flights, coverageRows) {
        const byDate = {};
        (coverageRows || []).forEach(r => {
            const secs = parseFloat(r.seconds);
            const hour = parseInt(r.hour, 10);
            if (!r.date || Number.isNaN(hour) || Number.isNaN(secs)) return;
            if (!byDate[r.date]) byDate[r.date] = { intervals: [], source: 'coverage' };
            if (secs >= MIN_OBSERVED_SEC) byDate[r.date].intervals.push([hour * 60, hour * 60 + 60]);
        });
        Object.values(byDate).forEach(d => { d.intervals = mergeIntervals(d.intervals); });

        const flightMins = {};
        flights.forEach(f => {
            if (!f.date || !f.time_local) return;
            (flightMins[f.date] = flightMins[f.date] || []).push(timeToMin(f.time_local));
        });
        Object.entries(flightMins).forEach(([date, mins]) => {
            if (byDate[date]) return;
            byDate[date] = { intervals: heuristicIntervals(mins), source: 'heuristic' };
        });
        return byDate;
    }

    function isObserved(day, startMin, endMin) {
        return !!day && day.intervals.some(([a, b]) => a <= startMin && endMin <= b);
    }

    function hourObserved(day, hour) {
        if (!day) return false;
        const hs = hour * 60, he = hs + 60;
        const overlap = day.intervals.reduce((acc, [a, b]) => acc + Math.max(0, Math.min(he, b) - Math.max(hs, a)), 0);
        return overlap >= MIN_HOUR_OVERLAP_MIN;
    }

    function computeStats(flights, coverage, opts) {
        const windowMin = (opts && opts.windowMin) || 60;
        const exponent = (opts && opts.noiseExponent) || 1.2;

        // The set of days under analysis = every day we observed (coverage keys),
        // so a fully quiet observed day still counts.
        const dates = Object.keys(coverage).sort();
        const datesPerDow = Array.from({ length: 7 }, () => []);
        dates.forEach(d => datesPerDow[dowOf(d)].push(d));

        const hourCounts = Array(24).fill(0);
        const hourNoise = Array(24).fill(0);
        const hourObservedDays = Array(24).fill(0);
        const dayHourCounts = Array.from({ length: 7 }, () => Array(24).fill(0));
        const dayHourNoise = Array.from({ length: 7 }, () => Array(24).fill(0));
        const dayHourObserved = Array.from({ length: 7 }, () => Array(24).fill(0));
        const routes = {};
        const flightMins = {};
        const completeDates = new Set();

        dates.forEach(d => {
            const dow = dowOf(d);
            for (let h = 0; h < 24; h++) {
                if (hourObserved(coverage[d], h)) { hourObservedDays[h]++; dayHourObserved[dow][h]++; }
            }
            if (isObserved(coverage[d], DAY_START, DAY_END)) completeDates.add(d);
        });
        const completeDays = completeDates.size;
        let flightsOnCompleteDays = 0;

        flights.forEach(f => {
            if (!f.date || !f.time_local) return;
            const min = timeToMin(f.time_local);
            (flightMins[f.date] = flightMins[f.date] || []).push(min);
            if (completeDates.has(f.date)) flightsOnCompleteDays++;
            const hour = Math.floor(min / 60);
            const dow = dowOf(f.date);
            const ns = noiseScore(f.altitude_ft, f.distance_from_home_km, exponent);
            hourCounts[hour]++;
            hourNoise[hour] += ns;
            dayHourCounts[dow][hour]++;
            dayHourNoise[dow][hour] += ns;
            const route = `${f.origin || '?'} -> ${f.destination || '?'}`;
            routes[route] = (routes[route] || 0) + 1;
        });

        const hourAvg = hourCounts.map((c, h) => hourObservedDays[h] ? c / hourObservedDays[h] : 0);
        const hourNoiseAvg = hourNoise.map((n, h) => hourObservedDays[h] ? n / hourObservedDays[h] : 0);
        const busiestHour = hourNoiseAvg.indexOf(Math.max(...hourNoiseAvg));
        const topRoutes = Object.entries(routes).sort((a, b) => b[1] - a[1]).slice(0, 5);

        // --- Quiet windows: P(zero flights in [t, t+W]) per weekday, observed days only ---
        const perDow = [];
        let best = null;
        for (let dow = 0; dow < 7; dow++) {
            const slots = [];
            for (let start = DAY_START; start + windowMin <= DAY_END; start += SLOT_MIN) {
                const end = start + windowMin;
                let observed = 0, quiet = 0;
                datesPerDow[dow].forEach(d => {
                    if (!isObserved(coverage[d], start, end)) return;
                    observed++;
                    const mins = flightMins[d] || [];
                    if (!mins.some(m => m >= start && m < end)) quiet++;
                });
                slots.push({ startMin: start, endMin: end, observed, quiet, p: observed ? quiet / observed : 0, sparse: observed < MIN_DAYS });
            }
            const candidates = slots.filter(s => s.observed > 0 && s.quiet > 0);
            const rank = (a, b) => (b.p - a.p) || (b.observed - a.observed) || (a.startMin - b.startMin);
            const solid = candidates.filter(s => !s.sparse).sort(rank)[0] || null;
            const dowBest = solid || candidates.sort(rank)[0] || null;
            perDow.push({ dow, numDays: datesPerDow[dow].length, slots, best: dowBest });
            if (dowBest && !dowBest.sparse && (!best || rank(dowBest, best) < 0)) best = { ...dowBest, dow };
        }
        if (!best) {
            const anyBest = perDow.map(p => p.best && { ...p.best, dow: p.dow }).filter(Boolean)
                .sort((a, b) => (b.p - a.p) || (b.observed - a.observed))[0];
            best = anyBest || null;
        }

        return {
            numDays: dates.length,
            completeDays,
            avgPerCompleteDay: completeDays ? flightsOnCompleteDays / completeDays : 0,
            totalFlights: flights.length,
            hourCounts, hourAvg, hourNoiseAvg, hourObservedDays,
            dayHourCounts, dayHourNoise, dayHourObserved,
            datesPerDow,
            busiestHour, topRoutes,
            quiet: { windowMin, perDow, best },
            DAY_START, DAY_END, SLOT_MIN, MIN_DAYS,
        };
    }

    return {
        DAY_START, DAY_END, SLOT_MIN, MIN_DAYS,
        timeToMin, formatMinutes, dowOf, dateMatches, noiseScore,
        buildCoverage, isObserved, hourObserved, computeStats,
    };
}));
