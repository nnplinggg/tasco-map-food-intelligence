# TASCO FOOD INTELLIGENCE — BUILD RUNBOOK & DEPLOYMENT
## Part 5: Step-by-Step Build, Test, Deploy, and Operations

---

## 1. PREREQUISITES

### 1.1 Environment

- **Node.js:** v18+ (for native async/await, top-level await)
- **NPM:** 9+ (for npm workspaces if modular)
- **OS:** Linux/macOS/Windows (WSL2 recommended for Windows)
- **Disk:** 500MB (code + node_modules + data + cache)
- **Memory:** 512MB minimum (preferably 2GB+ for indexing)

### 1.2 Files Required (Already in Repo)

```
tasco-map-food-intelligence/
├── data/
│   ├── POI/
│   │   └── ai_maps_track6_dataset_participants.xlsm - Restaurant POI Dataset.csv
│   ├── Menu/
│   │   └── ai_maps_track6_dataset_participants.xlsm - Menu Dataset.csv
│   ├── OCR/
│   │   └── ai_maps_track6_dataset_participants.xlsm - OCR Menu Dataset.csv
│   ├── Reviews/
│   │   └── ai_maps_track6_dataset_participants.xlsm - Restaurant Reviews.csv
│   └── Eval/
│       └── ai_maps_track6_dataset_participants.xlsm - Public Evaluation.csv
├── package.json
├── package-lock.json
└── src/
    ├── index.js
    └── (module source files)
```

---

## 2. FIRST-TIME SETUP

### 2.1 Clone & Install

```bash
# Clone repo (or unzip if already downloaded)
git clone <repo-url>
cd tasco-map-food-intelligence

# Install dependencies
npm install

# Verify Node version
node --version  # Should be v18+
```

### 2.2 Build Data Indices

```bash
# Load CSVs and build all indices (indexes for fast lookups)
npm run data:load

# This creates:
#   data/POI/index_by_id.json
#   data/POI/lookup_by_segment.json
#   data/Menu/index_by_restaurant.json
#   data/Menu/index_by_dish.json
#   data/Reviews/by_restaurant.json
#   etc.

# Verification
ls -la data/POI/index_by_id.json     # Should exist, ~50KB
ls -la data/Menu/index_by_restaurant.json  # Should exist, ~30KB
```

### 2.3 Compile Modules

```bash
# Build all modules (generates optimized bundles, if applicable)
npm run build

# Or individually (if parallel needed):
npm run build:module1 &
npm run build:module2 &
npm run build:module3 &
npm run build:module4 &
npm run build:module5 &
wait

# Module 5 also needs to build corridor bundle from APIs
npm run build:module5     # This calls module5/scripts/build_corridor.js
# Requires: TASCO_ROUTE_BASE, TASCO_GEOCODE_BASE, TASCO_BEARER_TOKEN env vars
# Or uses cached version if cache/corridor_bundle.json already exists
```

---

## 3. TESTING

### 3.1 Unit Tests

```bash
# Run all unit tests
npm test

# Or specific module:
npm test -- tests/module1.test.js
npm test -- tests/module2.test.js
npm test -- tests/module3.test.js
npm test -- tests/module4.test.js
npm test -- tests/module5.test.js
npm test -- tests/lib.test.js

# With coverage:
npm test -- --coverage

# Expected output:
#   Pass: ✓ 45+ tests
#   Coverage: >85% statements
```

### 3.2 Integration Tests

```bash
# Start server in background
npm start &
SERVER_PID=$!

# Run integration tests
npm run test:integration

# Stop server
kill $SERVER_PID

# Expected output:
#   Pass: ✓ 12 HTTP contract tests
#   All endpoints (search, OCR, reviews, quality, corridor) responding
```

### 3.3 Data Quality Tests

```bash
# Verify CSV integrity, consistency, isolation
npm run test:data

# Expected output:
#   ✓ 30 POI records
#   ✓ 179 menu items
#   ✓ 150 reviews (5 per restaurant)
#   ✓ All foreign keys valid
#   ✓ Module 5 doesn't reference benchmark files
```

### 3.4 Evaluation (15 Questions)

```bash
# Auto-score 15 benchmark questions
npm run test:eval

# This runs EVAL_QUESTIONS from tests/eval_harness.js
# Each question has a validator; response is pass/fail

# Expected output:
#   eval_001: ✓ PASS
#   eval_002: ✓ PASS
#   eval_003: ✓ PASS
#   ...
#   eval_015: ✓ PASS
#
#   EVALUATION RESULTS: 15/15 passed
#   Report saved: eval_report.json

# If any fail:
#   ✗ eval_XXX: FAIL
#   Response: { ... }
#   → Debug and fix module
#   → Re-run test:eval
```

### 3.5 Full Test Suite

