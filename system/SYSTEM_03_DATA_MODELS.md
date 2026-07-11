# TASCO FOOD INTELLIGENCE — DATA MODELS & CONTRACTS
## Part 3: TypeScript Interfaces, JSON Schemas, Database Formats

---

## 1. SHARED DOMAIN MODELS

### 1.1 POI (Point of Interest) — Restaurant Record

```typescript
// Source: "ai_maps_track6_dataset_participants.xlsm - Restaurant POI Dataset.csv"

interface POI {
  // Identifiers
  id: string;                           // e.g., "res001" (primary key)
  name: string;                         // e.g., "Phở Hàng Quân"
  
  // Location
  latitude: number;                     // WGS84
  longitude: number;                    // WGS84
  address: string;                      // Full address
  city: string;                         // e.g., "Hanoi", "HCMC"
  
  // Restaurant Info
  category: string;                     // e.g., "Nhà hàng", "Quán cơm"
  cuisine_type: string;                 // e.g., "Vietnamese", "Phở"
  
  // Quality Metrics
  rating: number;                       // 0.0–5.0 (from reviews or surveys)
  rating_count: number;                 // # of ratings
  popularity_percentile: number;        // 0–100 (precomputed ranking)
  poi_quality_score: number;            // 0.86–0.99 (ground truth from dataset)
  
  // Operating Hours
  hours: string;                        // e.g., "07:00-22:00" or "06:00-14:00"
  
  // Segments & Amenities
  recommended_segments: string;         // Semicolon-separated: "Gia đình; Business; Casual"
  amenities_raw: string;                // Semicolon-separated: "Bãi đỗ xe; Phù hợp trẻ em; WiFi"
  
  // Data Completeness (ground truth known_strengths/weaknesses)
  known_strengths: string;              // e.g., "Food Quality; Value"
  known_weaknesses: string;             // e.g., "Service Speed; Parking"
  
  // Pricing
  price_tier: number;                   // 1–5 (implicit from menu items)
  
  // Meta
  source: "mock" | "tasco-maps-production";
}

// Example
const poi_example: POI = {
  id: "res001",
  name: "Phở Hàng Quân",
  latitude: 21.0285,
  longitude: 105.8541,
  address: "123 Tran Hung Dao, Hanoi",
  city: "Hanoi",
  category: "Nhà hàng",
  cuisine_type: "Phở",
  rating: 4.5,
  rating_count: 120,
  popularity_percentile: 75,
  poi_quality_score: 0.92,
  hours: "07:00-22:00",
  recommended_segments: "Gia đình; Casual; Late Night",
  amenities_raw: "Bãi đỗ xe; Phù hợp trẻ em; WiFi; AC",
  known_strengths: "Food Quality; Authentic",
  known_weaknesses: "Service Speed",
  price_tier: 2,
  source: "mock"
};
```

### 1.2 MenuItem — Menu Item Record

```typescript
// Source: "ai_maps_track6_dataset_participants.xlsm - Menu Dataset.csv"

interface MenuItem {
  // Identifiers
  id: string;                           // e.g., "menu0001" (unique across all restaurants)
  restaurant_id: string;                // e.g., "res001" (foreign key)
  
  // Content
  dish_name: string;                    // e.g., "Phở Bò Tái"
  description?: string;                 // Optional longer description
  price_vnd: number;                    // Integer (cents)
  
  // Categorization
  menu_category: string;                // "Món chính" | "Đồ uống" | "Tráng miệng"
  
  // Tags
  dietary_tags: string[];               // ["Không chay", "Có gluten"]
  ingredients: string[];                // ["thịt bò", "nước dùng", "noodles"]
  cuisine_tags: string[];               // ["Vietnamese", "Authentic"]
  
  // Sourcing
  source: "menu_dataset" | "ocr_parsed";
  confidence?: number;                  // 0.0–1.0 (for OCR-parsed items)
  matched_to_ground_truth?: boolean;    // Whether OCR matched the menu dataset
}

// Example
const menu_example: MenuItem = {
  id: "menu0035",
  restaurant_id: "res001",
  dish_name: "Bún Chả",
  description: "Charred pork with noodles and fish sauce dip",
  price_vnd: 107640,
  menu_category: "Món chính",
  dietary_tags: ["Không chay"],
  ingredients: ["thịt heo", "noodles", "cá", "rau", "mắm cua"],
  cuisine_tags: ["Vietnamese", "Traditional"],
  source: "menu_dataset",
  matched_to_ground_truth: true
};
```

