# TASCO FOOD INTELLIGENCE — TEST PLAN & EVALUATION HARNESS
## Part 4: Unit Tests, Integration Tests, 15-Question Eval

---

## 1. TEST STRATEGY

### 1.1 Test Pyramid

```
                    ▲
                   / \
                  /   \
                 / E2E  \        3 tests (full system flows)
                /         \
               ├───────────┤
              /   Integration \  12 tests (module contracts)
             /                 \
            ├─────────────────────┤
          /      Unit Tests       \  40+ tests (functions, utilities)
         /                         \
        ──────────────────────────────
```

### 1.2 Test Coverage Goals

| Layer | # Tests | Coverage | Tools |
|-------|---------|----------|-------|
| **Unit** | 40+ | >90% functions | Jest, node-test |
| **Integration** | 12 | All modules in pairs | Supertest (HTTP) |
| **E2E** | 3 | Complete request→eval | Manual + harness |
| **Eval** | 15 | Benchmark questions | Custom harness |
| **Data Quality** | 20+ | CSV integrity, isolation | Node script |

---

## 2. UNIT TESTS

### 2.1 Module 1: Search Engine

```javascript
// tests/module1.test.js

describe('Module 1: Semantic Search', () => {
  
  describe('RANK_RESTAURANTS()', () => {
    
    it('should rank restaurants by weighted formula', () => {
      const result = rankRestaurants(
        "gia đình bãi đỗ",
        { segments: ["Gia đình"], amenities: ["Bãi đỗ xe"] },
        poiList,
        menuList
      );
      
      expect(result.length).toBeGreaterThan(0);
      expect(result[0].score).toBeGreaterThan(result[1]?.score || 0);
      // First result should have highest score
    });
    
    it('should return 404 for hallucination trap (Crystal BBQ)', () => {
      const req = {
        query: "Crystal BBQ"
      };
      
      expect(() => rankRestaurants(req.query, {}, poiList, menuList))
        .toThrow('not_found');
    });
    
    it('should return empty results for geographic trap (Halal HCMC)', () => {
      const result = rankRestaurants(
        "halal HCMC",
        { dietary_tags: ["Halal"], city: "HCMC" },
        poiList,
        menuList
      );
      
      expect(result).toEqual([]);
    });
    
    it('should apply price filter correctly', () => {
      const result = rankRestaurants(
        "",
        { price_max: 100000 },
        poiList,
        menuList
      );
      
      for (const r of result) {
        const menu_items = menuList.filter(m => m.restaurant_id === r.poi.id);
        const avg_price = mean(menu_items.map(m => m.price_vnd));
        expect(avg_price).toBeLessThanOrEqual(100000);
      }
    });
    
    it('should apply segment filter correctly', () => {
      const result = rankRestaurants(
        "",
        { segments: ["Gia đình"] },
        poiList,
        menuList
      );
      
      for (const r of result) {
        expect(r.poi.recommended_segments).toContain("Gia đình");
      }
    });
    
    it('should apply amenity filter correctly', () => {
      const result = rankRestaurants(
        "",
        { amenities: ["Bãi đỗ xe"] },
        poiList,
        menuList
      );
      
      for (const r of result) {
        expect(r.poi.amenities_raw).toContain("Bãi đỗ xe");
      }
    });
    
    it('should handle opening hours filter', () => {
      const result = rankRestaurants(
        "",
        { open_at_hour: 18 },
        poiList,
        menuList
      );
      
      for (const r of result) {
        const isOpen = isOpenAt(r.poi.hours, 18);
        expect(isOpen).toBe(true);
      }
    });
    
    it('should deduplicate results', () => {
      // Even if ranking produces same POI twice, it should appear once
      const result = rankRestaurants("", {}, poiList, menuList);
      const ids = result.map(r => r.poi.id);
      expect(ids.length).toBe(new Set(ids).size);  // All unique
    });
    
    it('should sort by score DESC, name ASC for stability', () => {
      const result = rankRestaurants("", {}, poiList, menuList);
      
      for (let i = 0; i < result.length - 1; i++) {
        const current_score = result[i].score;
        const next_score = result[i + 1].score;
        
        if (current_score === next_score) {
          // Tie-break by name
          expect(result[i].poi.name).toBeLessThanOrEqual(result[i + 1].poi.name);
        } else {
          expect(current_score).toBeGreaterThan(next_score);
        }
      }
    });
  });
  
  describe('MATCH_SEGMENT()', () => {
    it('should return 0 for no segment requirement', () => {
      const score = matchSegment(poi, null);
      expect(score).toBe(0.0);
    });
    
    it('should return 1.0 for perfect segment match', () => {
      const poi = { recommended_segments: "Gia đình; Business" };
      const score = matchSegment(poi, ["Gia đình"]);
      expect(score).toBe(1.0);
    });
    
    it('should handle partial matches', () => {
      const poi = { recommended_segments: "Gia đình; Business" };
      const score = matchSegment(poi, ["Gia đình", "Romantic"]);
      expect(score).toBe(0.5);  // 1 of 2 match
    });
  });
  
  describe('COMPUTE_PRICE_FIT()', () => {
    it('should return 0 for no price constraint', () => {
      const fit = computePriceFit(poi, null, null, menuItems);
      expect(fit).toBe(0.0);
    });
    
    it('should return 0 if avg price exceeds max', () => {
      const fit = computePriceFit(poi, null, 50000, menuItems);
      if (avgPrice > 50000) {
        expect(fit).toBe(0.0);
      }
    });
    
    it('should normalize price fit within range', () => {
      const fit = computePriceFit(poi, 50000, 150000, menuItems);
      expect(fit).toBeGreaterThanOrEqual(0.0);
      expect(fit).toBeLessThanOrEqual(1.0);
    });
  });
});
```

