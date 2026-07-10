// Module 5 test suite — run: node module5/test/run_tests.js
// Covers spec 05 §6: geometry vs hand-computed answers, progress ordering,
// honesty check (meta.note), engine formula, and DATA ISOLATION (the
// most important check: module 5 must never touch the 30-restaurant
// benchmark datasets used by Modules 1-4).

'use strict';

const fs = require('fs');
const path = require('path');
const geo = require('../lib/geometry');
const engine = require('../lib/module1_engine');

let failures = 0;
function check(name, cond, detail = '') {
  console.log(`${cond ? '  ✓' : '  ✗ FAIL'} ${name}${cond ? '' : ' — ' + detail}`);
  if (!cond) failures++;
}
function approx(a, b, relTol) {
  return Math.abs(a - b) <= relTol * Math.abs(b);
}

// ── 1. geometry: point-to-segment, hand-computed (spec 05 §6, <1% error) ──
console.log('1) point-to-segment geometry');
{
  // E-W segment at lat 21: A→B spans 0.02° lon.
  const A = { lat: 21.0, lon: 105.0 };
  const B = { lat: 21.0, lon: 105.02 };
  // Perpendicular from mid-segment: 0.009° lat ≈ 0.009 × 111 195 m ≈ 1000.7 m
  const mid = geo.pointToSegment({ lat: 21.009, lon: 105.01 }, A, B);
  check('perpendicular mid-segment ≈ 1000.7 m', approx(mid.distanceMeters, 1000.7, 0.01), `got ${mid.distanceMeters.toFixed(1)}`);
  check('mid-segment t ≈ 0.5', approx(mid.t, 0.5, 0.01), `got ${mid.t}`);
  // Beyond A: must clamp to endpoint (the classic missing-clamp bug).
  const beforeA = geo.pointToSegment({ lat: 21.0, lon: 104.99 }, A, B);
  const expA = geo.haversineMeters({ lat: 21.0, lon: 104.99 }, A);
  check('beyond start clamps to A', approx(beforeA.distanceMeters, expA, 0.01) && beforeA.t === 0, `got ${beforeA.distanceMeters.toFixed(1)} t=${beforeA.t}`);
  // Beyond B: clamp to B.
  const afterB = geo.pointToSegment({ lat: 21.0, lon: 105.03 }, A, B);
  const expB = geo.haversineMeters({ lat: 21.0, lon: 105.03 }, B);
  check('beyond end clamps to B', approx(afterB.distanceMeters, expB, 0.01) && afterB.t === 1, `got ${afterB.distanceMeters.toFixed(1)} t=${afterB.t}`);
}

// ── 2. engine formula (spec 01 §4 step 5 weights) ──
console.log('2) Module 1 engine scoring');
{
  const spec = { segments: ['Gia đình'], amenities: ['Bãi đỗ xe'], keywords_boost: [] };
  const full = { rating: 4.5, popularity_score: 80, recommended_segments: 'Gia đình, Du lịch', amenities_raw: 'Bãi đỗ xe, Wifi', known_strengths: '' };
  // 0.40*0.9 + 0.20*0.8 + 0.25*1 + 0.15*1 = 0.92
  check('full match scores 0.92', engine.score(full, spec).toFixed(4) === '0.9200', `got ${engine.score(full, spec)}`);
  const bare = { rating: null, popularity_score: null, recommended_segments: '', amenities_raw: '', known_strengths: '' };
  // neutral midpoints: 0.40*0.7 + 0.20*0.5 + 0.25*0 + 0.15*1 = 0.53
  check('missing fields use neutral midpoints (0.53)', engine.score(bare, spec).toFixed(4) === '0.5300', `got ${engine.score(bare, spec)}`);
  check('diacritics-insensitive match', engine.normalize('Bãi Đỗ Xe') === 'bai do xe');
}

// ── 3. bundle sanity + honesty ──
console.log('3) corridor bundle honesty & ordering');
{
  const bundle = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'cache', 'corridor_bundle.json'), 'utf8'));
  check('meta.note present (bắt buộc, spec 05 §3)', typeof bundle.meta.note === 'string' && bundle.meta.note.includes('MÔ PHỎNG'));
  check('mocked list names ONLY the toll trigger', bundle.meta.mocked.length === 1 && /toll-crossing/.test(bundle.meta.mocked[0]));
  const progs = bundle.gates.map((g) => g.progressKm);
  check('gates ordered by progressKm', progs.every((p, i) => i === 0 || p > progs[i - 1]), progs.join(','));
  check('2-3 gates', bundle.gates.length >= 2 && bundle.gates.length <= 3, String(bundle.gates.length));
  for (const g of bundle.gates) {
    if (!g.suggestion) continue;
    const d = g.suggestion.detour;
    check(`${g.gateId} detour = withStop − baseline`, d.detourMeters === d.withStopMeters - d.baselineMeters && d.detourSeconds === d.withStopSeconds - d.baselineSeconds);
    check(`${g.gateId} suggestion is ahead of gate`, g.suggestion.poi.progressKm >= g.progressKm - 5);
  }
  const ui = fs.readFileSync(path.join(__dirname, '..', 'ui', 'index.html'), 'utf8');
  check('UI shows simulated-signal label', ui.includes('MÔ PHỎNG') && /SIMULATED/i.test(ui));
  check('UI shows privacy note (N ≥ 5, Nghị định 13/2023/NĐ-CP)', ui.includes('N ≥ 5') && ui.includes('13/2023/NĐ-CP'));
  check('UI shows detour computation note', ui.includes('baseline vs with-stop'));
}

// ── 4. DATA ISOLATION (spec 05 §4 step 1 — the critical invariant) ──
console.log('4) isolation from the 30-restaurant benchmark');
{
  const root = path.join(__dirname, '..');
  const sources = [];
  (function walk(dir) {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory() && e.name !== 'cache' && e.name !== 'node_modules') walk(p);
      else if (e.isFile() && /\.(js|html)$/.test(e.name)) sources.push(p);
    }
  })(root);
  const offenders = [];
  for (const f of sources) {
    const src = fs.readFileSync(f, 'utf8');
    const benchmarkName = 'ai_maps_track6' + '_dataset_participants'; // split so this file doesn't match itself
    if (src.includes(benchmarkName)) offenders.push(`${f}: references benchmark CSV`);
    if (/readFileSync\([^)]*\.csv/i.test(src)) offenders.push(`${f}: reads a CSV`);
  }
  check('no module5 source references the benchmark datasets', offenders.length === 0, offenders.join('; '));
  check('scanned a real set of sources', sources.length >= 5, `only ${sources.length}`);
  // NOTE: spec 05 §6 also requires re-running the Module 1/3/4 evals
  // byte-identical after adding Module 5. Those modules have no code in the
  // repo yet — re-run that check once they land. Module 5 shares only
  // lib/module1_engine.js with them and reads no benchmark data (proven above).
}

console.log(failures === 0 ? '\nALL TESTS PASSED' : `\n${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
