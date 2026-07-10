// Module 5 — corridor bundle builder.
//
// Fetches EVERYTHING geographic from the real Tasco Maps APIs and writes a
// self-contained bundle to module5/cache/corridor_bundle.json that the demo
// server replays. Run once with network before the demo:
//
//   node module5/scripts/build_corridor.js            # cache-first
//   TASCO_CACHE=refresh node module5/scripts/build_corridor.js  # force live
//
// REAL (from Tasco production APIs): route geometry, distances, durations,
// toll-gate coordinates (geocoded from real plaza names), restaurant
// candidates + coordinates, detour math (baseline vs with-stop routing).
// MOCKED: only the toll-crossing trigger events fired by the UI clock.

'use strict';

const fs = require('fs');
const path = require('path');
const { TascoApiClient } = require('../lib/tasco_api');
const geo = require('../lib/geometry');
const engine = require('../lib/module1_engine');

const OUT = path.join(__dirname, '..', 'cache', 'corridor_bundle.json');

// Trip definition: Hà Nội (Hồ Hoàn Kiếm area) → Hạ Long (Bãi Cháy).
const ORIGIN = { lat: 21.0285, lon: 105.8542, label: 'Hà Nội (Hồ Hoàn Kiếm)' };
const DEST = { lat: 20.9509, lon: 107.0784, label: 'Hạ Long (Bãi Cháy)' };

// Real toll plaza names on the Hà Nội → Hải Phòng / Hạ Long corridor, to be
// geocoded via the real API. Only those that snap within MAX_GATE_OFFSET_M of
// the actual route polyline are kept (max 3, ordered by progress).
const TOLL_GATE_QUERIES = [
  'Trạm thu phí Quốc lộ 5',
  'Trạm thu phí số 1 Quốc lộ 5',
  'Trạm thu phí số 2 Quốc lộ 5',
  'Trạm thu phí Hà Nội Hải Phòng',
  'Trạm thu phí Bạch Đằng',
  'Trạm thu phí Đại Yên',
  'Trạm thu phí Tiên Cựu',
];
const MAX_GATE_OFFSET_M = 5000;
const MAX_GATES = 3;

// Trip context for the suggestion (spec 05 §2): family with kids, needs
// parking, quick stop. Fed into the Module 1 engine as a FilterSpec.
const TRIP_CONTEXT = {
  label: 'Gia đình có trẻ nhỏ, cần bãi đỗ xe, dừng nhanh',
  segments: ['Gia đình'],
  amenities: ['Bãi đỗ xe'],
  keywords_boost: ['ăn nhanh'],
};

// ---------------------------------------------------------------------------
// Candidate adaptation: PlaceResult (real API) → POI record for the engine.
// Fields the API cannot provide (rating, popularity) stay null — the engine
// substitutes documented neutral midpoints. Derived attributes carry their
// provenance so the UI/judges can see what is verified vs inferred.
// ---------------------------------------------------------------------------

const FAST_FOOD_RE = /kfc|lotteria|jollibee|mcdonald|burger|pizza|texas chicken/i;
const RESTAURANT_RE = /nhà hàng|restaurant|quán ăn|quán cơm|cơm|phở|bún|lẩu|gà|hải sản|beefsteak|nướng|trạm dừng|bánh mì|ăn uống/i;
const CAFE_RE = /caf[eé]|cà phê|coffee|kafe/i;
const EXCLUDE_RE = /chợ|siêu thị|big c|vinmart|winmart|bách hóa|nhà thờ|nhà văn hóa|trường|market/i;

function classify(place) {
  const name = place.name || '';
  if (EXCLUDE_RE.test(name)) return null;
  if (FAST_FOOD_RE.test(name) || place.tags.includes('food:burger')) return 'fast_food';
  if (RESTAURANT_RE.test(name)) return 'restaurant';
  if (CAFE_RE.test(name)) return 'cafe';
  return null; // unclassifiable food venue → skip (honesty over volume)
}