```bash
# Run everything in sequence
npm run test:all

# This runs (in order):
#   1. unit tests
#   2. data quality
#   3. server startup
#   4. integration tests
#   5. eval harness (15 questions)
#   6. module 5 isolation check
#   7. Generate coverage report

# Total time: ~3–5 minutes
```

---

## 4. LOCAL DEVELOPMENT SERVER

### 4.1 Start Server

```bash
# Start HTTP server (default port 8787)
npm start

# Logs:
#   Data loaded: 30 POI, 179 menu items, 150 reviews
#   Indices built successfully
#   Server running: http://localhost:8787

# Custom port:
PORT=3000 npm start
```

### 4.2 Test Endpoints Manually

```bash
# Terminal 1: npm start
# Terminal 2: (test endpoints)

# Module 1: Search
curl "http://localhost:8787/v1/search?query=gia%20đình%20bãi%20đỗ&limit=5"

# Module 2: OCR Parse
curl -X POST http://localhost:8787/v1/menu/parse \
  -H "Content-Type: application/json" \
  -d '{
    "rawOcrText": "Pho bo tai .... 80.397 VND",
    "restaurantId": "res001"
  }'

# Module 3: Review Analysis
curl "http://localhost:8787/v1/reviews/analyze?restaurantId=res001"

# Module 4: Quality Score
curl "http://localhost:8787/v1/poi/quality-score?restaurantId=res001"

# Module 5: Corridor Demo
curl "http://localhost:8787/v1/route/rest-stops?corridorId=hanoi-halong&currentProgressKm=80&atHour=12"

# All should return 200 with JSON bodies
```

### 4.3 Debug Mode

```bash
# Enable verbose logging
DEBUG=* npm start

# Shows all module function calls, data lookups, etc.
# Useful for diagnosing issues
```

---

## 5. DEPLOYMENT

### 5.1 Docker Build (Optional)

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --production

COPY data/ ./data/
COPY src/ ./src/

# Pre-build indices
RUN npm run data:load

EXPOSE 8787

CMD ["npm", "start"]
```

```bash
# Build image
docker build -t tasco-food-intelligence .

# Run container
docker run -p 8787:8787 tasco-food-intelligence

# With environment variables (for Module 5 API keys)
docker run -p 8787:8787 \
  -e TASCO_ROUTE_BASE=https://... \
  -e TASCO_GEOCODE_BASE=https://... \
  -e TASCO_BEARER_TOKEN=... \
  tasco-food-intelligence
```

### 5.2 Systemd Service (Linux)

```ini
# /etc/systemd/system/tasco-food-intel.service

[Unit]
Description=Tasco Food Intelligence Service
After=network.target

[Service]
Type=simple
User=tasco
WorkingDirectory=/opt/tasco-food-intelligence
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

Environment="NODE_ENV=production"
Environment="PORT=8787"

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable tasco-food-intel
sudo systemctl start tasco-food-intel

# Check status
sudo systemctl status tasco-food-intel

# Logs
journalctl -u tasco-food-intel -f
```

### 5.3 Environment Configuration

```bash
# .env (or export in shell)

# API keys (for Module 5 only; optional if using cached data)
TASCO_ROUTE_BASE=https://tasco-maps.dnpwater.vn
TASCO_GEOCODE_BASE=https://tasco-maps.dnpwater.vn
TASCO_BEARER_TOKEN=Bearer_token_here
TASCO_API_KEY=api_key_here

# Server config
PORT=8787
NODE_ENV=production

# Caching (Module 5)
TASCO_CACHE=replay          # 'replay' = use cache only, 'refresh' = rebuild cache
```

### 5.4 Health Check Endpoint

```bash
# Add health endpoint for monitoring
curl http://localhost:8787/health

# Response:
# {
#   "status": "ok",
#   "modules": {
#     "search": "ready",
#     "ocr": "ready",
#     "reviews": "ready",
#     "quality": "ready",
#     "corridor": "ready"
#   },
#   "data_loaded": true,
#   "timestamp": "2026-07-11T10:30:00Z"
# }
```

---

## 6. MAINTENANCE & UPDATES

### 6.1 Rebuild Indices

```bash
# If CSV data changes:
npm run data:load

# If you need to rebuild Module 5 corridor cache from scratch:
TASCO_CACHE=refresh npm run build:module5

# Note: Requires network access to Tasco APIs
# If building on air-gapped machine, copy cache from another build
```

### 6.2 Update Dependencies

```bash
# Check for updates
npm outdated

# Update minor versions (safe)
npm update

# Update major versions (may break things)
npm install package@latest

# After updating, re-run tests:
npm test
npm run test:eval
```

### 6.3 Monitoring

```bash
# Check for memory leaks (run under load)
node --inspect src/index.js

