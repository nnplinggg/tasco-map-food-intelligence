# TASCO FOOD INTELLIGENCE — COMPLETE SYSTEM DESIGN
## Master Index & Table of Contents

---

## EXECUTIVE SUMMARY FOR AI DEVELOPERS

You are being handed a **complete, AI-executable system specification** for the Tasco Maps Food Intelligence hackathon. This is not a vague brief — every algorithm is written in pseudo-code, every data flow is diagrammed, every API contract is specified, and every test case is written.

**Your job:** Implement this spec exactly as written, using the language/framework of your choice.

**Philosophy:** If this spec requires you to guess about behavior, it's incomplete. Ask before coding.

---

## DOCUMENT STRUCTURE (Read in Order)

### **SYSTEM_01_ARCHITECTURE.md** — System Design & Data Flows
**Audience:** Everyone (architect-level overview)  
**Length:** ~2000 words  
**Time to read:** 15–20 mins

**Contains:**
- Module boundary definitions (5 independent modules + 1 shared kernel)
- Dependency graph (what calls what)
- Complete data flow diagrams for each module (request → response)
- Shared kernel specifications (normalize, parse, match, datetime, DTOs)
- Error handling strategy
- Database/file layout

**After reading, you understand:**
- How the 5 modules fit together
- What data flows where
- Which modules are independent (can build in parallel)
- API contracts at HTTP level

**Key deliverable:** Folder structure, file layout, module boundaries.

---

### **SYSTEM_02_ALGORITHMS.md** — Exact Specifications with Pseudo-Code
**Audience:** Developers (algorithm-level detail)  
**Length:** ~5000 words  
**Time to read:** 45–60 mins

**Contains:**
- **Module 1 (Search):** RANK_RESTAURANTS() pseudo-code with 4-factor scoring formula
  - Filter-by-constraints algorithm
  - Sub-functions: MATCH_SEGMENT, MATCH_AMENITY, MATCH_KEYWORDS, COMPUTE_PRICE_FIT
  - Complexity analysis: O(30 + log 30) = O(1) practical time
  - Edge cases: hallucination traps, empty results, ties

- **Module 2 (OCR):** PARSE_OCR_MENU() pseudo-code
  - Line-by-line extraction with regex
  - Category inference, dietary tag extraction, ingredient parsing
  - Confidence scoring
  - Validation against ground truth
  - Complexity: O(n_ocr_length)

- **Module 3 (Review NLP):** ANALYZE_REVIEWS() pseudo-code
  - Sentiment classification (positive/negative/neutral)
  - Aspect extraction + aggregation
  - Summary generation (heuristic-based)
  - Complexity: O(n_reviews × n_review_length)

- **Module 4 (Quality Score):** COMPUTE_POI_QUALITY() pseudo-code
  - 4-component scoring (OCR coverage, review density, amenity detail, hours granularity)
  - Weights: 0.35, 0.30, 0.20, 0.15
  - Complexity: O(n_menu + n_reviews)

- **Module 5 (Corridor):** Reuses Module 1 ranker; no new algorithms
  - Meal-window gating logic
  - Progress filtering (40 km lookahead)

**After reading, you understand:**
- Exactly what computation happens in each module
- Edge cases and how to handle them
- Time complexity and expected performance
- How to validate outputs against ground truth

**Key deliverable:** Working pseudo-code you can translate to your language.

---

### **SYSTEM_03_DATA_MODELS.md** — TypeScript Interfaces & JSON Schemas
**Audience:** Developers & QA (data contract detail)  
**Length:** ~3000 words  
**Time to read:** 30–40 mins

**Contains:**
- **Domain models:** POI, MenuItem, Review (shape & fields)
- **Request/Response DTOs for all 5 modules**
  - Module 1 Search: SearchRequest → SearchResponse (PlaceResult[])
  - Module 2 OCR: ParseOcrRequest → ParseOcrResponse (StructuredMenuItem[])
  - Module 3 Review: AnalyzeReviewsRequest → AnalyzeReviewsResponse (AspectList)
  - Module 4 Quality: ComputeQualityScoreRequest → ComputeQualityScoreResponse
  - Module 5 Corridor: CorridorRestStopsRequest → CorridorRestStopsResponse

- **Internal indices** (POI by_id, by_segment; Menu by_restaurant, by_dish; etc.)
- **CSV schema** for all 5 input datasets
- **Error codes** (400, 404, 422, 500 + error response format)
- **Validation rules** (price ranges, coordinates, hallucination traps)

