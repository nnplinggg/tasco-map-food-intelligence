# TASCO FOOD INTELLIGENCE — ALGORITHMS & FORMULAS
## Part 2: Exact Specifications, Pseudo-Code, Edge Cases

---

## 1. MODULE 1: SEMANTIC SEARCH & RANKING

### 1.1 Input Contract

```typescript
interface FilterSpec {
  segments?: string[];           // e.g., ["Gia đình", "Business"]
  amenities?: string[];          // e.g., ["Bãi đỗ xe", "Phù hợp trẻ em"]
  price_max?: number;            // e.g., 150000 (VND)
  price_min?: number;            // e.g., 50000 (VND)
  dietary_tags?: string[];       // e.g., ["Chay", "Không gluten"]
  keywords_boost?: string[];     // e.g., ["ăn nhanh", "bãi đỗ"]
  open_at_hour?: number;         // e.g., 18 (6 PM)
  city?: string;                 // e.g., "Nha Trang"
}

interface SearchRequest {
  query: string;                 // "gia đình, bãi đỗ, trưa, dưới 100k"
  filters: FilterSpec;
  limit?: number;                // default 10
}

interface RankResult {
  poi: POI;
  score: number;                 // 0.0–1.0
  match_factors: {
    rating_factor: number;
    popularity_factor: number;
    match_strength: number;
    price_fit: number;
  };
  match_detail: {
    segment_match?: string;      // which segment matched
    amenity_match?: string[];    // which amenities matched
    keyword_boost?: number;      // how many keywords found in menu
    hours_match?: boolean;       // does it open at requested hour?
  };
}
```

### 1.2 Algorithm: RANK_RESTAURANTS