### 1.3 Review — Review Record

```typescript
// Source: "ai_maps_track6_dataset_participants.xlsm - Restaurant Reviews.csv"

interface Review {
  // Identifiers
  id: string;                           // e.g., "review0001"
  restaurant_id: string;                // e.g., "res001"
  
  // Content
  text: string;                         // Full review text in Vietnamese
  rating: number;                       // 1–5 stars (sometimes inferred from text)
  title?: string;                       // Short title
  
  // Metadata
  author?: string;                      // Optional author name (anonymized or omitted)
  timestamp?: string;                   // ISO 8601 date
  
  // Precomputed (for validation)
  sentiment_label?: "positive" | "negative" | "neutral";
  mentioned_aspects?: string[];         // Ground truth aspect keywords
}

// Example
const review_example: Review = {
  id: "review0001",
  restaurant_id: "res001",
  text: "Phở này ngon lắm, nước dùng thơm, nhưng chỗ đỗ xe hơi tội. Phục vụ cũng bình thường thôi.",
  rating: 4,
  title: "Đồ ăn tốt",
  author: "Anonymous",
  timestamp: "2026-06-15",
  sentiment_label: "positive",
  mentioned_aspects: ["Food Quality", "Parking", "Service Speed"]
};
```

---

## 2. REQUEST/RESPONSE DTOs (HTTP Contracts)

### 2.1 Module 1: Search

#### Request

```typescript
interface SearchRequest {
  query: string;                        // Free text query
  filters?: FilterSpec;                 // Optional structured filters
  limit?: number;                       // default: 10, max: 50
}

interface FilterSpec {
  segments?: string[];                  // e.g., ["Gia đình", "Business"]
  amenities?: string[];                 // e.g., ["Bãi đỗ xe"]
  price_max?: number;                   // VND
  price_min?: number;                   // VND
  dietary_tags?: string[];              // e.g., ["Chay"]
  keywords_boost?: string[];            // Additional keywords
  open_at_hour?: number;                // 0–23
  city?: string;                        // Filter by city
}

// HTTP: GET /v1/search?query=...&filters=...
```

#### Response (Success)

```typescript
interface SearchResponse {
  results: PlaceResult[];
  meta: {
    query: string;
    filters_applied: string[];          // Which filters were used
    total_results: number;
    threshold_applied: number;          // Minimum score cutoff
    constraint_filters_applied: number; // # of constraints
  }
}

interface PlaceResult {
  // DTO per API documentation
  id: string;                           // "poi:res001"
  type: "poi";
  name: string;
  label: string;                        // Category/type
  address: string;
  category: string;
  coordinates: {
    lat: number;
    lon: number;
  };
  distanceMeters: number | null;        // null for search context
  score: number;                        // 0.0–1.0 ranking score
  source: "mock" | "tasco-maps-production";
  tags: string[];                       // Segments + amenities
}

// Example
const search_response_example: SearchResponse = {
  results: [
    {
      id: "poi:res018",
      type: "poi",
      name: "Nhà Hàng Gia Đình Việt",
      label: "Nhà hàng",
      address: "456 Loc Tho, Nha Trang",
      category: "Nhà hàng",
      coordinates: { lat: 12.2567, lon: 109.1967 },
      distanceMeters: null,
      score: 0.91,
      source: "mock",
      tags: ["Gia đình", "Bãi đỗ xe", "Phù hợp trẻ em"]
    }
  ],
  meta: {
    query: "gia đình bãi đỗ trưa dưới 100k",
    filters_applied: ["segments", "amenities", "price_max"],
    total_results: 1,
    threshold_applied: 0.30,
    constraint_filters_applied: 3
  }
};
```

