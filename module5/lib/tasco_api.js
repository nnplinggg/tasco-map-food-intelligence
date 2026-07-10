// Module 5 — Tasco Maps API adapter.
//
// Exposes the normalized API surface documented in
// tasco_maps_hackathon_api_documentation.pdf (route / geocoding /
// nearby-search / reverse-geocoding) as a thin client over the REAL
// production services listed on page 1 of that doc:
//   - Route base   (Valhalla): https://tasco-maps.dnpwater.vn/route
//   - Geocode base (Pelias):   https://tasco-maps.dnpwater.vn/geocode
//
// Contract compliance (API doc p.2): base URLs and auth are configurable via
// env / constructor, never hardcoded in call sites; Bearer and X-API-Key are
// both supported.
//
// Reliability (live stage): every call is cache-first. Successful responses
// are written to module5/cache/ keyed by a hash of the request; on any
// network failure the adapter falls back to the cached copy, so a hiccup on
// stage replays real numbers captured earlier instead of crashing.

'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { decodePolyline } = require('./geometry');

const DEFAULTS = {
  routeBase: process.env.TASCO_ROUTE_BASE || 'https://tasco-maps.dnpwater.vn/route',
  geocodeBase: process.env.TASCO_GEOCODE_BASE || 'https://tasco-maps.dnpwater.vn/geocode',
  bearerToken: process.env.TASCO_BEARER_TOKEN || null,
  apiKey: process.env.TASCO_API_KEY || null,
  cacheDir: path.join(__dirname, '..', 'cache', 'api'),
  // 'prefer-cache' (demo default: replay if present) | 'refresh' (force live)
  cacheMode: process.env.TASCO_CACHE || 'prefer-cache',
  timeoutMs: 25000,
};

class TascoApiClient {
  constructor(opts = {}) {
    this.cfg = { ...DEFAULTS, ...opts };
    fs.mkdirSync(this.cfg.cacheDir, { recursive: true });
  }

  _headers() {
    const h = { 'Content-Type': 'application/json', 'X-Locale': 'vi-VN' };
    if (this.cfg.bearerToken) h.Authorization = `Bearer ${this.cfg.bearerToken}`;
    if (this.cfg.apiKey) h['X-API-Key'] = this.cfg.apiKey;
    return h;
  }

  _cachePath(key) {
    const hash = crypto.createHash('sha1').update(key).digest('hex').slice(0, 16);
    return path.join(this.cfg.cacheDir, `${hash}.json`);
  }

  _readCache(key) {
    try {
      const raw = fs.readFileSync(this._cachePath(key), 'utf8');
      return JSON.parse(raw).response;
    } catch {
      return null;
    }
  }

  _writeCache(key, response, label) {
    const doc = { label, key, cachedAt: new Date().toISOString(), response };
    fs.writeFileSync(this._cachePath(key), JSON.stringify(doc, null, 1));
  }