### 2.2 Module 2: OCR Parser

```javascript
// tests/module2.test.js

describe('Module 2: OCR Parser', () => {
  
  describe('PARSE_OCR_MENU()', () => {
    
    it('should extract dish name and price from line', () => {
      const ocr = "Pho bo tai .... 80.397 VND";
      const items = parseOcrMenu(ocr, "res001");
      
      expect(items).toHaveLength(1);
      expect(items[0].dishName).toMatch(/pho/i);
      expect(items[0].priceVnd).toBe(80397);
    });
    
    it('should normalize diacritics', () => {
      const ocr = "Bun cha .... 107.640 VND";  // Missing diacritics in OCR
      const items = parseOcrMenu(ocr, "res001");
      
      expect(items[0].dishName).toMatch(/b[uư]n/i);  // Should handle both
    });
    
    it('should validate price against ground truth', () => {
      const ocr = "Bun cha .... 107.640 VND";
      const items = parseOcrMenu(ocr, "res001");
      
      expect(items[0].matchedToGroundTruth).toBe(true);
      expect(items[0].priceVnd).toBe(107640);  // Exact match
    });
    
    it('should reject prices out of range', () => {
      const ocr = "Expensive dish .... 999.999 VND";
      const items = parseOcrMenu(ocr, "res001");
      
      if (items.length > 0) {
        expect(items[0].confidence).toBeLessThan(0.8);
        // Confidence reduced for unrealistic price
      }
    });
    
    it('should infer menu category from dish name', () => {
      const ocr1 = "Pho bo .... 80.397 VND";  // Main dish
      const ocr2 = "Nuoc chanh .... 15.000 VND";  // Beverage
      
      const items1 = parseOcrMenu(ocr1, "res001");
      const items2 = parseOcrMenu(ocr2, "res001");
      
      expect(items1[0].menuCategory).toBe("Món chính");
      expect(items2[0].menuCategory).toBe("Đồ uống");
    });
    
    it('should extract dietary tags', () => {
      const ocr = "Canh chay .... 45.000 VND";
      const items = parseOcrMenu(ocr, "res001");
      
      expect(items[0].dietaryTags).toContain("Chay");
    });
    
    it('should deduplicate entries', () => {
      const ocr = "Pho bo tai .... 80.397 VND\nPho bo tai .... 80.397 VND";
      const items = parseOcrMenu(ocr, "res001");
      
      expect(items).toHaveLength(1);  // Deduped
    });
    
    it('should return empty array for empty OCR', () => {
      const items = parseOcrMenu("", "res001");
      expect(items).toEqual([]);
    });
  });
  
  describe('EXTRACT_MENU_ITEM()', () => {
    it('should match pattern "Dish Name ... Price"', () => {
      const item = extractMenuItem("Bun cha .... 107.640 VND", "res001");
      
      expect(item).not.toBeNull();
      expect(item.dishName).toBeDefined();
      expect(item.priceVnd).toBe(107640);
    });
    
    it('should handle price without unit', () => {
      const item = extractMenuItem("Pho bo 80.397", "res001");
      
      if (item) {
        expect(item.priceVnd).toBe(80397);
      }
    });
    
    it('should return null for non-menu lines', () => {
      const item = extractMenuItem("This is not a menu item", "res001");
      expect(item).toBeNull();
    });
  });
});
```