#### Response (Trap: Hallucination)

```typescript
interface ErrorResponse {
  error: {
    code: string;                       // "not_found" | "invalid_request" | "validation_error"
    message: string;                    // Human-readable (Vietnamese)
    details?: object;
  };
  requestId: string;                    // UUID
}

// Example: Crystal BBQ doesn't exist
{
  "error": {
    "code": "not_found",
    "message": "Nhà hàng không tồn tại",
    "details": { "query": "crystal bbq" }
  },
  "requestId": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 2.2 Module 2: OCR Parser

#### Request

```typescript
interface ParseOcrRequest {
  rawOcrText: string;                   // Multi-line raw OCR
  restaurantId: string;                 // e.g., "res001"
}

// HTTP: POST /v1/menu/parse
// Content-Type: application/json
```

#### Response

```typescript
interface ParseOcrResponse {
  restaurantId: string;
  items: StructuredMenuItem[];
  totalItems: number;
  meta: {
    processingTime_ms: number;
    qualityScore: number;               // 0.0–1.0
    warnings: string[];
  }
}

interface StructuredMenuItem {
  dishName: string;
  priceVnd: number;
  menuCategory: string;                 // "Món chính" | "Đồ uống" | "Tráng miệng"
  dietaryTags: string[];
  ingredients: string[];
  confidence: number;                   // 0.0–1.0
  matchedToGroundTruth: boolean;
}

// Example
const ocr_response_example: ParseOcrResponse = {
  restaurantId: "res001",
  items: [
    {
      dishName: "Phở Bò Tái",
      priceVnd: 80397,
      menuCategory: "Món chính",
      dietaryTags: ["Không chay"],
      ingredients: ["thịt bò", "nước dùng"],
      confidence: 0.95,
      matchedToGroundTruth: true
    }
  ],
  totalItems: 1,
  meta: {
    processingTime_ms: 234,
    qualityScore: 0.89,
    warnings: []
  }
};
```

### 2.3 Module 3: Review Analysis

#### Request

```typescript
interface AnalyzeReviewsRequest {
  restaurantId: string;
}

// HTTP: GET /v1/reviews/analyze?restaurantId=res001
```

#### Response

```typescript
interface AnalyzeReviewsResponse {
  restaurantId: string;
  aspects: Aspect[];
  summary: string;
  meta: {
    totalReviews: number;
    positiveReviews: number;
    negativeReviews: number;
    neutralReviews: number;
  }
}

interface Aspect {
  aspect: string;                       // e.g., "Service Speed"
  sentiment: "positive" | "negative" | "neutral";
  count: number;                        // # times mentioned
  strength: number;                     // -1.0 (all negative) to +1.0 (all positive)
  quotes: string[];                     // Representative sentences
  confidence: number;                   // 0.0–1.0
}

// Example
const review_response_example: AnalyzeReviewsResponse = {
  restaurantId: "res001",
  aspects: [
    {
      aspect: "Service Speed",
      sentiment: "negative",
      count: 3,
      strength: -0.67,
      quotes: ["Chờ đã 30 phút", "Phục vụ chậm lắm"],
      confidence: 0.85
    },
    {
      aspect: "Food Quality",
      sentiment: "positive",
      count: 5,
      strength: 0.80,
      quotes: ["Phở ngon lắm", "Đồ ăn tươi"],
      confidence: 0.92
    }
  ],
  summary: "Đồ ăn ngon nhưng phục vụ chậm",
  meta: {
    totalReviews: 5,
    positiveReviews: 3,
    negativeReviews: 2,
    neutralReviews: 0
  }
};
```

### 2.4 Module 4: POI Quality Score

#### Request

```typescript
interface ComputeQualityScoreRequest {
  restaurantId: string;
}