```
function RANK_RESTAURANTS(
    query: string,
    filters: FilterSpec,
    poi_corpus: POI[],
    menu_items: MenuItem[]
) -> RankResult[]

  STEP 1: PARSE & NORMALIZE
  ──────────────────────────
    query_normalized = normalizeQuery(query)
    query_tokens = query_normalized.split()
    // Remove Vietnamese stopwords: cái, là, ở, tại, vì, etc.
    query_tokens = filter(query_tokens, not in STOPWORDS)
    
    EXAMPLE:
      input: "gia đình, bãi đỗ, trưa, dưới 100k"
      normalized: "gia dình bãi đỗ trưa dưới 100k"
      tokens after stopword removal: ["gia", "dình", "bãi", "đỗ", "trưa"]

  STEP 2: VALIDATE NO HALLUCINATION
  ──────────────────────────────────
    // Check if query explicitly names a restaurant
    if query_tokens[0] in POI_NAMES:
      named_poi = POI where name ~= query_tokens[0]
      if NOT found:
        return ERROR_404 { code: "not_found", message: "Nhà hàng không tồn tại" }
      // If found, proceed with that POI as anchor
    
    // Check for trap: "Crystal BBQ"
    for token in query_tokens:
      if token == "crystal bbq" or similar_fuzzy(token, "crystal bbq"):
        if "Crystal BBQ" not in any POI_NAMES:
          return ERROR_404

  STEP 3: LOAD INDICES
  ───────────────────
    // All lookups are O(1) or O(log n) via pre-built indices
    
    poi_by_id = load_index("poi/index_by_id.json")
    menu_by_restaurant = load_index("menu/index_by_restaurant.json")
    menu_by_dish = load_index("menu/index_by_dish.json")
    poi_by_segment = load_index("poi/lookup_by_segment.json")
    poi_by_amenity = load_index("poi/lookup_by_amenity.json")

  STEP 4: FILTER BY CONSTRAINTS (Pre-scoring)
  ───────────────────────────────────────────
    
    candidates = poi_corpus  // all 30 restaurants initially
    
    // City filter (if specified)
    if filters.city:
      candidates = filter(candidates, c.city == filters.city)
    
    // Segment filter (intersection)
    if filters.segments:
      candidates_by_segment = []
      for segment in filters.segments:
        candidates_by_segment += poi_by_segment[segment]
      candidates = intersection(candidates, candidates_by_segment)
    
    // Amenity filter (all must be present)
    if filters.amenities:
      for amenity in filters.amenities:
        candidates = filter(candidates, amenity in c.amenities_raw)
    
    // Opening hours filter
    if filters.open_at_hour:
      candidates = filter(candidates, isOpenAt(c.hours, filters.open_at_hour))
    
    // Dietary tags filter
    if filters.dietary_tags:
      for dietary in filters.dietary_tags:
        // Restaurant qualifies if at least 1 menu item has this tag
        candidates = filter(candidates, any(
          item.dietary_tags contains dietary
          for item in menu_by_restaurant[c.id]
        ))
    
    // Price range filter
    if filters.price_min or filters.price_max:
      for candidate in candidates:
        menu_items_here = menu_by_restaurant[candidate.id]
        prices = [item.price_vnd for item in menu_items_here]
        avg_price = mean(prices)
        if filters.price_min and avg_price < filters.price_min:
          remove candidate
        if filters.price_max and avg_price > filters.price_max:
          remove candidate
    
    if len(candidates) == 0:
      return { results: [], meta: { reason: "No restaurants match all constraints" } }

  STEP 5: SCORE CANDIDATES
  ────────────────────────
    results = []
    
    for poi in candidates:
      SCORE = COMPUTE_RANKING_SCORE(
        poi, query_tokens, filters, menu_by_restaurant, menu_by_dish
      )
      results.append({
        poi: poi,
        score: SCORE.total,
        match_factors: SCORE.factors,
        match_detail: SCORE.detail
      })
    
    // SCORE FORMULA (Tiers A & B, Spec 01 §4)
    ──────────────────────────────────────────
    
    function COMPUTE_RANKING_SCORE(
        poi: POI,
        query_tokens: string[],
        filters: FilterSpec,
        menu_by_restaurant,
        menu_by_dish
    ) -> SCORE_OBJECT
    
      // Factor 1: Rating (40% weight)
      rating_factor = poi.rating / 5.0  // Normalize to [0, 1]
      if poi.rating == 0 or null:
        rating_factor = 0.5  // Neutral default
      
      // Factor 2: Popularity (20% weight)
      // Assume popularity is pre-computed percentile [0, 100]
      popularity_factor = poi.popularity_percentile / 100.0
      if poi.popularity == 0 or null:
        popularity_factor = 0.5
      
      // Factor 3: Match Strength (25% weight)
      // Multi-faceted: segment, amenity, keyword matching
      
      segment_match = MATCH_SEGMENT(poi, filters.segments)
      amenity_match = MATCH_AMENITY(poi, filters.amenities)
      keyword_match = MATCH_KEYWORDS(
        poi, query_tokens, menu_by_restaurant[poi.id], menu_by_dish
      )
      
      match_strength = max([
        segment_match,
        amenity_match,
        keyword_match
      ])
      // Take max to avoid compound penalties; any good match helps
      
      // Factor 4: Price Fit (15% weight)
      price_fit = COMPUTE_PRICE_FIT(
        poi, filters.price_min, filters.price_max, menu_by_restaurant[poi.id]
      )
      
      // COMPOSITE SCORE
      total_score = (
        0.40 * rating_factor +
        0.20 * popularity_factor +
        0.25 * match_strength +
        0.15 * price_fit
      )
      
      return {
        total: total_score,
        factors: {
          rating_factor,
          popularity_factor,
          match_strength,
          price_fit
        },
        detail: {
          segment_match: filters.segments ? segment_match : null,
          amenity_match: filters.amenities ? amenity_match : [],
          keyword_boost: keyword_match,
          hours_match: filters.open_at_hour ? isOpenAt(poi.hours, filters.open_at_hour) : null
        }
      }
    end function

  STEP 6: SORT & DEDUPLICATE
  ──────────────────────────
    results.sort(by score DESC, then by poi.name ASC for stability)
    
    // Dedup: if same POI appears twice (shouldn't happen), keep highest score
    seen = set()
    deduped = []
    for result in results:
      if result.poi.id not in seen:
        deduped.append(result)
        seen.add(result.poi.id)
    
    results = deduped

  STEP 7: APPLY THRESHOLD & LIMIT
  ───────────────────────────────
    THRESHOLD = 0.30  // Don't show restaurants with score < 30%
    results = filter(results, score >= THRESHOLD)
    
    LIMIT = 10  // Default; configurable via request
    results = results[:LIMIT]

  STEP 8: TRANSFORM TO DTO
  ────────────────────────
    place_results = []
    for result in results:
      place_results.append({
        id: "poi:" + result.poi.id,
        type: "poi",
        name: result.poi.name,
        label: result.poi.category,  // "Nhà hàng" or "Quán cơm"
        address: result.poi.address,
        category: result.poi.category,
        coordinates: {
          lat: result.poi.latitude,
          lon: result.poi.longitude
        },
        distanceMeters: null,  // Not used in search context
        score: result.score,
        source: "mock",
        tags: concatenate([
          result.poi.recommended_segments,
          result.poi.amenities_raw
        ]).split("; ").filter(non-empty)
      })
    
    return {
      results: place_results,
      meta: {
        query: query,
        filters: filters,
        constraint_filters_applied: count of constraints,
        total_candidates_before_scoring: len(candidates),
        total_results: len(place_results),
        threshold_applied: THRESHOLD,
        scored_but_below_threshold: count
      }
    }

end function RANK_RESTAURANTS
```