# Visit chrome://inspect/ to connect debugger
# Take heap snapshots before/after load test

# Basic load test
npm run load:test

# Expected: <200ms response time, <100MB memory
```

---

## 7. TROUBLESHOOTING

### 7.1 Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Data not loading** | "Cannot read property 'length' of undefined" | Run `npm run data:load` first |
| **Module not found** | "Cannot find module '../lib/module1_engine.js'" | Run `npm run build` first |
| **Port already in use** | "EADDRINUSE: address already in use :::8787" | `PORT=3000 npm start` or `lsof -i :8787; kill -9 PID` |
| **CSV encoding issues** | Garbled Vietnamese characters | Ensure CSVs are UTF-8 BOM (not UTF-16) |
| **Test timeout** | "Jest timeout exceeded 5000ms" | Increase timeout: `npm test -- --testTimeout=10000` |
| **Module 5 cache missing** | "Cannot read property 'gates' of undefined" | Run `npm run build:module5` to rebuild cache |

### 7.2 Debug Checklist

```bash
# 1. Verify Node version
node --version  # v18+

# 2. Check data files exist
ls -la data/*/index_*.json

# 3. Run unit tests
npm test -- tests/lib.test.js  # Test shared kernel first

# 4. Run integration test for specific module
npm run test:integration -- tests/module1.test.js

# 5. Manual endpoint test
curl "http://localhost:8787/v1/search?query=test"

# 6. Check logs
tail -f debug.log  # If DEBUG env var is set
```

### 7.3 Performance Tuning

```bash
# If search is slow (>200ms):
# 1. Check data index size: ls -lah data/POI/index_by_*.json
# 2. Run data:load again (rebuild indices)
# 3. Check if all menu items are indexed: npm run data:validate

# If OCR parsing is slow (>1s):
# 1. Profile: node --prof src/module2.js
# 2. Reduce regex complexity or use lazy evaluation
# 3. Cache parsed results

# Memory profiling:
node --max-old-space-size=4096 src/index.js  # Allocate 4GB RAM
```

---

## 8. DEPLOYMENT CHECKLIST

Before going live, verify:

- [ ] All 15 eval questions pass: `npm run test:eval`
- [ ] No unit test failures: `npm test`
- [ ] Data isolation verified: `npm test -- tests/module5_isolation.test.js`
- [ ] Integration tests pass: `npm run test:integration`
- [ ] Health check endpoint responds
- [ ] Server starts cleanly: `npm start` (no errors)
- [ ] Load test passes: `npm run load:test` (<200ms responses)
- [ ] Log files are rotated or cleaned
- [ ] Environment variables set correctly
- [ ] Backup of CSVs taken
- [ ] Monitoring/alerting configured

```bash
# Final pre-deployment check script
npm run test:all && echo "✓ Ready to deploy"
```

---

## 9. QUICK COMMANDS REFERENCE

```bash
# Setup
npm install
npm run data:load
npm run build

# Development
npm start                     # Start server :8787
npm test                      # Run all unit tests
npm run test:eval             # Run 15 benchmark questions

# Deployment
npm run build                 # Optimize for production
docker build -t tasco .       # Build Docker image
docker run -p 8787:8787 tasco # Run container

# Maintenance
npm run data:load             # Reload CSVs
npm run build:module5         # Rebuild corridor cache
npm outdated                  # Check for updates
npm run test:data             # Verify data integrity

# Debugging
DEBUG=* npm start             # Verbose logging
npm test -- --coverage        # Test coverage report
npm run load:test             # Load testing
```

---

## 10. ARCHITECTURE SUMMARY (For Deployment)

```
Client (Browser / Curl)
       ↓
   HTTP Server (:8787)
       ↓
   ┌───────────────────────────┐
   │    Router                 │
   ├───────────────────────────┤
   │ GET /v1/search            │
   │ POST /v1/menu/parse       │
   │ GET /v1/reviews/analyze   │
   │ GET /v1/poi/quality-score │
   │ GET /v1/route/rest-stops  │
   └───────────────────────────┘
       ↓ (dispatches to)
   ┌─┴────┬─────┬──────┬─────┬──────┐
   │      │     │      │     │      │
  M1    M2    M3     M4    M5  Kernel
Search OCR  Review Quality Corridor (lib/)
   │      │     │      │     │      │
   └─┬────┴─────┴──────┴─────┴──────┘
     ↓
  In-Memory Data Layer
  ├─ POI indices
  ├─ Menu items
  ├─ Reviews
  ├─ Aspects (precomputed)
  └─ Corridor bundle (cached)
```

**No database. Pure in-memory JSON structures. Fast (<100ms per request).**

---

**END OF RUNBOOK**

For questions: See SYSTEM_01–04 for detailed specs.