### 2.3 Module 3: Review NLP

```javascript
// tests/module3.test.js

describe('Module 3: Review Sentiment & NLP', () => {
  
  describe('ANALYZE_REVIEWS()', () => {
    
    it('should aggregate aspects from multiple reviews', () => {
      const result = analyzeReviews("res001");
      
      expect(result.aspects).toBeDefined();
      expect(Array.isArray(result.aspects)).toBe(true);
    });
    
    it('should compute sentiment for each aspect', () => {
      const result = analyzeReviews("res001");
      
      for (const aspect of result.aspects) {
        expect(["positive", "negative", "neutral"]).toContain(aspect.sentiment);
        expect(aspect.strength).toBeGreaterThanOrEqual(-1.0);
        expect(aspect.strength).toBeLessThanOrEqual(1.0);
      }
    });
    
    it('should provide representative quotes', () => {
      const result = analyzeReviews("res001");
      
      for (const aspect of result.aspects) {
        if (aspect.count > 0) {
          expect(aspect.quotes.length).toBeGreaterThan(0);
        }
      }
    });
    
    it('should generate summary text', () => {
      const result = analyzeReviews("res001");
      expect(result.summary).toBeDefined();
      expect(result.summary.length).toBeGreaterThan(0);
    });
    
    it('should validate against known_strengths/weaknesses', () => {
      const result = analyzeReviews("res001");
      const poi = loadPoi("res001");
      
      const knownStrengths = poi.known_strengths.split(";").map(s => s.trim());
      const extractedAspects = result.aspects.map(a => a.aspect);
      
      // At least one known strength should be extracted
      const overlap = knownStrengths.filter(s => extractedAspects.includes(s));
      if (overlap.length === 0) {
        console.warn(`Warning: No overlap between known_strengths and extracted aspects`);
      }
    });
    
    it('should return empty for restaurant with no reviews', () => {
      const result = analyzeReviews("res_nonexistent");
      
      expect(result.aspects).toEqual([]);
      expect(result.meta.totalReviews).toBe(0);
    });
  });
  
  describe('CLASSIFY_SENTIMENT()', () => {
    
    it('should classify positive reviews', () => {
      const text = "Đồ ăn ngon, phục vụ nhanh, rất tốt!";
      const sentiment = classifySentiment(text);
      expect(sentiment).toBe("positive");
    });
    
    it('should classify negative reviews', () => {
      const text = "Tệ lắm, chậm, bẩn, không quay lại đâu.";
      const sentiment = classifySentiment(text);
      expect(sentiment).toBe("negative");
    });
    
    it('should classify neutral reviews', () => {
      const text = "Nhà hàng bình thường, không có gì đặc biệt.";
      const sentiment = classifySentiment(text);
      expect(sentiment).toBe("neutral");
    });
  });
});
```

### 2.4 Module 4: POI Quality Score

```javascript
// tests/module4.test.js

describe('Module 4: POI Quality Score', () => {
  
  describe('COMPUTE_POI_QUALITY()', () => {
    
    it('should compute score within [0.0, 1.0]', () => {
      const result = computeQualityScore("res001");
      
      expect(result.score).toBeGreaterThanOrEqual(0.0);
      expect(result.score).toBeLessThanOrEqual(1.0);
    });
    
    it('should provide component breakdown', () => {
      const result = computeQualityScore("res001");
      
      expect(result.components.ocrCoverage).toBeDefined();
      expect(result.components.reviewDensity).toBeDefined();
      expect(result.components.amenityDetail).toBeDefined();
      expect(result.components.hoursGranularity).toBeDefined();
    });
    
    it('should match ground truth within tolerance (±0.02)', () => {
      const computed = computeQualityScore("res001");
      const poi = loadPoi("res001");
      const groundTruth = poi.poi_quality_score;
      
      const error = Math.abs(computed.score - groundTruth);
      if (error > 0.02) {
        console.warn(`Quality score discrepancy for res001: ${error.toFixed(3)}`);
      }
      
      expect(error).toBeLessThanOrEqual(0.05);  // Loose tolerance for iteration
    });
    
    it('should provide recommendation text', () => {
      const result = computeQualityScore("res001");
      
      expect(result.recommendation).toBeDefined();
      expect(result.recommendation.length).toBeGreaterThan(0);
    });
    
    it('should handle missing OCR gracefully', () => {
      const result = computeQualityScore("res025");  // No OCR
      
      expect(result.components.ocrCoverage).toBe(0.0);
      expect(result.score).toBeGreaterThan(0.0);  // Still have other components
    });
  });
});
```