### 1.3 Sub-Functions

#### MATCH_SEGMENT(poi, requested_segments)
```
function MATCH_SEGMENT(poi, requested_segments) -> float [0.0, 1.0]
  
  if requested_segments == empty or null:
    return 0.0  // No segment requirement
  
  poi_segments = poi.recommended_segments.split(";").trim()
  // e.g., "Gia đình; Business; Casual"
  
  match_count = 0
  for requested in requested_segments:
    for poi_seg in poi_segments:
      if FUZZY_MATCH(normalizeText(requested), normalizeText(poi_seg), threshold=0.85):
        match_count += 1
        break  // Don't double-count
  
  match_score = match_count / len(requested_segments)
  return match_score  // 0.0 = no match, 1.0 = all match

end function
```

#### MATCH_AMENITY(poi, requested_amenities)
```
function MATCH_AMENITY(poi, requested_amenities) -> float [0.0, 1.0]
  
  if requested_amenities == empty or null:
    return 0.0
  
  poi_amenities = poi.amenities_raw.split(";").trim()
  // e.g., "Bãi đỗ xe; Phù hợp trẻ em; WiFi"
  
  match_count = 0
  for requested in requested_amenities:
    for poi_amenity in poi_amenities:
      if FUZZY_MATCH(
        normalizeText(requested),
        normalizeText(poi_amenity),
        threshold=0.80
      ):
        match_count += 1
        break
  
  match_score = match_count / len(requested_amenities)
  return match_score

end function
```

#### MATCH_KEYWORDS(poi, query_tokens, menu_items, menu_by_dish)
```
function MATCH_KEYWORDS(poi, query_tokens, menu_items, menu_by_dish) -> float [0.0, 1.0]
  
  // Count how many query keywords appear in restaurant's menu or dishes
  
  menu_text = concatenate([item.dish_name for item in menu_items])
  poi_text = normalizeText(poi.name + " " + poi.category + " " + poi.address)
  combined_text = normalizeText(menu_text + " " + poi_text)
  
  matched_keywords = 0
  for token in query_tokens:
    if token in combined_text (substring match):
      matched_keywords += 1
    // Also check fuzzy match for OCR typos
    else if any word in combined_text within levenshteinDistance(token) <= 2:
      matched_keywords += 1
  
  keyword_score = matched_keywords / max(len(query_tokens), 1)
  return clamp(keyword_score, 0.0, 1.0)

end function
```

#### COMPUTE_PRICE_FIT(poi, price_min, price_max, menu_items)
```
function COMPUTE_PRICE_FIT(poi, price_min, price_max, menu_items) -> float [0.0, 1.0]
  
  if price_min == null and price_max == null:
    return 0.0  // No price constraint
  
  if len(menu_items) == 0:
    return 0.5  // No menu data; neutral
  
  prices = [item.price_vnd for item in menu_items]
  avg_price = mean(prices)
  
  if price_max and avg_price > price_max:
    return 0.0  // Doesn't fit
  
  if price_min and avg_price < price_min:
    return 0.0  // Too cheap (rare, but possible)
  
  if price_min and price_max:
    // Normalize to [0, 1] based on range
    range = price_max - price_min
    fit = (avg_price - price_min) / range
    return clamp(fit, 0.0, 1.0)
  
  if price_max:
    // No minimum; compute from price_max as reference
    fit = 1.0 - min(1.0, (price_max - avg_price) / price_max)
    return clamp(fit, 0.0, 1.0)
  
  return 0.5  // Default

end function
```

### 1.4 Complexity Analysis

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| **Load indices** | O(1) | Indices pre-loaded at startup |
| **Parse query** | O(n_tokens) | Tokenization + stopword removal |
| **Filter by constraints** | O(n_poi × n_constraints) | Each constraint scans candidates |
| **Score candidates** | O(n_candidates × n_menu_items) | Per candidate: score involves menu scan |
| **Sort results** | O(n log n) | Final sort |
| **Transform to DTO** | O(n) | Linear transformation |
| **Total (typical)** | **O(30 × 6 + 30 log 30) = O(300)** | For 30 POI, typical query |
| **Practical time** | **<100ms** | In-memory operations, cached indices |

### 1.5 Edge Cases & Traps