// HTTP: GET /v1/poi/quality-score?restaurantId=res001
```

#### Response

```typescript
interface ComputeQualityScoreResponse {
  restaurantId: string;
  score: number;                        // 0.0–1.0 (ground truth 0.86–0.99)
  components: {
    ocrCoverage: number;                // 0.0–1.0
    reviewDensity: number;              // 0.0–1.0 (percentile)
    amenityDetail: number;              // 0.0–1.0
    hoursGranularity: number;           // 0.0–1.0
  };
  recommendation: string;               // Narrative recommendation
}

// Example
{
  "restaurantId": "res001",
  "score": 0.92,
  "components": {
    "ocrCoverage": 0.89,
    "reviewDensity": 0.95,
    "amenityDetail": 0.88,
    "hoursGranularity": 1.0
  },
  "recommendation": "High-quality POI; suitable for prominent display"
}
```

### 2.5 Module 5: Corridor Demo

#### Request

```typescript
interface CorridorRestStopsRequest {
  corridorId: string;                   // e.g., "hanoi-halong"
  currentProgressKm: number;            // e.g., 80.5
  atHour?: number;                      // 0–23 (default: 12)
}

// HTTP: GET /v1/route/rest-stops?corridorId=hanoi-halong&currentProgressKm=80&atHour=12
```

#### Response

```typescript
interface CorridorRestStopsResponse {
  corridor: {
    id: string;
    label: string;
    totalKm: number;
  };
  currentProgressKm: number;
  push: boolean;                        // true during meal window; false = silent
  meal: string;                         // "sáng" | "trưa" | "tối" | "khuya" | "ngoài bữa"
  results: PlaceResult[];               // (empty if !push)
  meta: {
    note: string;                       // Privacy/simulation notice
    differentiator: string;             // Why this matters
    tripClockHour: number;              // Simulated hour
    suppressedOutsideMealWindow: boolean;
    nearestTollStation: string;         // Current toll station
    detourInfo: DetourInfo[];
  }
}

interface DetourInfo {
  poiId: string;
  detourMeters: number;                 // Extra distance
  extraMinutesEstimate: number;
  progressKm: number;                   // Restaurant position on route
}

