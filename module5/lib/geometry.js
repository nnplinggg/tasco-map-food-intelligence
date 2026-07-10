// Module 5 — pure geometry helpers (no I/O, no LLM).
// Unit-tested in test/run_tests.js (spec 05 §6: point-to-segment cases must be
// verified against hand-computed answers before integration).

'use strict';

const EARTH_RADIUS_M = 6371008.8;

function toRad(deg) {
  return (deg * Math.PI) / 180;
}

// Great-circle distance in meters between {lat, lon} points.
function haversineMeters(a, b) {
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lon - a.lon);
  const sinLat = Math.sin(dLat / 2);
  const sinLon = Math.sin(dLon / 2);
  const h =
    sinLat * sinLat +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * sinLon * sinLon;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

// Decode a Valhalla/Google encoded polyline. Valhalla uses precision 1e6.
// Returns [{lat, lon}, ...].
function decodePolyline(encoded, precision = 6) {
  const factor = Math.pow(10, precision);
  const coords = [];
  let index = 0;
  let lat = 0;
  let lon = 0;
  while (index < encoded.length) {
    for (const which of ['lat', 'lon']) {
      let result = 0;
      let shift = 0;
      let byte;
      do {
        byte = encoded.charCodeAt(index++) - 63;
        result |= (byte & 0x1f) << shift;
        shift += 5;
      } while (byte >= 0x20);
      const delta = result & 1 ? ~(result >> 1) : result >> 1;
      if (which === 'lat') lat += delta;
      else lon += delta;
    }
    coords.push({ lat: lat / factor, lon: lon / factor });
  }
  return coords;
}

// Equirectangular local projection around a reference latitude — accurate
// enough (<0.1% error) for point-to-segment work at corridor scale (<200 km).
function project(p, refLat) {
  const kx = Math.cos(toRad(refLat)) * EARTH_RADIUS_M;
  return { x: toRad(p.lon) * kx, y: toRad(p.lat) * EARTH_RADIUS_M };
}

// Distance from point p to segment [a, b], WITH clamping to the endpoints
// (spec 05 §7 flags the missing-clamp bug explicitly). Returns
// { distanceMeters, t } where t ∈ [0,1] is the position of the projection
// along the segment.
function pointToSegment(p, a, b) {
  const refLat = (a.lat + b.lat + p.lat) / 3;
  const P = project(p, refLat);
  const A = project(a, refLat);
  const B = project(b, refLat);
  const dx = B.x - A.x;
  const dy = B.y - A.y;
  const lenSq = dx * dx + dy * dy;
  let t = 0;
  if (lenSq > 0) {
    t = ((P.x - A.x) * dx + (P.y - A.y) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t)); // clamp to endpoints
  }
  const proj = { x: A.x + t * dx, y: A.y + t * dy };
  const ddx = P.x - proj.x;
  const ddy = P.y - proj.y;
  return { distanceMeters: Math.sqrt(ddx * ddx + ddy * ddy), t };
}

// Cumulative distance (meters) at each vertex of a polyline.
function cumulativeDistances(polyline) {
  const cum = [0];
  for (let i = 1; i < polyline.length; i++) {
    cum.push(cum[i - 1] + haversineMeters(polyline[i - 1], polyline[i]));
  }
  return cum;
}

// Snap a point onto a polyline. Returns
// { progressMeters, offsetMeters, segmentIndex, snapped: {lat, lon} }.
function snapToPolyline(point, polyline, cum) {
  if (!cum) cum = cumulativeDistances(polyline);
  let best = null;
  for (let i = 0; i < polyline.length - 1; i++) {
    const a = polyline[i];
    const b = polyline[i + 1];
    const r = pointToSegment(point, a, b);
    if (!best || r.distanceMeters < best.offsetMeters) {
      const segLen = cum[i + 1] - cum[i];
      best = {
        offsetMeters: r.distanceMeters,
        progressMeters: cum[i] + r.t * segLen,
        segmentIndex: i,
        snapped: {
          lat: a.lat + r.t * (b.lat - a.lat),
          lon: a.lon + r.t * (b.lon - a.lon),
        },
      };
    }
  }
  return best;
}

// Interpolate the position at a given progress (meters) along a polyline.
function pointAtProgress(polyline, cum, progressMeters) {
  if (progressMeters <= 0) return polyline[0];
  const total = cum[cum.length - 1];
  if (progressMeters >= total) return polyline[polyline.length - 1];
  // binary search for the segment containing progressMeters
  let lo = 0;
  let hi = cum.length - 1;
  while (lo + 1 < hi) {
    const mid = (lo + hi) >> 1;
    if (cum[mid] <= progressMeters) lo = mid;
    else hi = mid;
  }
  const segLen = cum[lo + 1] - cum[lo];
  const t = segLen > 0 ? (progressMeters - cum[lo]) / segLen : 0;
  const a = polyline[lo];
  const b = polyline[lo + 1];
  return { lat: a.lat + t * (b.lat - a.lat), lon: a.lon + t * (b.lon - a.lon) };
}

module.exports = {
  haversineMeters,
  decodePolyline,
  pointToSegment,
  cumulativeDistances,
  snapToPolyline,
  pointAtProgress,
};