async function adaptCandidate(api, place, kind) {
  const segments = [];
  const amenities = [];
  const provenance = [];

  provenance.push({ field: 'coordinates,name', source: 'tasco-nearby-search', verified: true });

  if (kind === 'fast_food') {
    segments.push('Gia đình', 'Ăn nhanh');
    provenance.push({ field: 'segments', source: 'chuỗi ăn nhanh (heuristic tên quán)', verified: false });
  } else if (kind === 'restaurant') {
    segments.push('Gia đình');
    provenance.push({ field: 'segments', source: 'loại hình nhà hàng/quán cơm (heuristic tên quán)', verified: false });
  }

  // Real parking check: OSM transport venues within 400 m via the real API.
  let parkingVerified = false;
  try {
    const near = await api.nearbySearch({
      lat: place.coordinates.lat,
      lon: place.coordinates.lon,
      radiusMeters: 400,
      category: 'parking',
      limit: 3,
    });
    parkingVerified = near.results.length > 0;
  } catch {
    parkingVerified = false;
  }
  if (parkingVerified) {
    amenities.push('Bãi đỗ xe');
    provenance.push({ field: 'Bãi đỗ xe', source: 'OSM parking trong 400m (API nearby-search)', verified: true });
  } else if (kind !== 'cafe') {
    // Roadside restaurants / fast-food premises on national roads virtually
    // always have customer parking — inferred, and labeled as such.
    amenities.push('Bãi đỗ xe');
    provenance.push({ field: 'Bãi đỗ xe', source: 'suy luận từ loại hình quán ven quốc lộ (chưa xác minh)', verified: false });
  }

  return {
    id: place.id,
    name: place.name,
    label: place.label,
    address: place.address,
    category: kind,
    coordinates: place.coordinates,
    rating: null, // not provided by API — engine uses neutral midpoint
    popularity_score: null,
    price_level: null,
    cuisine_type: null,
    recommended_segments: segments.join(', '),
    amenities_raw: amenities.join(', '),
    known_strengths: kind === 'fast_food' ? 'ăn nhanh, phục vụ nhanh' : '',
    provenance,
  };
}

// ---------------------------------------------------------------------------