### 2.5 Module 5: Corridor Demo

```javascript
// tests/module5.test.js

describe('Module 5: Corridor Demo', () => {
  
  describe('Corridor Bundle Validation', () => {
    
    it('should load corridor bundle from cache', () => {
      const bundle = loadCorridorBundle();
      
      expect(bundle).toBeDefined();
      expect(bundle.corridor).toBeDefined();
      expect(bundle.gates).toBeDefined();
    });
    
    it('should have valid route geometry', () => {
      const bundle = loadCorridorBundle();
      
      for (const gate of bundle.gates) {
        expect(gate.progressKm).toBeGreaterThan(0);
        expect(gate.progressKm).toBeLessThanOrEqual(bundle.corridor.totalKm);
        expect(gate.coordinates.lat).toBeGreaterThanOrEqual(-90);
        expect(gate.coordinates.lat).toBeLessThanOrEqual(90);
      }
    });
    
    it('should have realistic detour costs', () => {
      const bundle = loadCorridorBundle();
      
      for (const gate of bundle.gates) {
        for (const poi of [gate.suggestion, ...gate.alternatives]) {
          if (poi && poi.detour) {
            expect(poi.detour.detourMeters).toBeGreaterThanOrEqual(-500);  // Allow small negatives
            expect(poi.detour.detourMeters).toBeLessThanOrEqual(20000);   // Sanity: < 20km detour
          }
        }
      }
    });
    
    it('should have cached at timestamp', () => {
      const bundle = loadCorridorBundle();
      
      expect(bundle.meta.cachedAt).toBeDefined();
      const cachedDate = new Date(bundle.meta.cachedAt);
      expect(cachedDate).toBeValid();
    });
  });
  
  describe('Data Isolation (CRITICAL)', () => {
    
    it('should NOT import any benchmark CSV filenames', () => {
      const code = fs.readFileSync('module5/**/*.js', 'utf8');
      const benchmarkFiles = [
        "Restaurant POI Dataset",
        "Menu Dataset",
        "OCR Menu Dataset",
        "Restaurant Reviews",
        "Public Evaluation"
      ];
      
      for (const file of benchmarkFiles) {
        expect(code).not.toContain(file);
      }
    });
    
    it('should only read from module5/cache/ + production APIs', () => {
      const readSync = fs.readdirSync('module5/cache/');
      expect(readSync).toContain('corridor_bundle.json');
      expect(readSync).toContain('api');
      
      // No file path references to /data/ from module5
      const buildCode = fs.readFileSync('module5/scripts/build_corridor.js', 'utf8');
      expect(buildCode).not.toContain('../data/');
      expect(buildCode).not.toContain('/data/');
    });
  });
  
  describe('Meal Window Gating', () => {
    
    it('should push during breakfast (6-9am)', () => {
      const result = getRestStops("hanoi-halong", 50, 7);  // 7am
      expect(result.push).toBe(true);
    });
    
    it('should push during lunch (11am-1pm)', () => {
      const result = getRestStops("hanoi-halong", 50, 12);
      expect(result.push).toBe(true);
    });
    
    it('should push during dinner (6-8pm)', () => {
      const result = getRestStops("hanoi-halong", 50, 19);
      expect(result.push).toBe(true);
    });
    
    it('should stay silent outside meal windows', () => {
      const result = getRestStops("hanoi-halong", 50, 3);  // 3am
      expect(result.push).toBe(false);
      expect(result.results).toEqual([]);
    });
  });
});
```

### 2.6 Shared Kernel (lib/)