**After reading, you understand:**
- Exact shape of every input/output
- How to validate requests/responses
- What fields are required vs optional
- How to handle errors consistently

**Key deliverable:** Type definitions (TypeScript, OpenAPI, or equivalent).

---

### **SYSTEM_04_TEST_PLAN.md** — Unit, Integration, & Evaluation Tests
**Audience:** QA & Developers (test case detail)  
**Length:** ~4000 words  
**Time to read:** 45–60 mins

**Contains:**
- **Unit tests** (40+) for all modules
  - Module 1: ranking formula, filter functions, edge cases (Crystal BBQ, Halal HCMC)
  - Module 2: OCR parsing, diacritic handling, price validation
  - Module 3: sentiment classification, aspect extraction, aggregation
  - Module 4: component scoring, ground-truth validation
  - Module 5: corridor bundle validation, meal-window gating, data isolation

- **Integration tests** (12) for HTTP contracts
  - /v1/search, /v1/menu/parse, /v1/reviews/analyze, /v1/poi/quality-score, /v1/route/rest-stops
  - Error responses, status codes

- **Evaluation harness** (15 benchmark questions)
  - Each question has: category, query, expected_type, trap_flag, validator function
  - Questions span all modules: Food Search, Family Dining, Budget, Halal, Reviews, Quality, Menu, etc.
  - 2 trap questions: Crystal BBQ (hallucination), Halal HCMC (geographic trap)

- **Data quality tests** (20+)
  - CSV completeness, consistency, foreign key integrity
  - Module 5 isolation verification (must not read benchmark files)

**After reading, you understand:**
- What "correct" looks like for every function
- How to validate against ground truth
- How to catch common errors (hallucination, traps)
- How to measure success (15/15 eval questions)

**Key deliverable:** Test code you can execute to verify correctness.

---

### **SYSTEM_05_BUILD_RUNBOOK.md** — Build, Test, Deploy
**Audience:** DevOps & Developers (operational procedures)  
**Length:** ~2000 words  
**Time to read:** 20–30 mins

**Contains:**
- **First-time setup:** Prerequisites, clone, install, build indices, compile modules
- **Testing procedures:**
  - Unit tests: `npm test`
  - Integration tests: `npm run test:integration`
  - Data quality: `npm run test:data`
  - Evaluation: `npm run test:eval` (15 questions)
  - Full suite: `npm run test:all` (~3–5 mins)

- **Local development:**
  - Start server: `npm start` (port 8787)
  - Manual curl tests for all endpoints
  - Debug mode with verbose logging

- **Deployment:**
  - Docker build + run
  - Systemd service (Linux)
  - Environment variables (API keys, port, caching mode)
  - Health check endpoint

- **Maintenance:**
  - Rebuild indices if CSVs change
  - Update Module 5 corridor cache if APIs change
  - Monitor performance, memory, response times
  - Troubleshooting guide (common issues + fixes)

- **Quick reference:** All commands in one place

**After reading, you understand:**
- How to set up the dev environment
- How to verify everything works (locally, integration, eval)
- How to deploy to production
- How to monitor and fix issues

**Key deliverable:** Deployable system that passes all tests.

---

## NAVIGATION GUIDE

### "I want to understand the system architecture"
→ Start with **SYSTEM_01_ARCHITECTURE.md**

### "I want to implement Module 1 (Search)"
→ SYSTEM_01 (data flow) → SYSTEM_02 (algorithms) → SYSTEM_03 (interfaces) → SYSTEM_04 (tests)

### "I want to write tests"
→ SYSTEM_04_TEST_PLAN.md (copy the test code)

### "I want to deploy this"
→ SYSTEM_05_BUILD_RUNBOOK.md

### "I'm debugging a failing test"
→ SYSTEM_02 (algorithm logic) → SYSTEM_03 (data format) → SYSTEM_04 (test case)

### "I need to understand an error response"
→ SYSTEM_03 (error codes section)

### "I need to verify data integrity"
→ SYSTEM_04 (data quality tests section)

---

## FILE STRUCTURE AFTER BUILD