  // Cache-first fetch with graceful fallback. `label` is human-readable and
  // stored alongside the cache entry for auditability.
  async _fetchJson(label, url, init) {
    const key = `${init?.method || 'GET'} ${url} ${init?.body || ''}`;
    if (this.cfg.cacheMode !== 'refresh') {
      const cached = this._readCache(key);
      if (cached) return { data: cached, fromCache: true };
    }
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), this.cfg.timeoutMs);
      const res = await fetch(url, {
        ...init,
        headers: { ...this._headers(), ...(init?.headers || {}) },
        signal: ctrl.signal,
      });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`HTTP ${res.status} from ${label}`);
      const data = await res.json();
      this._writeCache(key, data, label);
      return { data, fromCache: false };
    } catch (err) {
      const cached = this._readCache(key); // even in refresh mode, stale beats crash
      if (cached) return { data: cached, fromCache: true, staleFallback: true };
      throw new Error(`${label} failed and no cache available: ${err.message}`);
    }
  }

  // POST /v1/route (normalized DTO of the API doc, p.10), served by the real
  // Valhalla instance at the production route base.
  // locations: [{lat, lon}, ...] — VERIFIED: the API accepts a middle
  // waypoint (3 locations) and routes through it, returning one leg per pair.
  async route(locations, opts = {}) {
    const body = {
      locations: locations.map((l) => ({ lat: l.lat, lon: l.lon })),
      costing: opts.mode === 'pedestrian' ? 'pedestrian' : opts.mode === 'bicycle' ? 'bicycle' : 'auto',
      directions_options: { units: 'kilometers', language: opts.language || 'vi-VN' },
    };
    const url = `${this.cfg.routeBase}/route`;
    const { data, fromCache } = await this._fetchJson('route', url, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    if (!data.trip) throw new Error(`route: unexpected payload: ${JSON.stringify(data).slice(0, 200)}`);
    const legs = data.trip.legs.map((leg) => ({
      distanceMeters: Math.round(leg.summary.length * 1000),
      durationSeconds: Math.round(leg.summary.time),
      coordinates: decodePolyline(leg.shape, 6).map((p) => [p.lon, p.lat]),
    }));
    return {
      routes: [
        {
          routeId: 'route:primary',
          summary: {
            distanceMeters: Math.round(data.trip.summary.length * 1000),
            durationSeconds: Math.round(data.trip.summary.time),
          },
          geometry: {
            type: 'LineString',
            coordinates: legs.flatMap((l, i) => (i === 0 ? l.coordinates : l.coordinates.slice(1))),
          },
          legs: legs.map(({ distanceMeters, durationSeconds }) => ({ distanceMeters, durationSeconds })),
        },
      ],
      meta: { mode: body.costing, fromCache },
    };
  }

  // GET /v1/geocoding (API doc p.9) — Pelias /v1/search under the hood.
  async geocoding(address, opts = {}) {
    const params = new URLSearchParams({ text: address, size: String(opts.limit || 5) });
    if (opts.lat != null && opts.lon != null) {
      params.set('focus.point.lat', String(opts.lat));
      params.set('focus.point.lon', String(opts.lon));
    }
    if (opts.layers) params.set('layers', opts.layers);
    const url = `${this.cfg.geocodeBase}/v1/search?${params}`;
    const { data, fromCache } = await this._fetchJson('geocoding', url, {});
    return { query: address, results: peliasToPlaceResults(data), meta: { fromCache } };
  }

  // GET /v1/nearby-search (API doc p.8) — Pelias /v1/nearby under the hood.
  // category 'restaurant' maps to the Pelias category filter 'food'
  // (verified live: returns real OSM food venues with distances).
  async nearbySearch({ lat, lon, radiusMeters = 3000, category, limit = 15 }) {
    const params = new URLSearchParams({
      'point.lat': String(lat),
      'point.lon': String(lon),
      'boundary.circle.radius': String(radiusMeters / 1000), // Pelias radius is km
      size: String(limit),
    });
    const categoryMap = { restaurant: 'food', cafe: 'food', parking: 'transport' };
    if (category) params.set('categories', categoryMap[category] || category);
    const url = `${this.cfg.geocodeBase}/v1/nearby?${params}`;
    const { data, fromCache } = await this._fetchJson('nearby-search', url, {});
    return {
      center: { lat, lon },
      results: peliasToPlaceResults(data),
      meta: { radiusMeters, limit, fromCache },
    };
  }

  // GET /v1/reverse-geocoding (API doc p.7) — Pelias /v1/reverse.
  async reverseGeocoding(lat, lon) {
    const params = new URLSearchParams({ 'point.lat': String(lat), 'point.lon': String(lon), size: '1' });
    const url = `${this.cfg.geocodeBase}/v1/reverse?${params}`;
    const { data, fromCache } = await this._fetchJson('reverse-geocoding', url, {});
    return { results: peliasToPlaceResults(data), meta: { fromCache } };
  }
}

// Map Pelias GeoJSON features to the PlaceResult DTO of the API doc (p.2).
function peliasToPlaceResults(geojson) {
  return (geojson.features || []).map((f) => {
    const p = f.properties || {};
    const [lon, lat] = f.geometry.coordinates;
    return {
      id: p.gid || p.id || `poi:${lon},${lat}`,
      type: p.layer === 'venue' ? 'poi' : p.layer || 'poi',
      name: p.name || p.label || '',
      label: p.label || p.name || '',
      address: p.label || '',
      category: Array.isArray(p.category) ? p.category.join(',') : p.category || '',
      coordinates: { lat, lon },
      distanceMeters: p.distance != null ? Math.round(p.distance * 1000) : null,
      score: p.confidence != null ? p.confidence : null,
      source: 'tasco-maps-production', // real service, not mock
      tags: Array.isArray(p.category) ? p.category : [],
    };
  });
}

module.exports = { TascoApiClient };