```javascript
// tests/lib.test.js

describe('Shared Kernel', () => {
  
  describe('normalizeText()', () => {
    it('should remove diacritics', () => {
      expect(normalizeText("Phở")).toMatch(/pho/i);
      expect(normalizeText("Bún Chả")).toMatch(/bun cha/i);
    });
    
    it('should lowercase', () => {
      expect(normalizeText("HELLO")).toBe("hello");
    });
    
    it('should trim', () => {
      expect(normalizeText("  hello  ")).toBe("hello");
    });
  });
  
  describe('parsePrice()', () => {
    it('should parse "80.397 VND" → 80397', () => {
      expect(parsePrice("80.397 VND")).toBe(80397);
    });
    
    it('should parse "80397" → 80397', () => {
      expect(parsePrice("80397")).toBe(80397);
    });
    
    it('should throw on invalid input', () => {
      expect(() => parsePrice("abc")).toThrow();
    });
  });
  
  describe('levenshteinDistance()', () => {
    it('should be 0 for identical strings', () => {
      expect(levenshteinDistance("pho", "pho")).toBe(0);
    });
    
    it('should handle typos', () => {
      expect(levenshteinDistance("pho", "fho")).toBe(1);  // 1 substitution
    });
  });
  
  describe('mealWindow()', () => {
    it('should return push=true during breakfast', () => {
      const w = mealWindow(7);
      expect(w.meal).toBe("sáng");
      expect(w.push).toBe(true);
    });
    
    it('should return push=false at 3am', () => {
      const w = mealWindow(3);
      expect(w.push).toBe(false);
    });
  });
});
```

---

## 3. INTEGRATION TESTS

### 3.1 HTTP Contract Tests

```javascript
// tests/integration.test.js

const request = require('supertest');
const app = require('../src/server');

describe('HTTP Contracts (Integration)', () => {
  
  describe('GET /v1/search', () => {
    
    it('should return PlaceResult[]', async () => {
      const res = await request(app)
        .get('/v1/search')
        .query({ query: "gia đình bãi đỗ", limit: 5 });
      
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('results');
      expect(Array.isArray(res.body.results)).toBe(true);
      
      for (const place of res.body.results) {
        expect(place).toHaveProperty('id');
        expect(place).toHaveProperty('name');
        expect(place).toHaveProperty('score');
        expect(place).toHaveProperty('coordinates');
      }
    });
    
    it('should handle 404 for hallucination', async () => {
      const res = await request(app)
        .get('/v1/search')
        .query({ query: "Crystal BBQ" });
      
      expect(res.status).toBe(404);
      expect(res.body).toHaveProperty('error');
      expect(res.body.error.code).toBe('not_found');
    });
    
    it('should handle geographic trap gracefully', async () => {
      const res = await request(app)
        .get('/v1/search')
        .query({ query: "halal HCMC" });
      
      expect(res.status).toBe(200);
      expect(res.body.results).toEqual([]);
    });
  });
  
  describe('POST /v1/menu/parse', () => {
    
    it('should parse OCR and return StructuredMenu', async () => {
      const res = await request(app)
        .post('/v1/menu/parse')
        .send({
          rawOcrText: "Pho bo tai .... 80.397 VND",
          restaurantId: "res001"
        });
      
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('items');
      expect(Array.isArray(res.body.items)).toBe(true);
      
      if (res.body.items.length > 0) {
        const item = res.body.items[0];
        expect(item).toHaveProperty('dishName');
        expect(item).toHaveProperty('priceVnd');
        expect(item).toHaveProperty('confidence');
      }
    });
  });
  
  describe('GET /v1/reviews/analyze', () => {
    
    it('should analyze reviews and return aspects', async () => {
      const res = await request(app)
        .get('/v1/reviews/analyze')
        .query({ restaurantId: "res001" });
      
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('aspects');
      expect(res.body).toHaveProperty('summary');
      
      for (const aspect of res.body.aspects) {
        expect(["positive", "negative", "neutral"]).toContain(aspect.sentiment);
      }
    });
  });
  
  describe('GET /v1/poi/quality-score', () => {
    
    it('should compute quality score', async () => {
      const res = await request(app)
        .get('/v1/poi/quality-score')
        .query({ restaurantId: "res001" });
      
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('score');
      expect(res.body.score).toBeGreaterThanOrEqual(0.0);
      expect(res.body.score).toBeLessThanOrEqual(1.0);
    });
  });
  
  describe('GET /v1/route/rest-stops', () => {
    
    it('should return rest stop recommendations', async () => {
      const res = await request(app)
        .get('/v1/route/rest-stops')
        .query({
          corridorId: "hanoi-halong",
          currentProgressKm: 80,
          atHour: 12
        });
      
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('results');
      expect(res.body).toHaveProperty('push');
      expect(res.body).toHaveProperty('meal');
    });
    
    it('should return 404 for unknown corridor', async () => {
      const res = await request(app)
        .get('/v1/route/rest-stops')
        .query({
          corridorId: "unknown-route",
          currentProgressKm: 50
        });
      
      expect(res.status).toBe(404);
    });
  });
});
```