```
tasco-map-food-intelligence/
├── README.md                           # You are here
├── SYSTEM_01_ARCHITECTURE.md           # System design
├── SYSTEM_02_ALGORITHMS.md             # Algorithms & pseudo-code
├── SYSTEM_03_DATA_MODELS.md            # DTOs & schemas
├── SYSTEM_04_TEST_PLAN.md              # Test specifications
├── SYSTEM_05_BUILD_RUNBOOK.md          # Build & deploy
│
├── package.json                        # NPM dependencies
├── .env                                # Environment variables (optional)
│
├── src/
│   ├── index.js                        # Entry point (HTTP server)
│   ├── server.js                       # Express/HTTP setup
│   │
│   ├── lib/                            # Shared kernel
│   │   ├── normalize.js                # normalizeText(), removeDiacritics()
│   │   ├── format.js                   # parsePrice(), formatPrice(), parseHours()
│   │   ├── match.js                    # levenshteinDistance(), segment/amenity matching
│   │   ├── datetime.js                 # isOpenNow(), mealWindow()
│   │   ├── module1_engine.js           # rankRestaurants() (shared with Module 5)
│   │   └── dto.js                      # DTO definitions, validation
│   │
│   ├── modules/
│   │   ├── module1.js                  # /v1/search endpoint
│   │   ├── module2.js                  # /v1/menu/parse endpoint
│   │   ├── module3.js                  # /v1/reviews/analyze endpoint
│   │   ├── module4.js                  # /v1/poi/quality-score endpoint
│   │   └── module5.js                  # /v1/route/rest-stops endpoint
│   │
│   └── data-loader.js                  # CSV loading & indexing
│
├── data/
│   ├── POI/
│   │   ├── ai_maps_track6_dataset_participants.xlsm - Restaurant POI Dataset.csv  (input)
│   │   ├── index_by_id.json            (generated)
│   │   └── lookup_by_segment.json      (generated)
│   │
│   ├── Menu/
│   │   ├── ai_maps_track6_dataset_participants.xlsm - Menu Dataset.csv  (input)
│   │   ├── index_by_restaurant.json    (generated)
│   │   └── index_by_dish.json          (generated)
│   │
│   ├── OCR/
│   │   ├── ai_maps_track6_dataset_participants.xlsm - OCR Menu Dataset.csv  (input)
│   │   └── raw_by_restaurant.json      (generated)
│   │
│   ├── Reviews/
│   │   ├── ai_maps_track6_dataset_participants.xlsm - Restaurant Reviews.csv  (input)
│   │   ├── by_restaurant.json          (generated)
│   │   └── aspects.json                (precomputed aspect vocabulary)
│   │
│   └── Eval/
│       └── ai_maps_track6_dataset_participants.xlsm - Public Evaluation.csv  (input)
│
├── module5/                            # Corridor demo (independent)
│   ├── lib/
│   │   ├── geometry.js                 # Polyline, haversine, snap-to-segment
│   │   ├── tasco_api.js                # 4-endpoint adapter, cache-first
│   │   └── module1_engine.js           # (symlink to ../../src/lib/module1_engine.js)
│   │
│   ├── scripts/
│   │   └── build_corridor.js           # Build cache from production APIs
│   │
│   ├── server.js                       # :8790 demo HTTP server
│   ├── ui/
│   │   └── index.html                  # SVG map, vehicle animation, ledger
│   │
│   ├── test/
│   │   └── run_tests.js                # 23 tests (geometry, engine, isolation)
│   │
│   ├── cache/
│   │   ├── corridor_bundle.json        # (generated by build_corridor.js)
│   │   └── api/                        # Cached API responses (offline replay)
│   │       ├── 0026e3abcee414fd.json
│   │       ├── 006d068c1047a184.json
│   │       └── ... (1000+ files)
│   │
│   └── README.md                       # Module 5 specific runbook
│
├── tests/
│   ├── module1.test.js                 # Search engine tests
│   ├── module2.test.js                 # OCR parser tests
│   ├── module3.test.js                 # Review NLP tests
│   ├── module4.test.js                 # Quality score tests
│   ├── module5.test.js                 # Corridor demo tests
│   ├── lib.test.js                     # Shared kernel tests
│   ├── integration.test.js             # HTTP contract tests
│   ├── data_quality.test.js            # CSV integrity + isolation
│   ├── eval_harness.js                 # 15 benchmark questions
│   └── run_eval.js                     # Eval runner (auto-scoring)
│
└── docs/
    ├── ERRORS_AND_TRAPS.md             # Hallucination trap handling
    ├── PERFORMANCE_TUNING.md           # Optimization tips
    └── FAQ.md                          # Frequently asked questions
```

---

## QUICK START (For Impatient People)

