'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const A = require('../static/analytics.js');

const f = (date, time, alt = 5000, dist = 0.5) => ({ date, time_local: time, altitude_ft: String(alt), distance_from_home_km: String(dist) });
// coverage.csv rows marking the given hours (default: all 24) of a date as fully observed
const covRows = (date, hours = [...Array(24).keys()]) => hours.map(h => ({ date, hour: String(h), seconds: '3600' }));

test('timeToMin parses HH:MM:SS and HH:MM', () => {
    assert.equal(A.timeToMin('07:30:15'), 450);
    assert.equal(A.timeToMin('22:05'), 1325);
});

test('heuristic coverage: early first flight extends to midnight, late last flight to end of day', () => {
    const times = ['06:44:00', '08:10:00', '10:00:00', '12:30:00', '15:00:00', '17:45:00', '20:00:00', '23:08:00'];
    const cov = A.buildCoverage(times.map(t => f('2026-05-05', t)), []);
    assert.deepEqual(cov['2026-05-05'].intervals, [[0, 1440]]);
    assert.equal(cov['2026-05-05'].source, 'heuristic');
});

test('heuristic coverage: late start and early end shrink the observed interval', () => {
    const cov = A.buildCoverage([f('2026-05-06', '12:22:00'), f('2026-05-06', '16:00:00')], []);
    assert.deepEqual(cov['2026-05-06'].intervals, [[742, 960]]);
});

test('heuristic coverage: gap over 4h splits into two intervals', () => {
    const times = ['06:52:00', '07:00:00', '16:00:00', '18:00:00', '20:30:00', '23:06:00'];
    const cov = A.buildCoverage(times.map(t => f('2026-05-21', t)), []);
    assert.deepEqual(cov['2026-05-21'].intervals, [[0, 420], [960, 1440]]);
});

test('coverage.csv rows override heuristic; hour observed when >= 30 min polled', () => {
    const rows = [
        { date: '2026-09-10', hour: '6', seconds: '3600' },
        { date: '2026-09-10', hour: '7', seconds: '3600' },
        { date: '2026-09-10', hour: '8', seconds: '600' },   // too short
        { date: '2026-09-10', hour: '9', seconds: '1800' },
    ];
    const cov = A.buildCoverage([f('2026-09-10', '08:30:00')], rows);
    assert.equal(cov['2026-09-10'].source, 'coverage');
    assert.deepEqual(cov['2026-09-10'].intervals, [[360, 480], [540, 600]]);
});

test('coverage.csv day with zero flights is still a (quiet) observed day', () => {
    const rows = Array.from({ length: 24 }, (_, h) => ({ date: '2026-09-10', hour: String(h), seconds: '3600' }));
    const cov = A.buildCoverage([], rows);
    assert.deepEqual(cov['2026-09-10'].intervals, [[0, 1440]]);
});

test('isObserved requires the window to lie fully inside one interval', () => {
    const day = { intervals: [[0, 420], [960, 1440]] };
    assert.equal(A.isObserved(day, 360, 420), true);
    assert.equal(A.isObserved(day, 400, 430), false);
    assert.equal(A.isObserved(day, 1000, 1100), true);
});

test('hourObserved needs >= 30 min overlap', () => {
    const day = { intervals: [[742, 960]] };
    assert.equal(A.hourObserved(day, 12), true);  // 12:22-13:00 = 38 min
    assert.equal(A.hourObserved(day, 11), false);
    assert.equal(A.hourObserved(day, 13), true);
    assert.equal(A.hourObserved(day, 15), true);
    assert.equal(A.hourObserved(day, 16), false);
});