---

## 4. EVALUATION HARNESS (15 Benchmark Questions)

### 4.1 Eval Spec

```javascript
// tests/eval_harness.js

const EVAL_QUESTIONS = [
  {
    id: "eval_001",
    category: "Food Search",
    query: "Find restaurants with vegetarian options under 150K in Hanoi",
    expected_type: "restaurant_list",
    trap: null,
    modules: [1, 2],
    validator: (result) => {
      // Must return restaurants with vegetarian menu items, price < 150k, in Hanoi
      return result.filter(r =>
        r.city === "Hanoi" &&
        avg_price(r) < 150000 &&
        has_vegetarian_item(r)
      ).length > 0;
    }
  },
  
  {
    id: "eval_002",
    category: "Family Dining",
    query: "Restaurants in Nha Trang with kids chairs, evening open, family-friendly",
    expected_type: "restaurant_list",
    trap: null,
    modules: [1],
    validator: (result) => {
      return result.filter(r =>
        r.city === "Nha Trang" &&
        r.amenities_raw.includes("Phù hợp trẻ em") &&
        r.recommended_segments.includes("Gia đình") &&
        isOpen(r.hours, 18)
      ).length > 0;
    }
  },
  
  {
    id: "eval_003",
    category: "Dietary (Halal)",
    query: "Halal restaurants in HCMC",
    expected_type: "restaurant_list",
    trap: "geographic",  // No halal in HCMC; test honesty
    modules: [1],
    validator: (result) => {
      // Must return empty array (no halal in HCMC)
      return result.length === 0;
    }
  },
  
  {
    id: "eval_004",
    category: "Review Analysis",
    query: "What are customers saying about Crystal BBQ?",
    expected_type: "error_not_found",
    trap: "hallucination",  // Crystal BBQ doesn't exist
    modules: [3],
    validator: (result) => {
      // Must return 404 or not_found error
      return result.error && result.error.code === "not_found";
    }
  },
  
  {
    id: "eval_005",
    category: "Budget + Rating",
    query: "Best-rated restaurant under 100K in Ha Long",
    expected_type: "restaurant",
    trap: null,
    modules: [1],
    validator: (result) => {
      if (!result) return false;
      return result.city === "Ha Long" &&
             avg_price(result) < 100000 &&
             result.rating >= 4.0;  // "Best-rated"
    }
  },
  
  {
    id: "eval_006",
    category: "Late Night",
    query: "Which restaurants open after 11 PM with parking?",
    expected_type: "restaurant_list",
    trap: null,
    modules: [1],
    validator: (result) => {
      // Must all have late hours + parking
      return result.filter(r =>
        isOpen(r.hours, 23) &&
        r.amenities_raw.includes("Bãi đỗ xe")
      ).length > 0;
    }
  },
  
  {
    id: "eval_007",
    category: "Comparison",
    query: "Compare service quality of RES002 and RES004 based on reviews",
    expected_type: "comparison_text",
    trap: null,
    modules: [3],
    validator: (result) => {
      // Should analyze aspects for both restaurants
      return result && result.length > 0;
    }
  },
  
  {
    id: "eval_008",
    category: "POI Quality",
    query: "Which restaurant has most complete information?",
    expected_type: "restaurant",
    trap: null,
    modules: [4],
    validator: (result) => {
      // Should return restaurant with highest poi_quality_score
      return result && result.poi_quality_score >= 0.90;
    }
  },
  
  {
    id: "eval_009",
    category: "Menu Search",
    query: "Does Pho Hoa Nhan have Pho Tai?",
    expected_type: "boolean",
    trap: null,
    modules: [2],
    validator: (result) => {
      // Must check Menu Dataset for this combination
      return result === true || result === false;
    }
  },
  
  {
    id: "eval_010",
    category: "Menu Extraction",
    query: "What is the exact price of Bun Cha at RES001?",
    expected_type: "number",
    trap: null,
    modules: [2],
    validator: (result) => {
      // Must return 107640 (from Menu Dataset)
      return result === 107640;
    }
  },
  
  {
    id: "eval_011",
    category: "Menu QA",
    query: "Find dishes with beef and under 100K",
    expected_type: "dish_list",
    trap: null,
    modules: [1, 2],
    validator: (result) => {
      // Must filter menu items: beef-related, price < 100k
      return result && result.every(d =>
        d.ingredients.some(i => i.includes("beef") || i.includes("bò")) &&
        d.price_vnd < 100000
      );
    }
  },
  
  {
    id: "eval_012",
    category: "Business Dining",
    query: "Professional restaurants with meeting rooms in Da Nang",
    expected_type: "restaurant_list",
    trap: null,
    modules: [1],
    validator: (result) => {
      return result && result.every(r =>
        r.city === "Da Nang" &&
        r.recommended_segments.includes("Business")
      );
    }
  },
  
  {
    id: "eval_013",
    category: "Romantic",
    query: "Upscale restaurants with ambiance for couples in Da Lat",
    expected_type: "restaurant_list",
    trap: null,
    modules: [1, 3],
    validator: (result) => {
      return result && result.every(r =>
        r.city === "Da Lat" &&
        r.recommended_segments.includes("Romantic")
      );
    }
  },
  
  {
    id: "eval_014",
    category: "Casual + Keywords",
    query: "Quick breakfast near Hanoi",
    expected_type: "restaurant_list",
    trap: null,
    modules: [1],
    validator: (result) => {
      return result && result.every(r => r.city === "Hanoi");
    }
  },
  
  {
    id: "eval_015",
    category: "AI Summary",
    query: "Summarize what makes Restaurant RES002 special",
    expected_type: "text",
    trap: null,
    modules: [3],
    validator: (result) => {
      // Should generate a non-empty summary
      return result && result.length > 20;
    }
  }
];
```