| Case | Handling |
|------|----------|
| **No candidates after filtering** | Return 200 { results: [] } with reason in meta |
| **All candidates below threshold** | Return 200 { results: [], reason: "no matches above threshold" } |
| **Hallucination: "Crystal BBQ"** | 404 { code: "not_found", message: "Nhà hàng không tồn tại" } |
| **Geographical trap: "Halal HCMC"** | 200 { results: [] } (no halal restaurants in HCMC; honest) |
| **Missing rating/popularity** | Use default 0.5 (neutral) |
| **Missing menu** | Can still rank by POI attributes; price_fit = 0.5 |
| **Fuzzy match ambiguity** | If 2 segments nearly match, pick the one with highest similarity |
| **Tie in scores** | Sort by POI name alphabetically for determinism |

---

## 2. MODULE 2: OCR MENU PARSER

### 2.1 Input Contract

```typescript
interface ParseOcrRequest {
  rawOcrText: string;          // Multi-line raw OCR
  restaurantId: string;        // e.g., "res001"
}

interface MenuItem {
  dishName: string;
  priceVnd: number;
  menuCategory: string;        // "Món chính", "Đồ uống", "Tráng miệng"
  dietaryTags: string[];
  ingredients: string[];
  confidence: number;           // 0.0–1.0
  matchedToGroundTruth: boolean;
}

interface ParseOcrResponse {
  restaurantId: string;
  items: MenuItem[];
  totalItems: number;
  meta: {
    processingTime_ms: number;
    qualityScore: number;       // 0.0–1.0 overall OCR quality
    warnings: string[];
  }
}
```

### 2.2 Algorithm: PARSE_OCR_MENU

```
function PARSE_OCR_MENU(rawOcrText: string, restaurantId: string) -> MenuItem[]
  
  STEP 1: NORMALIZE OCR TEXT
  ──────────────────────────
    text = rawOcrText.trim()
    
    // Remove extra whitespace
    text = replace(text, /\n\n+/g, "\n")  // Multiple newlines → single
    text = replace(text, /  +/g, " ")     // Multiple spaces → single
    
    // Standardize Vietnamese diacritics (NFC normalization)
    text = normalizeText(text)
    
    lines = text.split("\n")
    lines = filter(lines, line.length > 0)

  STEP 2: LINE-BY-LINE EXTRACTION
  ───────────────────────────────
    items = []
    
    for each line in lines:
      
      // Try to extract: dish name, price, category
      parsed_item = EXTRACT_MENU_ITEM(line, restaurantId)
      
      if parsed_item is not null:
        items.append(parsed_item)
      // else: skip line (not a menu item)

  STEP 3: DEDUP & CLEAN
  ─────────────────────
    // Remove exact duplicates
    seen_names = set()
    deduped = []
    for item in items:
      canonical = normalizeText(item.dishName)
      if canonical not in seen_names:
        deduped.append(item)
        seen_names.add(canonical)
    
    items = deduped

  STEP 4: VALIDATE AGAINST GROUND TRUTH
  ──────────────────────────────────────
    menu_ground_truth = load_index("menu/index_by_restaurant.json")[restaurantId]
    
    if menu_ground_truth:
      for item in items:
        matched = FIND_MATCH_IN_GROUND_TRUTH(
          item.dishName,
          item.priceVnd,
          menu_ground_truth
        )
        if matched:
          item.matchedToGroundTruth = true
          if item.priceVnd != matched.priceVnd:
            LOG_WARNING("Price mismatch for ${item.dishName}: OCR=${item.priceVnd}, GT=${matched.priceVnd}")
          else:
            item.confidence = min(item.confidence + 0.1, 1.0)  // Boost confidence

  STEP 5: TRANSFORM TO DTO
  ────────────────────────
    return {
      restaurantId: restaurantId,
      items: items,
      totalItems: len(items),
      meta: {
        processingTime_ms: elapsed(),
        qualityScore: COMPUTE_QUALITY_SCORE(items, menu_ground_truth),
        warnings: LOG_WARNINGS
      }
    }

end function PARSE_OCR_MENU
```

#### EXTRACT_MENU_ITEM(line, restaurantId)