```bash
# 1. Setup (5 mins)
npm install
npm run data:load
npm run build

# 2. Test (2 mins)
npm run test:eval

# 3. Deploy (1 min)
npm start

# Visit: http://localhost:8787/v1/search?query=gia%20đình%20bãi%20đỗ
# Result: JSON array of matching restaurants

# Expected: 15/15 eval questions pass
```

---

## KEY CONSTRAINTS & PRINCIPLES

### 1. **Zero Ambiguity**
Every algorithm is written. No "you decide" or "implement as you see fit." If something isn't specified, it's a gap in this spec—ask before coding.

### 2. **AI-Executable**
This spec is designed to be read by and executed by AI code generators (Claude, GPT, etc.). No vague narratives. Every function has input/output contracts, edge cases, and test cases.

### 3. **Modular Independence**
All 5 modules (1–4) can be built in parallel. No cross-module dependencies except Module 5 → Module 1 (shared ranker only).

### 4. **Trapful Eval**
The 15 benchmark questions include intentional traps:
- **Hallucination:** "Crystal BBQ" doesn't exist → must return 404, never invent
- **Geographic:** "Halal HCMC" has zero matches → must return [], not error
- **Data quality:** "Does RES002 have Pho Tai?" → check Menu Dataset exactly

### 5. **Offline-Safe Module 5**
Corridor demo builds once from APIs, caches everything, replays offline during demo. No network dependency.

### 6. **Complete Test Coverage**
40+ unit tests + 12 integration tests + 15 eval questions + 20+ data quality checks. If you pass all tests, you pass the hackathon.

---

## SUCCESS CRITERIA

| Criterion | Evidence | How to Verify |
|-----------|----------|---------------|
| **Correctness** | 15/15 eval questions pass | `npm run test:eval` |
| **No hallucination** | Crystal BBQ trap handled correctly | eval_004 passes (404 response) |
| **Honesty** | Halal HCMC returns empty, not error | eval_003 passes ([] response) |
| **Code quality** | >85% unit test coverage | `npm test -- --coverage` |
| **Performance** | <100ms search, <500ms OCR | Load tests pass |
| **Data integrity** | All CSVs consistent, no orphans | `npm run test:data` |
| **Isolation** | Module 5 doesn't read benchmark files | `npm test -- tests/module5_isolation.test.js` |
| **HTTP contracts** | All endpoints return correct DTOs | `npm run test:integration` |

**Passing all = Hackathon ready.**

---

## RECOMMENDED READING ORDER

1. **10 mins:** SYSTEM_01 (overview)
2. **15 mins:** SYSTEM_05 (build setup, so you can start coding)
3. **60 mins:** SYSTEM_02 (algorithms, the actual logic)
4. **30 mins:** SYSTEM_03 (data contracts, so you code the right shapes)
5. **60 mins:** SYSTEM_04 (write tests before/during coding)
6. **Ongoing:** Use each SYSTEM doc as reference while implementing

**Total time:** ~3 hours to fully understand, then code for 4 hours.

---

## SUPPORT & ESCALATION

**Question:** "The spec doesn't explain X"  
**Action:** Check all 5 SYSTEM docs. If still unclear, this is a spec gap. Ask for clarification before coding.

**Question:** "A test is failing"  
**Action:** 
1. Read the test case in SYSTEM_04
2. Re-read the algorithm in SYSTEM_02
3. Check data shapes in SYSTEM_03
4. Verify error handling strategy in SYSTEM_01

**Question:** "Can I do it differently?"  
**Action:** No. The spec is exact. But if your approach is provably better (faster, clearer, same output), propose it + add test to prove equivalence.

---

## DOCUMENT VERSIONS

| Document | Version | Last Updated | Status |
|----------|---------|--------------|--------|
| SYSTEM_01_ARCHITECTURE.md | 1.0 | 2026-07-11 | Final |
| SYSTEM_02_ALGORITHMS.md | 1.0 | 2026-07-11 | Final |
| SYSTEM_03_DATA_MODELS.md | 1.0 | 2026-07-11 | Final |
| SYSTEM_04_TEST_PLAN.md | 1.0 | 2026-07-11 | Final |
| SYSTEM_05_BUILD_RUNBOOK.md | 1.0 | 2026-07-11 | Final |

**Stability:** These specs are locked. No changes during development. If issues arise, log them; fix in v1.1 post-hackathon.

---

**END OF MASTER INDEX**

You now have everything needed to build the Tasco Maps Food Intelligence system from scratch. Good luck! 🚀