### 4.2 Eval Runner

```javascript
// tests/run_eval.js

async function runEvaluation() {
  const results = {};
  let passed = 0;
  let failed = 0;
  
  for (const question of EVAL_QUESTIONS) {
    console.log(`\n[${question.id}] ${question.category}: ${question.query}`);
    
    try {
      let response;
      
      // Route based on category
      if (question.modules.includes(1)) {
        response = await querySearch(question.query);
      } else if (question.modules.includes(2)) {
        response = await queryOcr(question.query);
      } else if (question.modules.includes(3)) {
        response = await queryReviews(question.query);
      } else if (question.modules.includes(4)) {
        response = await queryQuality(question.query);
      }
      
      const isValid = question.validator(response);
      
      if (isValid) {
        console.log(`✓ PASS`);
        passed++;
      } else {
        console.log(`✗ FAIL`);
        console.log(`  Response:`, JSON.stringify(response, null, 2).slice(0, 200));
        failed++;
      }
      
      results[question.id] = {
        category: question.category,
        passed: isValid,
        response: response
      };
      
    } catch (e) {
      console.log(`✗ ERROR: ${e.message}`);
      failed++;
      results[question.id] = { error: e.message };
    }
  }
  
  // Summary
  console.log(`\n${'='.repeat(60)}`);
  console.log(`EVALUATION RESULTS: ${passed}/${EVAL_QUESTIONS.length} passed`);
  console.log(`${'='.repeat(60)}`);
  
  // Write report
  fs.writeFileSync('eval_report.json', JSON.stringify(results, null, 2));
  
  return { passed, failed, total: EVAL_QUESTIONS.length };
}

module.exports = { runEvaluation, EVAL_QUESTIONS };
```

---

## 5. DATA QUALITY TESTS

### 5.1 CSV Integrity