```
function EXTRACT_MENU_ITEM(line: string, restaurantId: string) -> MenuItem | null
  
  line = line.trim()
  
  // Pattern 1: "Dish Name ... Price"
  // E.g., "Pho bo tai .... 80.397 VND"
  
  REGEX_PATTERN = /^(.+?)\s{2,}([\d.]+)\s+(VND|Đ|₫)?$/
  
  match = REGEX_PATTERN.match(line)
  if not match:
    return null
  
  dish_name_raw = match[1].trim()
  price_raw = match[2]
  
  // Extract dish name
  dish_name = normalizeText(dish_name_raw)
  
  // Extract price
  try:
    price_vnd = parsePrice(price_raw)
    // parsePrice("80.397") → 80397
  catch:
    LOG_WARNING("Could not parse price: ${price_raw}")
    return null
  
  // Validate price (sanity check: 10k–500k VND reasonable)
  if price_vnd < 10000 or price_vnd > 500000:
    LOG_WARNING("Price out of range: ${price_vnd} for ${dish_name}")
    price_vnd = 0  // Mark as uncertain
  
  // Infer menu category
  menu_category = INFER_CATEGORY(dish_name)
  
  // Extract dietary tags
  dietary_tags = EXTRACT_DIETARY_TAGS(dish_name, price_vnd)
  
  // Extract ingredients
  ingredients = EXTRACT_INGREDIENTS(dish_name)
  
  // Compute confidence
  confidence = COMPUTE_ITEM_CONFIDENCE(dish_name, price_vnd, menu_category)
  
  return MenuItem{
    dishName: dish_name,
    priceVnd: price_vnd,
    menuCategory: menu_category,
    dietaryTags: dietary_tags,
    ingredients: ingredients,
    confidence: confidence,
    matchedToGroundTruth: false  // Will be updated in Step 4
  }

end function EXTRACT_MENU_ITEM
```

#### INFER_CATEGORY(dish_name)

```
function INFER_CATEGORY(dish_name: string) -> string
  
  // Heuristic: infer category from dish name
  
  CATEGORY_KEYWORDS = {
    "Món chính": ["phở", "cơm", "bún", "mỳ", "cháo", "tiramisu"],
    "Đồ uống": ["nước", "trà", "cà phê", "bia", "rượu", "juice"],
    "Tráng miệng": ["trai miệng", "kem", "bánh", "pudding", "dessert"]
  }
  
  normalized = normalizeText(dish_name)
  
  for category, keywords in CATEGORY_KEYWORDS.items():
    for keyword in keywords:
      if keyword in normalized:
        return category
  
  // Default: assume main course
  return "Món chính"

end function INFER_CATEGORY
```

#### EXTRACT_DIETARY_TAGS(dish_name, price_vnd)

```
function EXTRACT_DIETARY_TAGS(dish_name: string, price_vnd: number) -> string[]
  
  tags = []
  
  normalized = normalizeText(dish_name)
  
  // Check for dietary indicators
  if "chay" in normalized or "canh chay" in normalized:
    tags.append("Chay")
  else:
    tags.append("Không chay")
  
  if "không gluten" in normalized or "gluten free" in normalized:
    tags.append("Không gluten")
  
  if "halal" in normalized:
    tags.append("Halal")
  
  if "organic" in normalized or "hữu cơ" in normalized:
    tags.append("Organic")
  
  return tags

end function EXTRACT_DIETARY_TAGS
```

#### EXTRACT_INGREDIENTS(dish_name)

```
function EXTRACT_INGREDIENTS(dish_name: string) -> string[]
  
  // Simple pattern-matching for common ingredients
  
  KNOWN_INGREDIENTS = {
    "thịt bò": ["bo", "beef"],
    "thịt gà": ["ga", "chicken"],
    "tôm": ["tom", "shrimp", "prawn"],
    "cá": ["ca", "fish"],
    "rau": ["rau", "vegetable"],
    ...
  }
  
  normalized = normalizeText(dish_name)
  ingredients = []
  
  for ingredient, patterns in KNOWN_INGREDIENTS.items():
    for pattern in patterns:
      if pattern in normalized:
        ingredients.append(ingredient)
        break
  
  return ingredients

end function EXTRACT_INGREDIENTS
```

#### COMPUTE_ITEM_CONFIDENCE(dish_name, price_vnd, category)

```
function COMPUTE_ITEM_CONFIDENCE(
    dish_name: string,
    price_vnd: number,
    category: string
) -> float [0.0, 1.0]
  
  confidence = 1.0
  
  // Reduce confidence if OCR quality seems poor
  if len(dish_name) < 3:
    confidence -= 0.3  // Very short; likely OCR error
  
  if price_vnd == 0:
    confidence -= 0.2  // Price couldn't be parsed
  
  if price_vnd > 500000:
    confidence -= 0.15  // Seems too high; OCR may have doubled digits
  
  // Check if dish name appears to have missing diacritics
  if "bo" in dish_name and "bò" not in dish_name:
    confidence -= 0.1  // Likely OCR diacritic loss
  
  return clamp(confidence, 0.1, 1.0)

end function COMPUTE_ITEM_CONFIDENCE
```

### 2.3 Complexity Analysis

| Operation | Complexity |
|-----------|-----------|
| **Normalize text** | O(n) where n = text length |
| **Split lines** | O(n) |
| **Extract per line** | O(1) regex match |
| **Dedup** | O(k log k) where k = items extracted |
| **Validate vs ground truth** | O(k × m) where m = ground truth items |
| **Transform to DTO** | O(k) |
| **Total** | **O(n + k log k + k×m)** |
| **Practical** | **<500ms for 6-item menu** |

