// Module 1 Filter & Rank engine — implementation of spec
// specs/01-semantic-search-spec.md §4 Tầng B (pure code, no LLM).
//
// NOTE ON REUSE: spec 05 mandates reusing Module 1's engine rather than
// building a new ranker. At the time Module 5 was built no Module 1 code
// existed yet in the repo, so this file implements spec 01 §4 verbatim
// (same normalization, same scoring formula, same weights) as a standalone
// dependency-free lib. The Module 1 dev should import THIS file for /v1/search
// so both modules share one engine — do not fork the formula.
//
// Scoring (spec 01 §4 step 5, weights are contract, do not change):
//   score = 0.40*(rating/5) + 0.20*(popularity_score/100)
//         + 0.25*match_strength + 0.15*price_fit

'use strict';

// NFC → lowercase → strip diacritics (đ→d). Matching only — display keeps accents.
function normalize(text) {
  return String(text || '')
    .normalize('NFC')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd');
}

function splitList(raw) {
  return String(raw || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

const PRICE_LEVELS = ['Bình dân', 'Trung bình', 'Cao cấp'];

// Neutral defaults when a data source lacks the field (e.g. Module 5's API
// candidates have no rating/popularity): documented midpoints, not zeros, so
// missing data neither sinks nor inflates a candidate.
const NEUTRAL_RATING = 3.5;
const NEUTRAL_POPULARITY = 50;

// poi shape (POI CSV column names, per spec 01 §2):
//   { rating, popularity_score, price_level, recommended_segments,
//     amenities_raw, known_strengths, ... }
// filterSpec (spec 01 §4 Tầng A output):
//   { segments: [], amenities: [], keywords_boost: [], price_level: null, ... }

function matchStrength(poi, spec) {
  const criteria = [];
  const segments = splitList(poi.recommended_segments).map(normalize);
  const amenities = splitList(poi.amenities_raw).map(normalize);
  const strengths = normalize(poi.known_strengths);

  for (const seg of spec.segments || []) {
    criteria.push(segments.includes(normalize(seg)));
  }
  for (const am of spec.amenities || []) {
    criteria.push(amenities.some((a) => a.includes(normalize(am))));
  }
  for (const kw of spec.keywords_boost || []) {
    const k = normalize(kw);
    criteria.push(strengths.includes(k) || amenities.some((a) => a.includes(k)));
  }
  if (criteria.length === 0) return 1; // no soft criteria → fully matched
  return criteria.filter(Boolean).length / criteria.length;
}

function priceFit(poi, spec) {
  if (!spec.price_level || !poi.price_level) return 1;
  const want = PRICE_LEVELS.indexOf(spec.price_level);
  const have = PRICE_LEVELS.indexOf(poi.price_level);
  if (want < 0 || have < 0) return 1;
  return Math.max(0, 1 - Math.abs(want - have) * 0.5); // 1 / 0.5 / 0 per step
}

function score(poi, spec) {
  const rating = poi.rating != null ? Number(poi.rating) : NEUTRAL_RATING;
  const pop = poi.popularity_score != null ? Number(poi.popularity_score) : NEUTRAL_POPULARITY;
  return (
    0.4 * (rating / 5) +
    0.2 * (pop / 100) +
    0.25 * matchStrength(poi, spec) +
    0.15 * priceFit(poi, spec)
  );
}

// Hard filters (subset relevant to Module 5's candidates; Module 1 adds
// city/menu filters on top per spec 01 §4 steps 3-4).
function passesHardFilters(poi, spec) {
  if (spec.cuisine_type && normalize(poi.cuisine_type) !== normalize(spec.cuisine_type)) return false;
  if (spec.min_rating != null && poi.rating != null && Number(poi.rating) < spec.min_rating) return false;
  return true;
}

// Main entry: filter + rank, descending score. Returns [{poi, score, matched}].
function filterAndRank(pois, spec) {
  return pois
    .filter((p) => passesHardFilters(p, spec))
    .map((p) => ({
      poi: p,
      score: Number(score(p, spec).toFixed(4)),
      matched: {
        segments: (spec.segments || []).filter((s) =>
          splitList(p.recommended_segments).map(normalize).includes(normalize(s))
        ),
        amenities: (spec.amenities || []).filter((a) =>
          splitList(p.amenities_raw).map(normalize).some((x) => x.includes(normalize(a)))
        ),
      },
    }))
    .sort((a, b) => b.score - a.score);
}

module.exports = { normalize, splitList, matchStrength, priceFit, score, filterAndRank };