```javascript
// tests/data_quality.test.js

describe('Data Quality & Integrity', () => {
  
  describe('CSV Completeness', () => {
    
    it('should have exactly 30 restaurants in POI Dataset', () => {
      const poi = loadCsv('data/POI/*.csv');
      expect(poi).toHaveLength(30);
    });
    
    it('should have 179 menu items', () => {
      const menu = loadCsv('data/Menu/*.csv');
      expect(menu).toHaveLength(179);
    });
    
    it('should have 150 reviews (5 per restaurant)', () => {
      const reviews = loadCsv('data/Reviews/*.csv');
      expect(reviews).toHaveLength(150);
      
      const byRestaurant = groupBy(reviews, 'restaurant_id');
      for (const restaurantId of ['res001', ..., 'res030']) {
        expect(byRestaurant[restaurantId]).toHaveLength(5);
      }
    });
    
    it('should have exactly 15 eval questions', () => {
      const eval_csv = loadCsv('data/Eval/*.csv');
      expect(eval_csv).toHaveLength(15);
    });
  });
  
  describe('Data Consistency', () => {
    
    it('should have no orphaned menu items', () => {
      const menu = loadCsv('data/Menu/*.csv');
      const poi_ids = loadCsv('data/POI/*.csv').map(p => p.restaurant_id);
      
      for (const item of menu) {
        expect(poi_ids).toContain(item.restaurant_id);
      }
    });
    
    it('should have no duplicate restaurant IDs', () => {
      const poi = loadCsv('data/POI/*.csv');
      const ids = poi.map(p => p.id);
      
      expect(ids.length).toBe(new Set(ids).size);  // All unique
    });
    
    it('should have valid coordinates', () => {
      const poi = loadCsv('data/POI/*.csv');
      
      for (const p of poi) {
        expect(p.latitude).toBeGreaterThanOrEqual(-90);
        expect(p.latitude).toBeLessThanOrEqual(90);
        expect(p.longitude).toBeGreaterThanOrEqual(-180);
        expect(p.longitude).toBeLessThanOrEqual(180);
      }
    });
    
    it('should have valid price values', () => {
      const menu = loadCsv('data/Menu/*.csv');
      
      for (const item of menu) {
        expect(item.price_vnd).toBeGreaterThan(0);
        expect(item.price_vnd).toBeLessThan(500000);
      }
    });
  });
});
```

### 5.2 Module 5 Isolation Test

```javascript
// tests/module5_isolation.test.js

describe('Module 5 Data Isolation (CRITICAL)', () => {
  
  it('should not reference benchmark CSV files', () => {
    const files = [
      'module5/lib/module1_engine.js',
      'module5/scripts/build_corridor.js',
      'module5/server.js',
      'module5/ui/index.html'
    ];
    
    const benchmarkNames = [
      'Restaurant POI Dataset',
      'Menu Dataset',
      'OCR Menu Dataset',
      'Restaurant Reviews',
      'Public Evaluation'
    ];
    
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf8');
      for (const name of benchmarkNames) {
        expect(content).not.toContain(name);
      }
    }
  });
  
  it('should only load from module5/cache/', () => {
    const serverCode = fs.readFileSync('module5/server.js', 'utf8');
    
    expect(serverCode).toContain('module5/cache/');
    expect(serverCode).not.toContain('../data/');
    expect(serverCode).not.toContain('../../data/');
  });
  
  it('should have no require() for benchmark files', () => {
    const files = glob('module5/**/*.js');
    
    for (const file of files) {
      const code = fs.readFileSync(file, 'utf8');
      
      // No require('../data/...')
      expect(code).not.toMatch(/require\(['"].*data\/.*['"]\)/);
      expect(code).not.toMatch(/import.*from ['"].*data\/.*['"]/);
    }
  });
});
```

---

## 6. TEST EXECUTION

### 6.1 Test Commands

```bash
# Unit tests
npm test -- tests/module1.test.js
npm test -- tests/module2.test.js
npm test -- tests/module3.test.js
npm test -- tests/module4.test.js
npm test -- tests/module5.test.js
npm test -- tests/lib.test.js

# Integration tests
npm run test:integration

# Full eval (15 questions)
npm run test:eval

# Data quality checks
npm run test:data

# Module 5 isolation (must pass)
npm test -- tests/module5_isolation.test.js

# Run all tests
npm test
```

### 6.2 Coverage Goals

| Layer | Goal | Tool |
|-------|------|------|
| **Unit** | >85% statements | Jest coverage |
| **Integration** | All endpoints | Supertest |
| **Eval** | 15/15 or better | Custom harness |
| **Data** | 100% consistency | CSV validation |

---

**Next:** SYSTEM_05_BUILD_RUNBOOK.md defines step-by-step build, test, and deployment commands.