test('window quiet probability counts only observed days and zero-flight windows', () => {
    const flights = [
        f('2026-08-31', '09:30:00'),
        f('2026-09-07', '10:30:00'),
        f('2026-08-24', '11:00:00'),
        f('2026-08-17', '12:00:00'),
    ];
    // Three Mondays fully observed; a fourth only observed 12:00-16:00 must not count for 09:00
    const rows = [...covRows('2026-08-31'), ...covRows('2026-09-07'), ...covRows('2026-08-24'), ...covRows('2026-08-17', [12, 13, 14, 15])];
    const cov = A.buildCoverage(flights, rows);
    const stats = A.computeStats(flights, cov, { windowMin: 60, noiseExponent: 1.2 });
    const mon = stats.quiet.perDow[1];
    const slot = mon.slots.find(s => s.startMin === 540);
    assert.equal(slot.observed, 3);
    assert.equal(slot.quiet, 2);
    const slot13 = mon.slots.find(s => s.startMin === 780);
    assert.equal(slot13.observed, 4);
    assert.equal(slot13.quiet, 4);
});

test('best window prefers highest probability then most evidence, needs >= 3 days to be solid', () => {
    const flights = [];
    const rows = [];
    // 4 Tuesdays fully observed, a flight at 08:00 on three of them, nothing else
    for (const d of ['2026-08-11', '2026-08-18', '2026-08-25', '2026-09-01']) {
        rows.push(...covRows(d));
        if (d !== '2026-09-01') flights.push(f(d, '08:00:00'));
    }
    // A single Wednesday: totally quiet -> 100% but sparse
    rows.push(...covRows('2026-09-02'));
    const cov = A.buildCoverage(flights, rows);
    const stats = A.computeStats(flights, cov, { windowMin: 60, noiseExponent: 1.2 });
    assert.equal(stats.quiet.best.dow, 2, 'Tuesday wins over sparse Wednesday');
    assert.equal(stats.quiet.best.p, 1);
    assert.equal(stats.quiet.best.observed, 4);
    assert.equal(stats.quiet.perDow[3].best.sparse, true);
});

test('the giant-window bug is gone: a flight every 20 min never yields a quiet 60-min window', () => {
    const flights = [];
    for (const d of ['2026-09-06', '2026-09-13', '2026-09-20']) {
        for (let m = 0; m < 1440; m += 20) flights.push(f(d, A.formatMinutes(m) + ':00'));
    }
    const cov = A.buildCoverage(flights, []);
    const stats = A.computeStats(flights, cov, { windowMin: 60, noiseExponent: 1.2 });
    assert.equal(stats.quiet.best, null);
    assert.ok(stats.quiet.perDow[0].slots.every(s => s.quiet === 0));
});

test('hour averages are normalised by observed hour-days, not by day count', () => {
    const flights = [f('2026-09-01', '10:00:00'), f('2026-09-02', '13:20:00')];
    const rows = [...covRows('2026-09-01'), ...covRows('2026-09-02', [13])]; // second day observed 13:00-14:00 only
    const cov = A.buildCoverage(flights, rows);
    const stats = A.computeStats(flights, cov, { windowMin: 60, noiseExponent: 1.2 });
    assert.equal(stats.hourObservedDays[10], 1);
    assert.equal(stats.hourAvg[10], 1);
    assert.equal(stats.hourObservedDays[13], 2);
    assert.equal(stats.hourAvg[13], 0.5);
    assert.equal(stats.numDays, 2);
    assert.equal(stats.completeDays, 1);
});

test('dateMatches applies period and day-type filters', () => {
    const today = '2026-09-09';
    assert.equal(A.dateMatches('2026-09-01', '7', 'all', today), false);
    assert.equal(A.dateMatches('2026-09-03', '7', 'all', today), true);
    assert.equal(A.dateMatches('2026-09-06', 'all', 'weekend', today), true);
    assert.equal(A.dateMatches('2026-09-07', 'all', 'weekend', today), false);
    assert.equal(A.dateMatches('2026-09-07', 'all', 'weekday', today), true);
});

test('avg flights per day uses only fully tracked days', () => {
    const flights = [f('2026-09-01', '10:00:00'), f('2026-09-01', '12:00:00'), f('2026-09-02', '13:20:00')];
    const rows = [...covRows('2026-09-01'), ...covRows('2026-09-02', [13])];
    const stats = A.computeStats(flights, A.buildCoverage(flights, rows), { windowMin: 60, noiseExponent: 1.2 });
    assert.equal(stats.avgPerCompleteDay, 2);
});