// Example
{
  "corridor": { "id": "hanoi-halong", "label": "Hà Nội → Hạ Long", "totalKm": 158.5 },
  "currentProgressKm": 80,
  "push": true,
  "meal": "trưa",
  "results": [
    {
      "id": "poi:loc_nearby_001",
      "type": "poi",
      "name": "Quán Bánh Mì Cô Ba",
      "coordinates": { "lat": 21.15, "lon": 105.95 },
      "score": 0.84,
      "tags": ["Gia đình", "Bãi đỗ xe"]
    }
  ],
  "meta": {
    "differentiator": "route-aware (quán phía trước, detour thật) + structured amenities",
    "detourInfo": [
      { "poiId": "poi:loc_nearby_001", "detourMeters": 450, "extraMinutesEstimate": 3, "progressKm": 82 }
    ]
  }
}
```

---

## 3. INTERNAL DATA STRUCTURES (Indices & Caches)

### 3.1 POI Index (by_id)

```json
{
  "res001": { POI object... },
  "res002": { POI object... },
  ...
  "res030": { POI object... }
}
```

**File:** `data/POI/index_by_id.json`  
**Load time:** Startup (singleton, in-memory)  
**Access pattern:** O(1) by restaurant ID

### 3.2 POI Index (by_segment)

```json
{
  "Gia đình": ["res001", "res018", "res022", ...],
  "Business": ["res002", "res005", "res014", ...],
  "Casual": ["res001", "res003", "res006", ...],
  "Romantic": ["res007", "res009", ...],
  "Late Night": ["res010", "res011", ...]
}
```

**File:** `data/POI/lookup_by_segment.json`  
**Access pattern:** O(1) per segment, then O(n) to iterate POIs in segment

### 3.3 Menu Index (by_restaurant)

```json
{
  "res001": [
    { MenuItem object },
    { MenuItem object },
    ...
  ],
  "res002": [ ... ],
  ...
}
```

**File:** `data/Menu/index_by_restaurant.json`  
**Access pattern:** O(1) by restaurant, then O(n_items) to process

### 3.4 Menu Index (by_dish)

```json
{
  "pho bo tai": [
    { "restaurantId": "res001", "priceVnd": 80397, "confidence": 0.95 },
    { "restaurantId": "res003", "priceVnd": 85000, "confidence": 0.88 }
  ],
  "bun cha": [
    { "restaurantId": "res001", "priceVnd": 107640, "confidence": 0.92 },
    ...
  ]
}
```

**File:** `data/Menu/index_by_dish.json`  
**Access pattern:** O(1) per normalized dish name; useful for menu search

### 3.5 Review Index (by_restaurant)

```json
{
  "res001": [
    { Review object },
    { Review object },
    ...
  ],
  "res002": [ ... ]
}
```

**File:** `data/Reviews/by_restaurant.json`  
**Access pattern:** O(1) by restaurant, then O(n_reviews) to process

### 3.6 Module 5: Corridor Bundle

```typescript
interface CorridorBundle {
  corridor: {
    id: string;                         // "hanoi-halong"
    label: string;                      // "Hà Nội → Hạ Long"
    totalKm: number;                    // 158.5
    totalSeconds: number;               // 5589 (baseline)
  };
  gates: TollGate[];
  meta: {
    note: string;                       // Privacy statement
    cachedAt: string;                   // ISO 8601 timestamp
  }
}

interface TollGate {
  id: string;                           // "gate_001"
  name: string;                         // "Trạm QL10"
  progressKm: number;                   // Position on route
  coordinates: { lat: number, lon: number };
  
  suggestion: RankedRestaurant;         // Top recommendation
  alternatives: RankedRestaurant[];     // 2–3 more options
}