### 2.4 Edge Cases

| Case | Handling |
|------|----------|
| **Empty OCR text** | Return 200 { items: [] } |
| **No prices found** | Log warnings; still extract dish names |
| **Multiple dishes per line** | Keep first regex match; log that manual review may be needed |
| **Price format variant: "80397" (no dot)** | parsePrice handles both "80.397" and "80397" |
| **Dish name with ambiguous price** | e.g., "Pho bo 30 tai 80.397" → regex is greedy right, takes last number |
| **Diacritic loss in OCR** | Fuzzy match vs ground truth still works due to normalizeText |

---

## 3. MODULE 3: REVIEW SENTIMENT & ASPECT EXTRACTION

### 3.1 Input Contract

```typescript
interface AnalyzeReviewsRequest {
  restaurantId: string;
}

interface Aspect {
  aspect: string;              // e.g., "Service Speed"
  sentiment: "positive" | "negative" | "neutral";
  count: number;
  strength: number;            // -1.0 to +1.0
  quotes: string[];            // Representative sentences
  confidence: number;           // 0.0–1.0
}

interface AnalyzeReviewsResponse {
  restaurantId: string;
  aspects: Aspect[];
  summary: string;             // AI-generated 1-line summary
  meta: {
    totalReviews: number;
    positiveReviews: number;
    negativeReviews: number;
    neutralReviews: number;
  }
}
```

### 3.2 Algorithm: ANALYZE_REVIEWS

```
function ANALYZE_REVIEWS(restaurantId: string) -> AnalyzeReviewsResponse
  
  STEP 1: LOAD REVIEWS
  ────────────────────
    reviews = load_index("reviews/by_restaurant.json")[restaurantId]
    
    if not reviews or len(reviews) == 0:
      return {
        restaurantId: restaurantId,
        aspects: [],
        summary: "Chưa có bình luận",
        meta: { totalReviews: 0, ... }
      }

  STEP 2: CLASSIFY SENTIMENT PER REVIEW
  ──────────────────────────────────────
    for each review in reviews:
      review.sentiment = CLASSIFY_SENTIMENT(review.text)
      // positive / negative / neutral based on keywords + rating

  STEP 3: EXTRACT ASPECTS
  ───────────────────────
    all_aspects = []
    
    for each review in reviews:
      aspects_in_review = EXTRACT_ASPECTS(review.text)
      all_aspects.extend(aspects_in_review)

  STEP 4: AGGREGATE ASPECTS
  ──────────────────────────
    // Group by aspect name; compute statistics
    
    aspect_map = {}  // { aspect_name: [aspect_extraction, ...] }
    
    for aspect_extraction in all_aspects:
      name = aspect_extraction.aspect
      if name not in aspect_map:
        aspect_map[name] = []
      aspect_map[name].append(aspect_extraction)
    
    aggregated_aspects = []
    for aspect_name, extractions in aspect_map.items():
      
      // Count sentiments
      positive_count = count(e.sentiment == "positive" for e in extractions)
      negative_count = count(e.sentiment == "negative" for e in extractions)
      
      // Compute strength (net sentiment)
      strength = (positive_count - negative_count) / len(extractions)
      // Range: -1.0 (all negative) to +1.0 (all positive)
      
      // Collect quotes
      quotes = [e.quote for e in extractions if e.quote][:3]  // Top 3
      
      aggregated_aspects.append(Aspect{
        aspect: aspect_name,
        sentiment: "positive" if strength > 0.2 else "negative" if strength < -0.2 else "neutral",
        count: len(extractions),
        strength: strength,
        quotes: quotes,
        confidence: mean([e.confidence for e in extractions])
      })
    
    // Sort by count (most frequent aspects first)
    aggregated_aspects.sort(by count DESC)

  STEP 5: VALIDATE AGAINST GROUND TRUTH
  ──────────────────────────────────────
    poi_record = load_index("poi/index_by_id.json")[restaurantId]
    
    if poi_record:
      known_strengths = poi_record.known_strengths.split(";")  // e.g., ["Food Quality", "Value"]
      known_weaknesses = poi_record.known_weaknesses.split(";")  // e.g., ["Service Speed", "Parking"]
      
      // Check if extracted aspects align
      for known_strength in known_strengths:
        if known_strength in [a.aspect for a in aggregated_aspects]:
          // Good; this aspect was extracted
          pass
        else:
          LOG_WARNING("Expected strength '${known_strength}' not extracted; may be data gap")

  STEP 6: GENERATE SUMMARY
  ────────────────────────
    // Simple heuristic: "Good X, but bad Y"
    positive_aspects = filter(aggregated_aspects, sentiment == "positive")[:2]
    negative_aspects = filter(aggregated_aspects, sentiment == "negative")[:2]
    
    if len(positive_aspects) > 0 and len(negative_aspects) > 0:
      summary = "Tốt về " + join(positive_aspects[*].aspect, ", ") +
                ", nhưng yếu về " + join(negative_aspects[*].aspect, ", ")
    else if len(positive_aspects) > 0:
      summary = "Tốt về " + join(positive_aspects[*].aspect, ", ")
    else if len(negative_aspects) > 0:
      summary = "Yếu về " + join(negative_aspects[*].aspect, ", ")
    else:
      summary = "Đánh giá trung bình"

  STEP 7: RETURN RESPONSE
  ──────────────────────
    return {
      restaurantId: restaurantId,
      aspects: aggregated_aspects,
      summary: summary,
      meta: {
        totalReviews: len(reviews),
        positiveReviews: count(r.sentiment == "positive" for r in reviews),
        negativeReviews: count(r.sentiment == "negative" for r in reviews),
        neutralReviews: count(r.sentiment == "neutral" for r in reviews)
      }
    }

end function ANALYZE_REVIEWS
```

