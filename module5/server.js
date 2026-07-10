// Module 5 demo server — zero dependencies, replay-first.
//
//   node module5/server.js          → http://localhost:8790
//
// Serves the demo UI and two endpoints backed by the cached corridor bundle
// (built once from the real Tasco APIs by scripts/build_corridor.js):
//
//   GET /api/corridor                     full bundle for the demo UI
//   GET /v1/route/rest-stops?corridorId=hanoi-halong&currentProgressKm=55
//                                         spec 05 §3 contract response
//
// The server never calls the network during the demo — a stage hiccup cannot
// break it. Errors follow the API doc format { error: {...}, requestId }.

'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = process.env.MODULE5_PORT || 8790;
const BUNDLE_PATH = path.join(__dirname, 'cache', 'corridor_bundle.json');
const UI_PATH = path.join(__dirname, 'ui', 'index.html');

function loadBundle() {
  return JSON.parse(fs.readFileSync(BUNDLE_PATH, 'utf8'));
}

function sendJson(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(body);
}

function sendError(res, status, code, message, details = {}) {
  sendJson(res, status, {
    error: { code, message, details },
    requestId: crypto.randomUUID(),
  });
}

// PlaceResult DTO (API doc p.2) from a ranked candidate. Extension data goes
// in meta only — no invented fields at PlaceResult level.
function toPlaceResult(item) {
  const p = item.poi;
  return {
    id: p.id,
    type: 'poi',
    name: p.name,
    label: p.label,
    address: p.address,
    category: p.category,
    coordinates: p.coordinates,
    distanceMeters: null,
    score: item.score,
    source: 'tasco-maps-production',
    tags: [p.recommended_segments, p.amenities_raw].join(', ').split(', ').filter(Boolean),
  };
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  try {
    if (url.pathname === '/' || url.pathname === '/index.html') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(fs.readFileSync(UI_PATH));
      return;
    }

    if (url.pathname === '/api/corridor') {
      sendJson(res, 200, loadBundle());
      return;
    }

    if (url.pathname === '/v1/route/rest-stops') {
      const bundle = loadBundle();
      const corridorId = url.searchParams.get('corridorId');
      if (corridorId !== bundle.corridor.id) {
        sendError(res, 404, 'not_found', `corridor không tồn tại: ${corridorId}`, { corridorId });
        return;
      }
      const progress = parseFloat(url.searchParams.get('currentProgressKm') || '0');
      if (Number.isNaN(progress)) {
        sendError(res, 400, 'invalid_request', 'currentProgressKm phải là số', { field: 'currentProgressKm' });
        return;
      }
      // Suggestions from gates the car has passed, stops still ahead (≤ 40 km).
      const items = [];
      for (const gate of bundle.gates) {
        for (const s of [gate.suggestion, ...(gate.alternatives || [])]) {
          if (!s) continue;
          if (s.poi.progressKm >= progress && s.poi.progressKm <= progress + 40) {
            items.push({ gate, s });
          }
        }
      }
      items.sort((a, b) => a.s.poi.progressKm - b.s.poi.progressKm || b.s.score - a.s.score);
      sendJson(res, 200, {
        corridor: {
          id: bundle.corridor.id,
          label: bundle.corridor.label,
          totalKm: bundle.corridor.totalKm,
        },
        currentProgressKm: progress,
        results: items.map(({ s }) => toPlaceResult(s)),
        meta: {
          note: bundle.meta.note,
          nearestTollStation: (bundle.gates.filter((g) => g.progressKm <= progress).pop() || bundle.gates[0]).name,
          detourInfo: items.map(({ s }) => ({
            poiId: s.poi.id,
            detourMeters: s.detour ? s.detour.detourMeters : null,
            extraMinutesEstimate: s.detour ? Math.max(0, Math.round(s.detour.detourSeconds / 60)) : null,
            progressKm: s.poi.progressKm,
          })),
        },
      });
      return;
    }

    sendError(res, 404, 'not_found', `không có endpoint ${url.pathname}`);
  } catch (e) {
    sendError(res, 500, 'internal_error', e.message);
  }
});

server.listen(PORT, () => {
  console.log(`Module 5 demo: http://localhost:${PORT}`);
  console.log(`Contract endpoint: http://localhost:${PORT}/v1/route/rest-stops?corridorId=hanoi-halong&currentProgressKm=55`);
});