async function main() {
  const api = new TascoApiClient();
  console.log('1) Baseline route Hà Nội → Hạ Long (real API)…');
  const baseline = (await api.route([ORIGIN, DEST])).routes[0];
  const polyline = baseline.geometry.coordinates.map(([lon, lat]) => ({ lat, lon }));
  const cum = geo.cumulativeDistances(polyline);
  const totalM = cum[cum.length - 1];
  console.log(
    `   ${polyline.length} pts, ${(baseline.summary.distanceMeters / 1000).toFixed(1)} km, ` +
      `${(baseline.summary.durationSeconds / 60).toFixed(0)} min`
  );

  console.log('2) Geocoding real toll plaza names + snapping to polyline…');
  const gates = [];
  for (const q of TOLL_GATE_QUERIES) {
    try {
      const res = await api.geocoding(q, { lat: 20.95, lon: 106.4, layers: 'venue', limit: 3 });
      for (const r of res.results) {
        const snap = geo.snapToPolyline(r.coordinates, polyline, cum);
        if (snap.offsetMeters <= MAX_GATE_OFFSET_M) {
          gates.push({
            query: q,
            name: r.name,
            label: r.label,
            id: r.id,
            coordinates: r.coordinates,
            snapped: snap.snapped,
            progressKm: +(snap.progressMeters / 1000).toFixed(1),
            offsetMeters: Math.round(snap.offsetMeters),
          });
          console.log(`   ✓ ${r.name} @ km ${(snap.progressMeters / 1000).toFixed(1)} (offset ${Math.round(snap.offsetMeters)} m)`);
        }
      }
    } catch (e) {
      console.log(`   ✗ geocode "${q}" failed: ${e.message}`);
    }
  }
  console.log('2b) Harvesting on-route plazas via reverse geocoding (every 400 m)…');
  // The reverse-geocoding API labels route points that sit ON a toll plaza —
  // these are the most honest gates (offset ≈ 0: the car literally drives
  // through them). Sampling is cheap: every call is disk-cached.
  for (let m = 0; m < totalM; m += 400) {
    const p = geo.pointAtProgress(polyline, cum, m);
    try {
      const rev = await api.reverseGeocoding(p.lat, p.lon);
      const hit = rev.results[0];
      if (hit && /thu phí|toll/i.test(hit.name)) {
        const snap = geo.snapToPolyline(hit.coordinates, polyline, cum);
        gates.push({
          query: 'reverse-geocoding sweep',
          name: hit.name,
          label: hit.label,
          id: hit.id,
          coordinates: hit.coordinates,
          snapped: snap.snapped,
          progressKm: +(snap.progressMeters / 1000).toFixed(1),
          offsetMeters: Math.round(snap.offsetMeters),
        });
        console.log(`   ✓ ${hit.name} @ km ${(snap.progressMeters / 1000).toFixed(1)} (offset ${Math.round(snap.offsetMeters)} m)`);
      }
    } catch {
      /* sweep is best-effort */
    }
  }

  // Dedupe by proximity (gates < 3 km apart along route = same plaza
  // cluster). Within a cluster keep the plaza CLOSEST to the driven route —
  // honesty: the marker should be the gate the car actually passes by.
  gates.sort((a, b) => a.progressKm - b.progressKm);
  const picked = [];
  for (const g of gates) {
    const near = picked.find((p) => Math.abs(p.progressKm - g.progressKm) <= 3);
    if (!near) picked.push(g);
    else if (g.offsetMeters < near.offsetMeters) picked[picked.indexOf(near)] = g;
  }
  // Prefer gates genuinely ON the driven route (offset ≤ 1.5 km); relax only
  // if that leaves fewer than 2. Cap at MAX_GATES, spaced first/middle/last.
  let pool = picked.filter((g) => g.offsetMeters <= 1500);
  if (pool.length < 2) pool = picked;
  let finalGates = pool;
  if (pool.length > MAX_GATES) {
    finalGates = [pool[0], pool[Math.floor(pool.length / 2)], pool[pool.length - 1]];
  }
  if (finalGates.length === 0) throw new Error('No toll gate geocoded within range of the route — inspect queries.');
  finalGates.forEach((g, i) => (g.gateId = `GATE_${i + 1}`));
  console.log(`   → ${finalGates.length} gates kept: ${finalGates.map((g) => `${g.name}@km${g.progressKm}`).join(', ')}`);

  console.log('3) Per gate: real nearby restaurants → Module 1 engine → real detours…');
  for (const gate of finalGates) {
    // Forward-window search (spec 05 §4 step 3: suggest stops AHEAD, window
    // [current, +40 km]). Start at the gate; if OSM food coverage is sparse
    // there (verified live on rural stretches), also probe points 10/20/30 km
    // further along the actual route polyline, merging deduped results.
    const seen = new Set();
    const places = [];
    const probes = [];
    const gateProgressM = gate.progressKm * 1000;
    for (const aheadKm of [0, 10, 20, 30]) {
      const prog = Math.min(gateProgressM + aheadKm * 1000, totalM - 500);
      const at = geo.pointAtProgress(polyline, cum, prog);
      const res = await api.nearbySearch({
        lat: at.lat,
        lon: at.lon,
        radiusMeters: 6000,
        category: 'restaurant',
        limit: 20,
      });
      probes.push({ aheadKm, found: res.results.length });
      for (const r of res.results) {
        if (!seen.has(r.id)) {
          seen.add(r.id);
          places.push(r);
        }
      }
      if (places.filter((p) => classify(p)).length >= 4) break;
    }
    gate.search = { radiusMeters: 6000, forwardProbes: probes };

    const candidates = [];
    for (const place of places) {
      const kind = classify(place);
      if (!kind) continue;
      const snap = geo.snapToPolyline(place.coordinates, polyline, cum);
      const progKm = snap.progressMeters / 1000;
      // Forward window per spec 05 §4: [gate, gate+40 km]. 5 km of slack
      // behind, because gates themselves can sit a few km off the polyline
      // (real plaza coordinates) — actual reachability is settled by the
      // with-stop detour routing, not by this narrative filter.
      if (progKm < gate.progressKm - 5 || progKm > gate.progressKm + 40) continue;
      const cand = await adaptCandidate(api, place, kind);
      cand.progressKm = +progKm.toFixed(1);
      cand.offRouteMeters = Math.round(snap.offsetMeters);
      candidates.push(cand);
    }

    // REUSE Module 1 engine (spec 01 §4) — no new ranker.
    const ranked = engine.filterAndRank(candidates, TRIP_CONTEXT);
    const top = ranked.slice(0, 3);

    // Real detour: baseline (origin→dest) vs with-stop (origin→stop→dest),
    // one 3-location route call per candidate. VERIFIED: the route API honors
    // the middle waypoint (returns 2 legs through it).
    for (const item of top) {
      try {
        const withStop = (await api.route([ORIGIN, item.poi.coordinates, DEST])).routes[0];
        item.detour = {
          method: 'origin→stop→dest (1 call, middle waypoint) minus origin→dest baseline',
          baselineMeters: baseline.summary.distanceMeters,
          baselineSeconds: baseline.summary.durationSeconds,
          withStopMeters: withStop.summary.distanceMeters,
          withStopSeconds: withStop.summary.durationSeconds,
          detourMeters: withStop.summary.distanceMeters - baseline.summary.distanceMeters,
          detourSeconds: withStop.summary.durationSeconds - baseline.summary.durationSeconds,
        };
      } catch (e) {
        console.log(`   ✗ detour route for ${item.poi.name} failed: ${e.message}`);
        item.detour = null;
      }
    }

    // Suggestion = best engine score among candidates with a computed detour,
    // preferring reasonable detours (< 15 min penalty threshold).
    const usable = top.filter((t) => t.detour);
    usable.sort((a, b) => {
      const pa = a.detour.detourSeconds > 900 ? 1 : 0;
      const pb = b.detour.detourSeconds > 900 ? 1 : 0;
      return pa - pb || b.score - a.score || a.detour.detourSeconds - b.detour.detourSeconds;
    });
    gate.suggestion = usable[0] || null;
    gate.alternatives = usable.slice(1);
    console.log(
      `   ${gate.gateId} ${gate.name}: ${candidates.length} candidates → top: ` +
        (gate.suggestion
          ? `${gate.suggestion.poi.name} (score ${gate.suggestion.score}, +${Math.round(
              gate.suggestion.detour.detourSeconds / 60
            )} min / +${(gate.suggestion.detour.detourMeters / 1000).toFixed(1)} km)`
          : 'NONE')
    );
  }

  console.log('4) Reverse-geocoding sample points along route (for moving-car label)…');
  const placeNames = [];
  const N = 12;
  for (let i = 0; i <= N; i++) {
    const prog = (totalM * i) / N;
    const p = geo.pointAtProgress(polyline, cum, prog);
    try {
      const rev = await api.reverseGeocoding(p.lat, p.lon);
      const best = rev.results[0];
      placeNames.push({ progressKm: +(prog / 1000).toFixed(1), name: best ? best.label : null });
    } catch {
      placeNames.push({ progressKm: +(prog / 1000).toFixed(1), name: null });
    }
  }

  // Thin the polyline for the UI (keep shape fidelity, cap point count).
  const step = Math.max(1, Math.floor(polyline.length / 1500));
  const uiPolyline = polyline.filter((_, i) => i % step === 0 || i === polyline.length - 1);

  const bundle = {
    generatedAt: new Date().toISOString(),
    corridor: {
      id: 'hanoi-halong',
      label: `${ORIGIN.label} → ${DEST.label}`,
      origin: ORIGIN,
      destination: DEST,
      totalKm: +(baseline.summary.distanceMeters / 1000).toFixed(1),
      totalMinutes: Math.round(baseline.summary.durationSeconds / 60),
      polyline: uiPolyline.map((p) => [+p.lat.toFixed(6), +p.lon.toFixed(6)]),
    },
    gates: finalGates,
    tripContext: TRIP_CONTEXT,
    placeNames,
    meta: {
      note:
        'Sự kiện qua trạm là TÍN HIỆU VETC MÔ PHỎNG (mock). Toàn bộ dữ liệu địa lý — tuyến đường, ' +
        'toạ độ trạm (geocode từ tên trạm thật), quán ăn, số liệu detour — lấy từ Tasco Maps API thật.',
      real: [
        'route geometry + distance/duration (POST /v1/route, Valhalla production)',
        'toll gate coordinates (GET /v1/geocoding trên tên trạm thu phí thật)',
        'restaurant candidates + coordinates (GET /v1/nearby-search, categories=food)',
        'detour numbers (baseline vs with-stop, cùng route API)',
        'place names along route (GET /v1/reverse-geocoding)',
      ],
      mocked: ['toll-crossing trigger events (thời điểm xe qua trạm do demo clock phát)'],
      engineReuse: 'Ranking dùng module5/lib/module1_engine.js — hiện thực spec 01 §4, không xây ranker mới.',
    },
  };

  fs.writeFileSync(OUT, JSON.stringify(bundle, null, 1));
  console.log(`\n✔ Bundle written: ${OUT}`);
}

main().catch((e) => {
  console.error('BUILD FAILED:', e.message);
  process.exit(1);
});