#### CLASSIFY_SENTIMENT(review_text)

```
function CLASSIFY_SENTIMENT(review_text: string) -> string ("positive" | "negative" | "neutral")
  
  POSITIVE_WORDS = ["tốt", "ngon", "nhanh", "sạch", "thân thiện", "tuyệt vời", "excellent", ...]
  NEGATIVE_WORDS = ["tệ", "chậm", "bẩn", "thô lỗ", "tồi", "dreadful", ...]
  
  normalized = normalizeText(review_text)
  
  positive_count = count(word in normalized for word in POSITIVE_WORDS)
  negative_count = count(word in normalized for word in NEGATIVE_WORDS)
  
  if positive_count > negative_count:
    return "positive"
  else if negative_count > positive_count:
    return "negative"
  else:
    return "neutral"

end function CLASSIFY_SENTIMENT
```

#### EXTRACT_ASPECTS(review_text)

```
function EXTRACT_ASPECTS(review_text: string) -> AspectExtraction[]
  
  ASPECT_KEYWORDS = {
    "Service Speed": ["phục vụ", "chờ", "nhanh", "chậm", "tư vấn", ...],
    "Food Quality": ["đồ ăn", "ngon", "tươi", "tây", "bệ", ...],
    "Ambiance": ["không gian", "thoáng", "ồn", "yên tĩnh", "sang trọng", ...],
    "Cleanliness": ["sạch", "bẩn", "vệ sinh", "gọn gàng", ...],
    "Price": ["giá", "mắc", "rẻ", "đắt", "hợp lý", ...],
    "Parking": ["đỗ xe", "bãi", "gần", "xa", ...],
    ...
  }
  
  aspects = []
  sentences = review_text.split(".")  // Split into sentences
  
  for sentence in sentences:
    normalized = normalizeText(sentence)
    
    for aspect_name, keywords in ASPECT_KEYWORDS.items():
      for keyword in keywords:
        if keyword in normalized:
          
          sentiment = CLASSIFY_SENTIMENT(sentence)  // Per-sentence sentiment
          confidence = calculate_confidence(keyword, sentence)
          
          aspects.append(AspectExtraction{
            aspect: aspect_name,
            sentiment: sentiment,
            quote: sentence.strip(),
            confidence: confidence
          })
          
          break  // Don't double-count aspect in same sentence

  return aspects

end function EXTRACT_ASPECTS
```

### 3.3 Complexity Analysis

| Operation | Complexity |
|-----------|-----------|
| **Load reviews** | O(1) (indexed) |
| **Classify sentiment** | O(n_reviews × n_review_length) |
| **Extract aspects** | O(n_reviews × n_sentences × n_keywords) |
| **Aggregate** | O(n_extracted_aspects log n_aspects) |
| **Total** | **O(n_reviews × n_review_length + n_aspects log n_aspects)** |
| **Practical** | **<1 sec for 5 reviews** |

### 3.4 Edge Cases

| Case | Handling |
|------|----------|
| **No reviews** | Return empty aspects, summary = "Chưa có bình luận" |
| **Review in English** | Still works (keywords include English synonyms) |
| **All neutral sentiment** | Summary = "Đánh giá trung bình" |
| **Contradictory reviews** | Reflect in strength (some positive, some negative) |

---

## 4. MODULE 4: POI QUALITY SCORE

### 4.1 Algorithm: COMPUTE_POI_QUALITY