interface RankedRestaurant {
  poi: {
    id: string;
    name: string;
    address: string;
    coordinates: { lat: number, lon: number };
    progressKm: number;                 // Distance along route
    amenities_raw: string;
    recommended_segments: string;
  };
  score: number;                        // 0.0–1.0 (Module 1 ranking)
  detour?: {
    detourMeters: number;
    detourSeconds: number;
  };
}
```

**File:** `module5/cache/corridor_bundle.json`  
**Build process:** `node module5/scripts/build_corridor.js` calls production APIs once  
**Demo access:** Pure in-memory lookups (no API calls during demo)

---

## 4. DATABASE SCHEMA (CSV Import Format)

### 4.1 Restaurant POI Dataset

```
restaurant_id | name | latitude | longitude | address | city | category | cuisine_type | rating | rating_count | popularity_percentile | poi_quality_score | hours | recommended_segments | amenities_raw | known_strengths | known_weaknesses | price_tier | source
res001|Phở Hàng Quân|21.0285|105.8541|123 Tran Hung Dao|Hanoi|Nhà hàng|Phở|4.5|120|75|0.92|07:00-22:00|Gia đình;Casual;Late Night|Bãi đỗ xe;Phù hợp trẻ em;WiFi;AC|Food Quality;Authentic|Service Speed|2|mock
```

**# of records:** 30  
**# of columns:** 20  
**Nullability:** All columns filled (100% complete)

### 4.2 Menu Dataset

```
menu_id | restaurant_id | dish_name | description | price_vnd | menu_category | dietary_tags | ingredients | cuisine_tags | source
menu0001|res001|Phở Bò Tái|Rare beef pho|80397|Món chính|Không chay|thịt bò;nước dùng;noodles|Vietnamese;Traditional|menu_dataset
```

**# of records:** 179 (5–7 per restaurant)  
**Key validation:** price_vnd must match OCR exactly when both exist

### 4.3 OCR Menu Dataset

```
restaurant_id | raw_ocr_text
res001|Pho bo tai .... 80.397 VND
res001|Bun cha .... 107.640 VND
```

**# of records:** RES001–RES018 only (18 restaurants)  
**Note:** RES019–RES030 deliberately missing to test enrichment gaps

### 4.4 Restaurant Reviews

```
review_id | restaurant_id | text | rating | title | author | timestamp | sentiment_label | mentioned_aspects
review0001|res001|Phở này ngon lắm...|4|Đồ ăn tốt|Anon|2026-06-15|positive|Food Quality;Authentic
```

**# of records:** 150 (exactly 5 per restaurant)  
**Key validation:** sentiment_label pre-annotated (ground truth for NLP eval)

### 4.5 Public Evaluation

```
question_id | question | expected_answer_type | trap_flag | related_modules
eval_001|Find family restaurants with parking in Nha Trang under 100k|restaurant_list||1,2,3
eval_002|Does Crystal BBQ exist?|boolean|hallucination|1
eval_003|What halal restaurants are in HCMC?|restaurant_list|geographic_trap|1
```

**# of records:** 15  
**Key notes:** Traps explicitly marked; expected_answer_type guides eval harness

---

## 5. ERROR CODES & HTTP STATUS SUMMARY

### 5.1 Success Responses

| Status | Meaning |
|--------|---------|
| **200 OK** | Request succeeded (even if results empty) |
| **201 Created** | Resource created (unused in this API) |

### 5.2 Client Error Responses

| Status | Code | Example Message |
|--------|------|-----------------|
| **400 Bad Request** | `invalid_request` | "currentProgressKm phải là số" |
| **404 Not Found** | `not_found` | "Nhà hàng không tồn tại" or "Corridor không tồn tại" |
| **422 Unprocessable Entity** | `validation_error` | "Price format invalid" |

### 5.3 Server Error Responses

| Status | Code | Example Message |
|--------|------|-----------------|
| **500 Internal Server Error** | `internal_error` | Unexpected error (catch-all) |

### 5.4 Error Response Format (All)

```typescript
interface ErrorResponse {
  error: {
    code: string;                       // Machine-readable error type
    message: string;                    // Human-readable (Vietnamese)
    details?: Record<string, any>;
  };
  requestId: string;                    // UUID for debugging
}
```

---

## 6. VALIDATION RULES

### 6.1 Input Validation

| Field | Rule | Example |
|-------|------|---------|
| **restaurantId** | Must exist in POI index | "res001"–"res030" |
| **price_vnd** | Integer > 0, < 500,000 | 80397 |
| **latitude** | -90 to +90 | 21.0285 |
| **longitude** | -180 to +180 | 105.8541 |
| **rating** | 0.0 to 5.0 or null | 4.5 |
| **hours** | Pattern "HH:MM-HH:MM" | "07:00-22:00" |
| **query** | Non-empty string, < 500 chars | "gia đình bãi đỗ" |
| **atHour** | Integer 0–23 | 12 |
| **segments** | Must be in known vocabulary | "Gia đình", "Business" |

### 6.2 Hallucination Traps

| Trap | Expected Behavior | HTTP Status |
|------|------------------|-------------|
| **"Crystal BBQ"** | `not_found` error | 404 |
| **"Halal HCMC"** | Empty results (honest) | 200 { results: [] } |
| **Nonexistent corridor** | `not_found` error | 404 |

### 6.3 Data Integrity Checks

| Check | Criteria | Failure Action |
|-------|----------|-----------------|
| **OCR Price Match** | price_vnd from OCR == Menu Dataset | Log warning; still return parsed item |
| **Review Count** | Must be exactly 5 per restaurant | Log error if < 5; still process |
| **Menu Completeness** | All restaurants have 5–7 items | No action; precomputed |

---

**Next:** SYSTEM_04_TEST_PLAN.md defines unit tests, integration tests, and eval harness.