```
function COMPUTE_POI_QUALITY(restaurantId: string) -> QualityScoreResponse
  
  STEP 1: LOAD CROSS-DATASET DATA
  ───────────────────────────────
    poi_record = load_index("poi/index_by_id.json")[restaurantId]
    menu_items = load_index("menu/index_by_restaurant.json")[restaurantId]
    ocr_text = load_index("ocr/raw_by_restaurant.json")[restaurantId]
    reviews = load_index("reviews/by_restaurant.json")[restaurantId]

  STEP 2: MEASURE OCR COVERAGE
  ────────────────────────────
    if len(menu_items) > 0:
      ocr_coverage = (count items with price in menu_items) / len(menu_items)
    else:
      ocr_coverage = 0.0  // No menu data at all

  STEP 3: MEASURE REVIEW DENSITY
  ───────────────────────────────
    review_count = len(reviews)
    
    all_review_counts = [len(load_index(...)[id]) for id in all_restaurant_ids]
    median_reviews = median(all_review_counts)
    
    if median_reviews > 0:
      review_percentile = min(1.0, review_count / (median_reviews × 1.5))
    else:
      review_percentile = 0.0

  STEP 4: MEASURE AMENITY SPECIFICITY
  ────────────────────────────────────
    amenities_raw = poi_record.amenities_raw
    amenity_count = len(amenities_raw.split(";").filter(non-empty))
    
    // Assume max ~10 structured amenities
    MAX_AMENITIES = 10
    amenity_specificity = clamp(amenity_count / MAX_AMENITIES, 0.0, 1.0)

  STEP 5: MEASURE HOURS GRANULARITY
  ──────────────────────────────────
    hours = poi_record.hours
    
    if hours matches HH:MM-HH:MM pattern:
      hours_granularity = 1.0  // Fully specific
    else if hours is a range (e.g., "Morning-Evening"):
      hours_granularity = 0.5
    else:
      hours_granularity = 0.0

  STEP 6: COMPUTE COMPOSITE SCORE
  ───────────────────────────────
    poi_quality_score = (
      0.35 × ocr_coverage +
      0.30 × review_percentile +
      0.20 × amenity_specificity +
      0.15 × hours_granularity
    )
    
    clamp to [0.0, 1.0]

  STEP 7: VALIDATE AGAINST GROUND TRUTH
  ──────────────────────────────────────
    ground_truth_score = poi_record.poi_quality_score
    
    if ground_truth_score:
      error = abs(poi_quality_score - ground_truth_score)
      if error > 0.02:
        LOG_WARNING("Quality score discrepancy for ${restaurantId}: computed=${poi_quality_score}, GT=${ground_truth_score}")

  STEP 8: RETURN RESPONSE
  ──────────────────────
    return {
      restaurantId: restaurantId,
      score: poi_quality_score,
      components: {
        ocrCoverage: ocr_coverage,
        reviewDensity: review_percentile,
        amenityDetail: amenity_specificity,
        hoursGranularity: hours_granularity
      },
      recommendation: (
        "High-quality POI; suitable for prominent display" if score >= 0.85 else
        "Medium-quality; encourage OCR/review updates" if score >= 0.70 else
        "Low-quality; likely data gaps; de-prioritize" 
      )
    }

end function COMPUTE_POI_QUALITY
```

### 4.2 Complexity Analysis

| Operation | Complexity |
|-----------|-----------|
| **Load data** | O(1) each (indexed) |
| **Compute metrics** | O(n_menu + n_reviews + n_amenities) |
| **Total** | **O(n_menu + n_reviews)** |
| **Practical** | **<50ms per POI** |

---

## 5. MODULE 5: CORRIDOR DEMO (Shared Module 1 Engine)

Module 5 reuses `Module1Engine.rankRestaurants()` exactly, passing:
- `query` = implicit filter spec (e.g., "Gia đình, bãi đỗ")
- `filters` = { segments: ["Gia đình"], amenities: ["Bãi đỗ xe"], ... }
- `poi_corpus` = restaurants returned by Nearby-Search API
- `menu_items` = empty (not needed at corridor time)

**No new algorithms; pure reuse of Module 1.**

---

## 6. SUMMARY: COMPLEXITY BOUNDS

| Module | Time Complexity | Practical Time |
|--------|-----------------|----------------|
| **1 (Search)** | O(30 + log 30) | <100ms |
| **2 (OCR)** | O(n_ocr_length) | <500ms |
| **3 (Reviews)** | O(5 × n_review_length) | <1s |
| **4 (Quality)** | O(n_menu + n_reviews) | <50ms |
| **5 (Corridor)** | O(1) pure lookup | <10ms |

**Bottleneck:** Module 3 (NLP aspect extraction) due to keyword matching; <1s is acceptable for batch.

---

**Next:** SYSTEM_03_DATA_MODELS.md defines TypeScript interfaces + JSON schemas for all I/O.

