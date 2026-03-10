# GreenValue AI — Development Roadmap 2026

> **Last Updated:** March 10, 2026  
> **Architecture:** 7-Layer Enterprise Stack (Zero Cost / Bootstrap)  
> **Hardware Target:** NVIDIA RTX 5070 Ti (Dev) / GTX 1650 Ti (Staging)  
> **Codebase:** ~10,000 LOC Python (AI) + ~5,000 LOC TypeScript (Backend) + ~8,000 LOC TypeScript (Mobile)

---

## Executive Summary

GreenValue AI is a PropTech platform that automates property valuation and energy efficiency analysis through a Scan-to-Value pipeline. This roadmap defines 6 development phases from March 2026 to February 2027, transforming the current advanced prototype into a production-ready enterprise platform.

**What's built:** A fully functional AI engine (YOLO11 vision + physics + 17-file RAG system + IVS report generation), a production-grade NestJS backend (92% complete), and a polished React Native mobile app (85% complete). Three web apps remain empty shells.

---

## RAG Knowledge Library (8 Books)

The RAG system is powered by 8 professionally curated PropTech reference books. Each book maps to a specific **AI Expertise Domain** and is routed by the Semantic Router based on the query context.

| # | Book | AI Expertise Domain | RAG Router Category | Impact on App |
|---|------|---------------------|---------------------|---------------|
| 1 | **IVS-Jan-2025.pdf** | Official Appraisal (Legal / IVS) | `valuation` `legal` | "High Confidence (98%)" badge, legal basis for bank/institutional PDF reports |
| 2 | **The Appraisal of Real Estate, 15th Ed.** | U.S. Real Estate Valuation | `valuation` | 3 appraisal approaches (Cost, Comparable, Income), value calculation text |
| 3 | **Sustainable Home Refurbishment** | Thermal Physics & Energy | `energy` | Energy Performance (A–G) score, Heat Loss / U-Value calculations |
| 4 | **Green Building Illustrated** | Architectural Design & Integration | `retrofit` `sustainability` | "How-to" guides, structural feasibility warnings |
| 5 | **Sustainable Construction** | Materials Science & Life Cycle (LCA) | `sustainability` | Carbon Footprint Reduction metrics, material sustainability reports |
| 6 | **The Book on Flipping Houses** (J. Scott) | Construction / Renovation Costs | `finance` `retrofit` | "Est. Cost ($)" figures on Upgrade Suggestions screen |
| 7 | **What Every Real Estate Investor...** | Financial Modeling (ROI) | `finance` | "Value Gain ($)" and "Payback Years" financial calculations |
| 8 | **REALES.PDF** | Basic Real Estate Concepts | `general` | Glossary of Terms in reports, basic informational texts |

### Multi-Book Chain-of-Thought Example

> **Trigger:** YOLO11 detects an old HVAC unit in a property photo.

```
Step 1 → Physics Engine (Book #3: Sustainable Home Refurbishment)
         "Old HVAC → energy rating D. Needs a new heat pump."

Step 2 → Cost Expert (Book #6: The Book on Flipping Houses)
         "Heat pump installation for this size → Est. $7,500"

Step 3 → Investment Expert (Book #7: What Every Real Estate Investor...)
         "$150/mo savings → $1,800/yr NOI increase"

Step 4 → Appraisal Expert (Book #2: Appraisal of Real Estate + Book #1: IVS)
         "$1,800 NOI ÷ 6% Cap Rate = +$30,000 property value (IVS-compliant)"
```

**Result on Mobile Screen:**
```
┌────────────────────────────────────────┐
│  🔄 Upgrade to Heat Pump              │
│  Cost:      $7,500                     │
│  Value Add: +$30,000                   │
│  ROI:       300%                       │
│  Payback:   4.2 years                  │
│  IVS Basis: Income Approach (6% Cap)   │
└────────────────────────────────────────┘
```

---

## Deep-Dive: Current State Assessment (March 8, 2026)

### Component-Level Status

| Component | Files | LOC | Status | Completion |
|-----------|-------|-----|--------|------------|
| **AI Engine — Vision (YOLO11)** | 2 | 400 | ✅ Production-ready | 100% |
| **AI Engine — Physics (U-Value)** | 1 | 500+ | ✅ Production-ready (EN ISO 6946) | 98% |
| **AI Engine — RAG System** | 17 | 3,000+ | ✅ Advanced (8-book, semantic cache, learning) | 90% |
| **AI Engine — Report Engine** | 8 | 2,000+ | ✅ IVS-2025 compliant (WeasyPrint) | 85% |
| **AI Engine — OCR Module** | 6 | 1,500+ | ✅ Enterprise (4 strategies) | 95% |
| **AI Engine — Graph (Neo4j)** | 4 | 600+ | ✅ Working (schema + property graph) | 80% |
| **AI Engine — gRPC Server** | 3 | 400+ | ✅ Working (8/8 methods) | 90% |
| **AI Engine — Pipeline** | 1 | 200+ | ✅ 5-step orchestration | 95% |
| **AI Engine — Queue Consumer** | 2 | 150 | ✅ BullMQ compatible | 100% |
| **AI Engine — Storage (MinIO)** | 2 | 150 | ✅ S3-compatible | 100% |
| **AI Engine — Config** | 1 | 150 | ✅ All vars used | 100% |
| **AI Engine — FastAPI Endpoints** | 1 | 500+ | ✅ 14 endpoints | 90% |
| **AI Engine — Tests** | 2 | 150 | ⚠️ Physics only | 40% |
| **NestJS Backend — Auth** | 8 | 800+ | ✅ JWT + OAuth stubs + RBAC | 95% |
| **NestJS Backend — Users** | 7 | 400+ | ✅ Full CRUD + admin | 100% |
| **NestJS Backend — Properties** | 4 | 400+ | ✅ CRUD + geolocation | 100% |
| **NestJS Backend — Reports** | 6 | 500+ | ⚠️ BullMQ worker issue | 85% |
| **NestJS Backend — AI Proxy** | 5 | 700+ | ✅ gRPC → HTTP fallback | 90% |
| **NestJS Backend — Audit** | 3 | 300+ | ✅ Immutable trail | 100% |
| **NestJS Backend — WebSocket** | 2 | 200+ | ✅ Real-time, Redis adapter | 95% |
| **NestJS Backend — Health** | 2 | 100+ | ✅ K8s-ready | 100% |
| **NestJS Backend — Metrics** | 4 | 400+ | ✅ Prometheus instrumented | 95% |
| **NestJS Backend — Core Infra** | 8 | 800+ | ✅ Prisma, Redis, BullMQ, Storage | 100% |
| **NestJS Backend — E2E Tests** | 1 | 5 | ❌ Placeholder only | 5% |
| **Mobile App (React Native)** | 50+ | 8,000+ | ✅ Full scan-to-value flow | 85% |
| **Web Consumer App** | 0 | 0 | ❌ Empty directory | 0% |
| **Web Partner Portal** | 0 | 0 | ❌ Empty directory | 0% |
| **Web Admin Dashboard** | 0 | 0 | ❌ Empty directory | 0% |
| **Docker Infrastructure** | 15+ | — | ✅ 14 services defined | 85% |
| **Monitoring (Prometheus/Grafana)** | 6 | — | ⚠️ Configs exist, metrics missing | 60% |
| **Kubernetes** | 0 | 0 | ❌ Empty directory | 0% |

### Critical Issues Discovered (March 8 Deep Audit)

| # | Issue | Severity | Location | Impact |
|---|-------|----------|----------|--------|
| ~~1~~ | ~~**gRPC stubs not generated**~~ | ✅ Fixed | AI Engine | ~~Fixed March 10, 2026~~ |
| ~~2~~ | ~~**Report BullMQ worker**~~ | ✅ Fixed | NestJS `report.module.ts` | ~~Fixed March 10, 2026~~ |
| 3 | **Prisma migration needed** — Report service uses `as any` casts | 🟡 High | NestJS `report.service.ts` | Type safety lost for reportType, language, generationTimeMs |
| 4 | **Auth `resetPassword()` incomplete** — method truncated | 🟡 High | NestJS `auth.service.ts` | Password reset flow broken |
| 5 | **Auth `forgotPassword()` TODO** — email sending not implemented | 🟡 High | NestJS `auth.service.ts` | No password reset emails sent |
| 6 | **Grafana datasources empty** — no Prometheus auto-provisioning | 🟡 High | `monitoring/grafana/datasources/` | Dashboard shows no data |
| 7 | **Prometheus metrics undefined** — alerts reference non-existent metrics | 🟡 High | `alerting_rules.yml` | `greenvalue_up`, `greenvalue_model_loaded` etc. never fire |
| 8 | **Ollama model not pulled** — LLM container starts empty | 🟡 High | `docker-compose.yml` | RAG chain-of-thought fails |
| 9 | **Neo4j `get_graph_context()` incomplete** | 🟡 Medium | `graph/property_graph.py` | Graph-enhanced RAG partially broken |
| 10 | **E2E tests blank** — zero actual test cases | 🟡 Medium | `test/app.e2e-spec.ts` | No integration test coverage |
| 11 | **Alert webhook handler missing** — backend must handle alerts | 🟡 Medium | NestJS `/api/v1/webhooks/alert` | Alertmanager notifications lost |
| 12 | **CORS open to all origins** — `origin: '*'` in production risk | 🟡 Medium | AI Engine + WebSocket | Security vulnerability |
| 13 | **SSL self-signed only** — no Let's Encrypt automation | 🟢 Low | `nginx/generate-ssl.sh` | Not production-ready |
| 14 | **Mobile subscription payments** — "Coming soon!" placeholder | 🟢 Low | Mobile `subscription-plan.tsx` | No monetization |
| 15 | **Mobile investment prefs** — local storage only, no backend sync | 🟢 Low | Mobile `investment-preferences.tsx` | Preferences lost on reinstall |

---

## Phase 1: Foundation Hardening (March 2026) ✅ COMPLETE

**Goal:** Fix critical runtime errors, integrate new OCR + Neo4j modules, stabilize the core pipeline.

### Tasks

- [x] 1.1 Professional OCR module with hi_res strategy (multi-strategy engine)
- [x] 1.2 Neo4j graph database module (schema, client, property graph)
- [x] 1.3 Docker Compose — Neo4j service + environment variables
- [x] 1.4 Fix `RealTimeLearningEngine` / `AdvancedAnalyticsDashboard` references in `rag_pipeline.py`
- [x] 1.5 Integrate OCR module into RAG ingestion pipeline (3-tier strategy: OCR Engine → Unstructured API → PyPDF2)
- [x] 1.6 Integrate Neo4j graph into both RAG pipelines (replace in-memory graph, graceful fallback)
- [x] 1.7 Add Neo4j + OCR API endpoints to `main.py` (7 new endpoints)
- [x] 1.8 Fix Vision-RAG endpoint mismatch (`/analyze/property` → `/api/v1/analyze/upload`)
- [x] 1.9 Create `RealTimeLearningEngine` implementation (`learning.py`)
- [x] 1.10 Create `AdvancedAnalyticsDashboard` implementation (`analytics.py`)
- [x] 1.11 Fix missing `PropTechDomain` import in `rag_pipeline.py`
- [x] 1.12 Add Neo4j + Unstructured API settings to `config/settings.py`

### Deliverables
- ✅ Stable AI Engine with no runtime `NameError`s
- ✅ OCR system with hi_res, Tesseract, hybrid, and fast strategies
- ✅ Neo4j graph with 25+ PropTech concepts, 35+ relationships, 13 materials
- ✅ All API endpoints functional (OCR: 2, Graph: 5, Vision-RAG: 2, RAG: 4, Analysis: 3)

---

## Phase 2: IVS-Compliant Report Generation & Multi-Book RAG Chain (April 2026) ✅ COMPLETE

**Goal:** Build an IVS-2025-compliant PDF report engine, implement multi-book chain-of-thought reasoning, and complete all gRPC service methods. Reports must pass institutional review for banks and appraisal boards.

### 2A: RAG Knowledge Base — 8-Book Expert Library

- [x] 2A.1 Ingest all 8 books into Qdrant with book-aware metadata tagging
  - Each chunk tagged with `book_id`, `book_title`, `expertise_domain`, `book_authority_level`
  - Priority weighting: IVS (authority=1.0), Appraisal of RE (0.95), textbooks (0.85), practical (0.80)
  - CLI script: `scripts/ingest_books.py` with `--force-recreate`, `--verify-only`, `--book`, `--output-json`
- [x] 2A.2 Update `EnhancedSemanticRouter` with book-to-domain mapping + `retrieve_for_books()`
  - Route `valuation` queries → Books #1, #2 (IVS + Appraisal of RE)
  - Route `energy` queries → Book #3 (Sustainable Home Refurbishment)
  - Route `retrofit` queries → Books #4, #6 (Green Building Illustrated + Flipping Houses)
  - Route `sustainability` queries → Books #4, #5 (Green Building + Sustainable Construction)
  - Route `finance` queries → Books #6, #7 (Flipping Houses + RE Investor)
  - Route `legal` queries → Book #1 (IVS-Jan-2025)
  - Route `general` queries → Book #8 (REALES) + all books
  - `store.py`, `retrieval.py`, `rag_pipeline.py`: `book_ids` filter parameter via Qdrant MatchAny
- [x] 2A.3 Implement **Multi-Book Chain-of-Thought** reasoning via **LangGraph Stateful Workflow**
  - Ditched mega-prompting → isolated micro-agents with Pydantic structured JSON outputs
  - LangGraph StateGraph: `physics_agent → cost_agent → finance_agent → appraisal_agent`
  - Context window CLEARED between steps (fresh LLM call each time)
  - Each step receives ONLY: (a) previous step's Pydantic JSON + (b) book-specific RAG context
  - Pydantic models: `PhysicsOutput`, `CostOutput`, `FinanceOutput`, `AppraisalOutput`
  - Sequential fallback when langgraph is not installed (same isolation guarantees)
- [x] 2A.4 Book-specific `TableAwareChunker` enhancements
  - J. Scott cost tables → structured cost estimates with `$/sqft` normalization
  - IVS appendix tables → regulatory reference tables
  - Appraisal of RE → comparable sales grids, adjustment tables
  - RE Investor → Cap Rate tables, NOI worksheets
  - Per-book regex patterns in `book_table_patterns` dict; `detect_table_content(book_id=)` dispatch

### 2B: IVS-2025-Compliant PDF Report Engine

- [x] 2B.1 Create `ReportEngine` module (`modules/report/`)
  - `engine.py` — Main report orchestrator
  - `ivs_template.py` — IVS-2025 compliant report structure
  - `sections.py` — Individual report section generators
  - `charts.py` — Chart and visualization generators
  - `pdf_renderer.py` — **WeasyPrint** (HTML/CSS → PDF) — replaced ReportLab
  - `chain_of_thought.py` — **LangGraph** stateful workflow + Pydantic structured outputs
  - `templates/report.html` — Jinja2 + Tailwind CSS report template (edit HTML = change design)
- [x] 2B.2 IVS-2025 Report Structure (per IVS-Jan-2025.pdf standard)
  - **Cover Page**: Property photo, address, report date, valuation date, appraiser
  - **Section 1 — Scope of Work**: Purpose, intended use, type of value (Market Value per IVS 104)
  - **Section 2 — Property Description**: Location, zoning, physical characteristics, improvements
  - **Section 3 — Market Analysis**: Local market conditions, comparable data, comparable property table, market indicators (median €/m², YoY trend, days-on-market, inventory level, energy premium)
  - **Section 4 — Valuation Approaches**:
    - 4a. Cost Approach (Book #2 methodology)
    - 4b. Sales Comparison Approach (Book #2 comparable adjustments)
    - 4c. Income Approach (Book #7 Cap Rate / NOI / DCF)
  - **Section 5 — Energy & Sustainability Assessment** (GreenValue AI unique):
    - Energy label (A–G) from YOLO11 + Physics Engine
    - Component detection table (windows, roof, facade, insulation) with U-values
    - Thermal heatmap overlay
    - Carbon footprint estimate (Book #5 LCA data)
  - **Section 6 — Renovation Impact Analysis** (GreenValue AI unique):
    - Upgrade recommendations with cost estimates (Book #6)
    - ROI analysis per upgrade (Book #7)
    - Before/After energy label projection
    - Payback period calculations
    - Aggregate value impact (IVS Income Approach)
  - **Section 7 — Reconciliation & Final Value Opinion**
  - **Section 8 — Assumptions & Limiting Conditions** (IVS 101/102 compliance)
  - **Appendix A**: YOLO11 detection results (annotated image)
  - **Appendix B**: Detailed financial calculations
  - **Appendix C**: Glossary of Terms (Book #8)
  - **Appendix D**: Data sources & book citations
  - **Data Models**: `ComparableProperty`, `MarketAnalysis` dataclasses in `ivs_template.py`
  - **Engine**: `_populate_market()` wired into both `generate()` and `generate_json()` flows
- [x] 2B.3 Chart & visualization generation (7 charts)
  - Energy label gauge (A+ through G, color-coded) — `energy_gauge()`
  - Before/After comparison bars (3-panel: label rank, heat loss, carbon) — `before_after_comparison()`
  - ROI waterfall chart — `roi_waterfall()`
  - Cost breakdown pie chart — `cost_breakdown_pie()`
  - U-value comparison (current vs target per component) — `u_value_comparison()`
  - Thermal heatmap overlay on property photo — `heatmap_overlay()`
  - Cap Rate sensitivity bar chart — `cap_rate_sensitivity()`
  - All 7 wired in `engine.py._generate_charts()`, rendered in `report.html`
- [x] 2B.4 Multi-language support (EN, TR, DE) via `translations.py` i18n module
  - ~200 translation keys for all section labels, table headers, disclaimers
  - Full glossary in EN/TR/DE (16 terms)
  - All 13 section methods in `sections.py` use `t(key, lang)` pattern
- [x] 2B.5 PDF styling via HTML/CSS: Professional typography, GreenValue branding
  - `templates/report.html` — full Jinja2 template with green-branded CSS
  - To change design: edit the HTML template, zero Python changes needed
  - WeasyPrint renders HTML/CSS faithfully to PDF (A4, @page rules, page breaks)

### 2C: gRPC Service Completion

- [x] 2C.1 Implement `GenerateReport` gRPC method
  - Input: property_id, report_type (full_ivs, summary, energy_only)
  - Output: PDF bytes + presigned RustFS URL
  - Calls `ReportEngine.generate()`, uploads to MinIO/RustFS, returns key
- [x] 2C.2 Implement `FindSimilarProperties` gRPC method (Qdrant similarity)
  - Embedding similarity via RAG pipeline `similarity_search()`
  - Returns `SimilarProperty` with property_id, score, energy_label
- [x] 2C.3 Implement `GetPropertyGraph` gRPC method
  - Returns knowledge graph relations + ripple effects + related factors
  - Uses `KnowledgeGraph` + `PropertyGraph` from `rag/graph.py`
  - Proto: `GetPropertyGraphRequest/Response` with `GraphRelation`, `RippleEffect` messages
- [x] 2C.4 Implement `ChainOfThoughtAnalysis` gRPC method
  - Runs the multi-book chain for detected components via `ChainOfThoughtEngine`
  - Returns structured: upgrades, step_logs, total_cost, total_value_add, aggregate_roi
  - Proto: `ChainOfThoughtRequest/Response` with `UpgradeRecommendation`, `StepLog` messages

### 2D: Backend Integration

- [x] 2D.1 NestJS `ReportModule` with full CRUD + generate endpoints
  - POST `/api/v1/reports` — trigger report generation (enqueues BullMQ job)
  - GET `/api/v1/reports` — list my reports
  - GET `/api/v1/reports/:id` — get report details + presigned download URL
  - GET `/api/v1/reports/:id/preview` — JSON preview with analysis data + chain-of-thought log
  - GET `/api/v1/reports/property/:propertyId` — list reports for property
  - DELETE `/api/v1/reports/:id` — delete report + storage file
- [x] 2D.2 Report storage in RustFS (`pdf-reports` bucket) with presigned URLs
  - `ReportService` uses `StorageService.getPresignedDownloadUrl()` for downloads
  - Storage cleanup on report deletion
- [x] 2D.3 Report generation queue (BullMQ `reports` queue)
  - `ReportModule.onModuleInit()` registers worker via `QueueService.registerWorker()`
  - Worker calls `ReportService.processReportJob()` → AI proxy → storage
- [x] 2D.4 Prisma `Report` model extended
  - Added `ReportType` enum (ENERGY_CERTIFICATE, ROI_ANALYSIS, COMPARISON, FULL_IVS)
  - Added fields: `reportType`, `language`, `generationTimeMs`, `ivsComplianceWarnings`, `chainOfThoughtLog`
- [x] 2D.5 JSON report format option
  - Python: `ReportEngine.generate_json()` — returns structured sections dict
  - FastAPI: `POST /api/v1/report/generate/json` endpoint
  - NestJS: format field in `GenerateReportDto` supports `PDF` | `JSON`

### Deliverables
- ✅ IVS-2025-compliant professional PDF reports (WeasyPrint HTML/CSS → PDF)
- ✅ Multi-book chain-of-thought reasoning (Physics → Cost → Finance → Appraisal) via LangGraph
- ✅ 8-book RAG library with book-aware routing, authority weighting, and `retrieve_for_books()` API
- ✅ CLI book ingestion script (`scripts/ingest_books.py`) with per-book metadata tagging
- ✅ Complete 8/8 gRPC methods (AnalyzeImage, GetAnalysisStatus, CalculateUValue, GenerateReport, FindSimilarProperties, GetPropertyGraph, ChainOfThoughtAnalysis, HealthCheck)
- ✅ Multi-language support (EN/TR/DE) — 200+ translation keys, all 13 report sections
- ✅ NestJS ReportModule with CRUD endpoints + BullMQ queue + RustFS storage
- ✅ JSON report format option alongside PDF
- ✅ Prisma Report model with ReportType enum and generation metadata

---

## Phase 2.5: Bug Fixes & Integration Stabilization (March 2026) — 🔶 IN PROGRESS

**Goal:** Fix all critical and high-severity issues found during the March 8 deep audit. Zero blockers before frontend development begins.

### 2.5A: Critical Fixes (Blocking)

- [x] 2.5A.1 **Generate gRPC Python stubs** — ✅ Fixed March 10, 2026
  - gRPC stubs compiled and verified
- [x] 2.5A.2 **Fix Report BullMQ worker** — ✅ Fixed March 10, 2026
  - Worker registration implemented and verified
- [ ] 2.5A.3 **Run Prisma migration** — `npx prisma migrate dev && npx prisma generate`
  - Remove all `as any` casts in `report.service.ts` for `reportType`, `language`, `generationTimeMs`
  - Verify: TypeScript compiles without `as any` in report module

### 2.5B: High-Priority Fixes

- [ ] 2.5B.1 **Complete `resetPassword()` in `auth.service.ts`** — method is truncated/incomplete
  - Implement: validate reset token → hash new password → update user → invalidate token
- [ ] 2.5B.2 **Implement password reset email** — `forgotPassword()` has TODO for email sending
  - Use `nodemailer` (already in dependencies) + `handlebars` templates
  - Store reset tokens in Redis with 1-hour TTL
- [ ] 2.5B.3 **Fix Grafana datasource auto-provisioning** — `monitoring/grafana/datasources/` is empty
  - Create `datasources.yml` with Prometheus connection (`http://prometheus:9090`)
- [ ] 2.5B.4 **Export missing Prometheus metrics from AI Engine**
  - Add to `main.py`: `greenvalue_up`, `greenvalue_model_loaded`, `greenvalue_uptime_seconds`, `greenvalue_jobs_completed_total`
  - These are referenced by `alerting_rules.yml` and `greenvalue-dashboard.json`
- [ ] 2.5B.5 **Pull Ollama model on startup** — container starts empty
  - Add `ollama pull llama3.2:3b` to entrypoint or docker-compose healthcheck
  - Without model, chain-of-thought reasoning and RAG LLM calls fail
- [ ] 2.5B.6 **Complete Neo4j `get_graph_context()` method** in `graph/property_graph.py`
  - Currently truncated — needs Cypher queries for context extraction
  - RAG pipeline falls back to in-memory graph without this

### 2.5C: Medium-Priority Fixes

- [ ] 2.5C.1 **Implement alert webhook handler** — NestJS needs `POST /api/v1/webhooks/alert`
  - Alertmanager sends alerts to `http://backend:3000/api/v1/webhooks/alert`
  - Log to audit table + emit WebSocket event
- [ ] 2.5C.2 **Restrict CORS origins** — both AI Engine and WebSocket use `origin: '*'`
  - Set allowed origins from environment variable (e.g., `CORS_ORIGINS=http://localhost:3001,http://localhost:3002`)
- [ ] 2.5C.3 **Add AI Engine test coverage** — only Physics tests exist
  - Add tests for: Vision inference, pipeline orchestration, RAG query, report generation
  - Target: 60% coverage (from current ~15%)
- [ ] 2.5C.4 **Add NestJS E2E tests** — currently blank placeholder
  - Auth flow tests (register → login → me → logout)
  - Property CRUD tests
  - Analysis submission + status polling
  - Target: cover all critical paths d
- [ ] 2.5C.5 **Fix docker-compose inconsistency** — `greenvalue-be/docker-compose.dev.yml` uses MinIO, root uses RustFS
  - Align dev compose to use RustFS or document the difference

### Deliverables
- Zero `as any` casts in TypeScript
- Working end-to-end report generation pipeline
- Password reset flow functional
- Monitoring stack producing real data
- gRPC stubs compiled and verified

---

## Phase 3: Frontend Applications & Mobile Polish (April – June 2026)

**Goal:** Build all three web applications and polish the mobile app's remaining gaps.

### 3A: Consumer Web App — `greenvalue-consumer/` (April 2026)
**Stack:** Next.js 14 + Tailwind CSS + shadcn/ui + TanStack Query + Zustand

- [ ] 3A.1 Next.js 14 project setup with Tailwind CSS + shadcn/ui design system
- [ ] 3A.2 Auth pages (register, login, forgot password, Google/GitHub OAuth redirects)
- [ ] 3A.3 Dashboard — portfolio overview, total properties, recent analyses, energy score distribution
- [ ] 3A.4 Property list with search + filters (city, energy label, building type, date range)
- [ ] 3A.5 Property detail page (photo gallery, heatmap overlay, energy label, component breakdown, U-values)
- [ ] 3A.6 Upload photo & request analysis (drag-and-drop, real-time WebSocket progress bar)
- [ ] 3A.7 Report viewer (rendered PDF preview) + download button
- [ ] 3A.8 "Homes Like This" similarity view — Qdrant-powered property comparison cards
- [ ] 3A.9 RAG chat interface — property Q&A with source citations
- [ ] 3A.10 Interactive map explorer (React-Leaflet + OSM, property markers, clustering, filters)
- [ ] 3A.11 User profile & settings (personal info, change password, notification preferences)
- [ ] 3A.12 Responsive design (desktop + tablet breakpoints)

### 3B: Admin Dashboard — `greenvalue-admin/` (May 2026)
**Stack:** Next.js 14 + Tailwind CSS + shadcn/ui + Recharts

- [ ] 3B.1 Next.js 14 project setup + Admin auth (JWT with ADMIN role enforcement)
- [ ] 3B.2 Dashboard overview — total users, properties, analyses, reports (real-time counters)
- [ ] 3B.3 User management — list, search, filter, ban/unban, role change (OWNER/CONTRACTOR/ADMIN)
- [ ] 3B.4 Property management — CRUD, search, map view, ownership transfer
- [ ] 3B.5 Analysis monitoring — active jobs, queue depth, GPU usage, inference times (live)
- [ ] 3B.6 Knowledge base management — book list, ingest new PDF, delete, chunk stats per book
- [ ] 3B.7 System health dashboard — Neo4j, Qdrant, Redis, RustFS, Ollama service status
- [ ] 3B.8 Grafana embed — `<iframe>` embedded monitoring dashboards
- [ ] 3B.9 Audit log viewer — searchable, filterable, exportable (CSV)
- [ ] 3B.10 Report management — list all reports, view compliance warnings, re-generate

### 3C: Partner Portal — `greenvalue-partner/` (June 2026)
**Stack:** Next.js 14 + Tailwind CSS + shadcn/ui

- [ ] 3C.1 Portal for contractors / energy auditors / B2B partners
- [ ] 3C.2 Batch property analysis — CSV upload → multi-property job queue
- [ ] 3C.3 Renovation cost calculator — interactive tool using Book #6 data
- [ ] 3C.4 Client property sharing — share analysis results with property owners
- [ ] 3C.5 Competitive analysis dashboard — market comparison by region
- [ ] 3C.6 API key management — generate, revoke, rate-limit partner API keys
- [ ] 3C.7 White-label report branding — custom logo, colors, disclaimers per partner

### 3D: Mobile App Final Polish (Ongoing)

- [x] 3D.1 Camera integration (photo capture + HEIF support) ✅
- [x] 3D.2 Real-time analysis progress (WebSocket + polling fallback) ✅
- [x] 3D.3 Offline mode (SQLite cache, background sync, PENDING tracking) ✅
- [x] 3D.4 Map view with property pins (OSM, clustering, filters, geocoding) ✅
- [x] 3D.5 Full scan-to-value wizard (5-step: capture → upload → processing → validation → results) ✅
- [x] 3D.6 Report generation & download from mobile ✅
- [x] 3D.7 Notification center with deep links ✅
- [x] 3D.8 Profile settings (personal info, security, environmental impact) ✅
- [ ] 3D.9 Sync investment preferences to backend (currently local-only via SecureStore)
- [ ] 3D.10 Payment integration for subscription plans (Stripe/RevenueCat)
- [ ] 3D.11 Biometric authentication (Face ID / fingerprint)
- [ ] 3D.12 Push notification integration (Expo Notifications → backend triggers)
- [ ] 3D.13 Clean up legacy Expo starter files (`components/hello-wave.tsx`, `modal.tsx`, etc.)
- [ ] 3D.14 Feature folder modules — move screen logic into `src/features/` (currently empty folders)

### Deliverables
- 3 fully functional web apps with shared design system
- Mobile app at 95%+ completion
- WebSocket integration for live updates across all clients
- Responsive design (mobile-first for consumer, desktop-first for admin/partner)

---

## Phase 4: Intelligence & Optimization (July – September 2026)

**Goal:** Enhance AI capabilities, MLflow integration, performance optimization, and testing.

### 4A: AI Model Enhancement

- [ ] 4A.1 Custom YOLO11 training pipeline for Turkish building stock
  - Collect & annotate 2,000+ Turkish building images
  - Fine-tune YOLO11m-seg on local architecture (Ottoman, Art Deco, Modern Turkish)
  - MLflow experiment tracking for training runs
- [ ] 4A.2 MLflow experiment tracking integration
  - Training run logging (loss, mAP, precision, recall)
  - Model versioning (YOLO weights auto-registered)
  - A/B testing framework (compare model versions on same test set)
- [ ] 4A.3 GPU optimization — TensorRT & ONNX export
  - Export YOLO11m to TensorRT FP16 for RTX 5070 Ti
  - ONNX Runtime fallback for non-NVIDIA GPUs
  - Target: 30% faster inference (2s → 1.4s)

### 4B: Advanced RAG Features

- [ ] 4B.1 Multi-modal embeddings (CLIP for image-text matching)
  - Property photos → visual embeddings in Qdrant
  - Text queries match both text chunks AND similar property images
- [ ] 4B.2 Graph-RAG (Neo4j traversal-enhanced retrieval)
  - Cypher queries find related concepts before vector search
  - Graph context injected into RAG prompt for richer answers
- [ ] 4B.3 Agentic RAG with tool use
  - LLM can call tools: `calculate_u_value()`, `find_similar()`, `get_market_data()`
  - Multi-step reasoning without predefined chains

### 4C: Performance & Quality

- [ ] 4C.1 Caching optimization — Redis + semantic cache tuning
  - Tune semantic similarity threshold (0.95 → measure optimal)
  - Redis cache warming from popular queries
  - Cache hit rate target: >40%
- [ ] 4C.2 Batch processing pipeline — CSV upload → multi-property analysis
  - Partner portal uploads CSV with property addresses
  - BullMQ bulk job creation with progress tracking
- [ ] 4C.3 Energy certificate generation (EU EPC format)
  - Generate official-looking EPC documents
  - Country-specific templates (UK, DE, NL, TR)
- [ ] 4C.4 Load testing & performance benchmarks
  - k6/Locust scripts for API endpoints
  - Baseline benchmarks: inference time, RAG response, report generation
  - Target: 25 concurrent users on single node

### 4D: Test Coverage

- [ ] 4D.1 AI Engine unit tests — target 70% coverage
  - Vision inference mock tests
  - RAG pipeline integration tests (with test Qdrant collection)
  - Report engine output validation
  - Chain-of-thought step verification
- [ ] 4D.2 NestJS E2E test suite — target 80% endpoint coverage
  - Auth flow (register → login → me → refresh → logout)
  - Property CRUD lifecycle
  - Analysis submission → status poll → result
  - Report generation → download → delete
  - WebSocket connection + event subscription
- [ ] 4D.3 Mobile E2E tests (Detox or Maestro)
  - Login → dashboard → scan → results flow
  - Offline mode (airplane mode toggle)
  - Report generation from mobile

### Deliverables
- Fine-tuned YOLO11 for Turkish buildings
- MLflow model registry with versioned weights
- 30% faster inference via TensorRT
- Graph-RAG with Neo4j traversal
- 70%+ test coverage across all layers
- Production performance benchmarks

---

## Phase 4.5: Green Mortgage & Bank Integration (September – October 2026) — 📋 PLANNED

**Goal:** Implement a comprehensive Green Mortgage module that enables the mobile app and platform to calculate bank-specific green mortgage eligibility, interest rate discounts, LTV ratios, and financial benefits based on a property's energy performance. This feature makes GreenValue AI directly actionable for homebuyers, banks, and mortgage brokers.

### Research Context

Green mortgages (also known as Energy Efficient Mortgages / EEM) offer preferential loan terms for energy-efficient properties. Banks worldwide are adopting these products to comply with EU Taxonomy, TCFD reporting, and national sustainability regulations. GreenValue AI's existing energy analysis pipeline (YOLO11 → Physics Engine → EPC label) provides the exact data these banks require.

### 4.5A: Green Mortgage Rule Engine (Backend + AI Engine)

- [ ] 4.5A.1 **Design Green Mortgage data model** — Prisma schema for bank rules
  - `GreenMortgageBank` — bank info, country, active status
  - `MortgageProduct` — product name, base rate, green discount, min/max LTV, eligibility criteria
  - `LTVMatrix` — energy_class (A–G), max_ltv_percent, interest_discount_bps, cashback_percent
  - `CertificationRequirement` — required certifications per bank (EPC, EKB, BREEAM, LEED)
  - `DocumentRequirement` — required documents per product (EPC certificate, energy audit, renovation plan)

- [ ] 4.5A.2 **Implement bank rule configurations** — seed data for 10+ banks
  - **Turkish Banks (BDDK regulated):**
    - Garanti BBVA — up to 0.50% rate discount for A/B labels, 5% higher LTV for A-class, EKB certificate required
    - İş Bankası — "Green Mortgage" product, 0.25–0.75% discount tiered by label, renovation loan bundle
    - Yapı Kredi — 0.30% discount for B+ labels, combo with energy efficiency loan
    - TSKB (Industrial Development Bank) — specialized green building finance, BREEAM/LEED eligible, project-level LTV up to 85%
  - **European Banks (EU Taxonomy / EED compliant):**
    - HSBC — Energy Efficient Mortgage (EEM), 0.10–0.25% discount for EPC A/B, Green Home Fund cashback up to £2,000
    - BNP Paribas — "Crédit Immobilier Vert", DPE A/B required, 0.10% discount, +€5,000 renovation top-up
    - ING — "Groen Hypotheek", energy label A/B/C eligible, 0.20% discount, €25,000 extra for renovations
    - Barclays — Green Home Mortgage, EPC A/B, cashback £500–£2,000, 5% LTV uplift
  - **US Banks (Fannie Mae / Freddie Mac compliant):**
    - Fannie Mae — HomeStyle Energy, up to $3,500 energy report incentive, 97% LTV with energy improvements
    - Chase — Green Mortgage pilot, ENERGY STAR certified, 0.125% rate reduction

- [ ] 4.5A.3 **BDDK LTV matrix implementation** (Turkish regulatory framework)
  - Energy Class A → Max LTV 80%, base rate - 0.50%
  - Energy Class B → Max LTV 75%, base rate - 0.25%
  - Energy Class C → Max LTV 70%, standard rate
  - Energy Class D → Max LTV 65%, standard rate
  - Energy Class E → Max LTV 60%, rate + 0.25% surcharge
  - Energy Class F–G → Max LTV 50%, rate + 0.50% surcharge, renovation plan required
  - Store as configurable matrix (BDDK regulations may change)

- [ ] 4.5A.4 **Carbon intensity formula integration**
  - Linear regression formula: `y = -0.8387x + 1719.4` (CO₂ kg/m²/year vs year of decarbonization)
  - Map property's carbon intensity to Paris Agreement trajectory
  - Calculate "years ahead/behind" the 2050 net-zero target
  - Feed into bank eligibility calculations (some banks require trajectory alignment)

- [ ] 4.5A.5 **NestJS Green Mortgage module** — new endpoints
  - `POST /api/v1/mortgage/eligibility` — calculate eligibility for all banks given property data
  - `GET /api/v1/mortgage/banks` — list all supported banks with green mortgage products
  - `GET /api/v1/mortgage/banks/:bankId/products` — get products for specific bank
  - `POST /api/v1/mortgage/compare` — compare multiple banks side-by-side for a property
  - `GET /api/v1/mortgage/ltv-matrix/:country` — get LTV matrix by country
  - `POST /api/v1/mortgage/calculate` — full mortgage calculation (monthly payment, total interest, savings)
  - `GET /api/v1/mortgage/documents/:bankId/:productId` — required documents checklist

- [ ] 4.5A.6 **Green mortgage calculation engine** (AI Engine Python module)
  - Input: energy_class, property_value, loan_amount, property_area_m2, country, building_year
  - Calculate per-bank: eligible products, adjusted LTV, adjusted interest rate, monthly payment delta
  - Calculate financial benefits: lifetime interest savings, cashback, renovation budget unlocked
  - Calculate environmental benefits: carbon savings projection, energy cost savings/year
  - Output: ranked list of bank products by total financial benefit

### 4.5B: Certification & Standards Integration

- [ ] 4.5B.1 **EPC / EKB certificate mapping**
  - Map GreenValue AI energy label (A–G) to official EPC/EKB certificate equivalents
  - Turkish EKB (Enerji Kimlik Belgesi) — map to A–G scale, validate against TEİAŞ standards
  - EU EPC (Energy Performance Certificate) — map to country-specific scales (UK SAP, DE EnEV, NL NTA 8800)
  - Store certificate metadata: issue date, validity period (10 years), issuing authority
  - Disclaimer: GreenValue AI provides an estimate, official EKB/EPC requires certified assessor

- [ ] 4.5B.2 **BREEAM scoring integration**
  - Map detected building features to BREEAM categories: Energy, Water, Materials, Waste, Pollution
  - Calculate estimated BREEAM score based on YOLO11 detections + physics analysis
  - BREEAM levels: Pass (≥30%), Good (≥45%), Very Good (≥55%), Excellent (≥70%), Outstanding (≥85%)
  - Required by: TSKB, some EU institutional lenders

- [ ] 4.5B.3 **LEED scoring integration**
  - Map features to LEED v4.1 categories: Energy & Atmosphere, Materials, Indoor Environment
  - LEED levels: Certified (40–49), Silver (50–59), Gold (60–79), Platinum (80+)
  - US market relevance: Fannie Mae, Chase preference for LEED-certified properties

- [ ] 4.5B.4 **Turkish-specific regulatory compliance**
  - BDDK (Banking Regulation and Supervision Agency) green lending guidelines
  - SPK (Capital Markets Board) green bond framework alignment
  - EPDK (Energy Market Regulatory Authority) energy efficiency targets
  - Map regulatory requirements to data GreenValue AI already collects

### 4.5C: RAG Knowledge Base Update

- [ ] 4.5C.1 **Ingest green mortgage reference documents** into Qdrant
  - Bank product brochures and term sheets
  - BDDK green lending circulars
  - EU Taxonomy technical screening criteria for buildings
  - EEM (Energy Efficient Mortgage) Action Plan documents
  - Route to new `mortgage` domain in `EnhancedSemanticRouter`

- [ ] 4.5C.2 **Add Book #9: Green Mortgage & Sustainable Finance reference**
  - Curate or compile green mortgage regulations, bank product rules
  - AI Expertise Domain: `mortgage` `finance` `regulation`
  - Authority level: 0.90 (regulatory reference)

- [ ] 4.5C.3 **Update Chain-of-Thought pipeline** — add Mortgage Agent step
  - Extended chain: `physics_agent → cost_agent → finance_agent → mortgage_agent → appraisal_agent`
  - Mortgage agent receives: energy class, property value, country → produces bank eligibility analysis
  - Pydantic model: `MortgageOutput(eligible_banks, best_rate, max_ltv, total_savings, required_docs)`

### 4.5D: Mobile App — Green Mortgage Screens

- [ ] 4.5D.1 **Mortgage Eligibility Screen** — post-analysis result screen
  - Show after energy analysis completes (new tab in results view)
  - Eligible banks listed with green checkmarks, ineligible greyed out with reason
  - Per-bank card: logo, product name, rate discount, max LTV, estimated monthly saving
  - "Best Deal" badge on top-ranked bank product

- [ ] 4.5D.2 **Bank Comparison Screen** — side-by-side comparison
  - Select 2–3 banks to compare
  - Comparison table: interest rate, LTV, total interest paid, monthly payment, cashback, requirements
  - Bar chart visualization of total cost over 15/20/25/30 year terms
  - Share comparison as image or PDF

- [ ] 4.5D.3 **Mortgage Calculator Screen** — interactive tool
  - Inputs: property value, down payment, loan term, energy class (auto-filled from analysis)
  - Outputs: monthly payment (standard vs green), total interest savings, cashback amount
  - Amortization schedule with green savings highlighted
  - "Green Premium": how much the energy label adds to mortgage affordability

- [ ] 4.5D.4 **Document Checklist Screen** — per-bank requirements
  - Checklist of required documents for selected bank product
  - Upload/attach document capability (link to existing storage)
  - Status tracking: required, uploaded, verified, expired
  - Items: EPC/EKB certificate, energy audit report, renovation plan, property valuation, income proof

- [ ] 4.5D.5 **Green Mortgage section in IVS Report**
  - New Section 9 in IVS report: "Green Mortgage Eligibility Analysis"
  - Table of eligible banks with terms
  - Financial benefit summary (lifetime savings)
  - Required certifications status
  - Carbon trajectory alignment chart

### 4.5E: Report Engine Enhancement

- [ ] 4.5E.1 **Add Section 9: Green Mortgage Eligibility** to report template
  - Eligible banks table with product details
  - LTV comparison chart (standard vs green by energy class)
  - Financial savings projection (10/15/20/25/30 year horizons)
  - Required documents checklist with status

- [ ] 4.5E.2 **Mortgage-specific charts** (add to `charts.py`)
  - `mortgage_savings_comparison()` — bar chart of annual savings per bank
  - `ltv_energy_matrix()` — heatmap of LTV % by energy class × bank
  - `carbon_trajectory()` — line chart showing property vs Paris Agreement 2050 target
  - `green_premium_waterfall()` — waterfall showing value uplift from energy improvements → mortgage benefit

- [ ] 4.5E.3 **Multi-language mortgage translations** (EN, TR, DE)
  - Add ~100 new translation keys for mortgage-related section labels, table headers, disclaimers
  - Bank-specific legal disclaimers per country

### Deliverables
- Green Mortgage rule engine with 10+ banks (4 Turkish, 4 European, 2 US)
- BDDK LTV matrix with energy-class-based tiering
- EPC/EKB, BREEAM, LEED certification mapping
- Carbon intensity trajectory calculation (Paris Agreement alignment)
- 7 new API endpoints for mortgage eligibility, comparison, and calculation
- 5 new mobile app screens (eligibility, comparison, calculator, docs, report section)
- RAG knowledge base expanded with mortgage domain (Book #9)
- Extended Chain-of-Thought with Mortgage Agent step
- 4 new report charts + Section 9 in IVS report
- Multi-language support for all mortgage content

---

## Phase 5: Production Hardening (October – December 2026)

**Goal:** Security hardening, observability, and production readiness.

### 5A: Security

- [ ] 5A.1 OAuth2 completion (Google, GitHub, Apple)
  - Mobile: deep link redirect flow
  - Web: popup/redirect flow
  - Apple Sign-In (required for iOS App Store)
- [ ] 5A.2 Email verification on registration
  - Verification link with 24-hour TTL
  - Resend verification endpoint
- [ ] 5A.3 Rate limiting per user (Redis-based, configurable per role)
- [ ] 5A.4 RBAC refinement — property-level permissions (owner, collaborator, viewer)
- [ ] 5A.5 API key management for partners (generate, revoke, rate-limit, scope)
- [ ] 5A.6 Let's Encrypt SSL automation (Certbot + auto-renewal)
- [ ] 5A.7 Security audit — OWASP Top 10 review
  - SQL injection (Prisma ORM protects, verify raw queries)
  - XSS (React/Next.js protects, verify dangerouslySetInnerHTML)
  - CORS (restrict origins per environment)
  - File upload validation (image type, size, EXIF stripping)

### 5B: Observability

- [ ] 5B.1 Distributed tracing (OpenTelemetry)
  - Trace: Mobile → NestJS → gRPC → AI Engine → LLM → response
  - Jaeger or Tempo for trace storage
- [ ] 5B.2 Custom Grafana dashboards (wired to real metrics)
  - AI Engine dashboard (inference time, GPU usage, model status)
  - Backend dashboard (request rate, error rate, response time)
  - Business dashboard (analyses/day, reports/day, user growth)
- [ ] 5B.3 Alertmanager rules refined
  - Fix all undefined metrics (replace `greenvalue_up` with actual exported metrics)
  - Slack/Discord webhook integration for alerts
- [ ] 5B.4 Log aggregation (Loki + promtail)
  - Structured JSON logs from all services
  - Grafana log viewer with query language
- [ ] 5B.5 SLA monitoring dashboard (uptime, latency P50/P95/P99)

### 5C: Data Pipeline

- [ ] 5C.1 Automated knowledge base updates
  - Scheduled ingestion of new PDFs dropped into `/knowledge_base/books/`
  - Re-indexing with version tracking
- [ ] 5C.2 Property data ETL from public sources
  - Turkish TKGM land registry (web scraping)
  - OpenStreetMap building data import
  - EU Energy Performance Certificate databases
- [ ] 5C.3 Nightly Neo4j graph refresh
  - Aggregate property analysis data into graph nodes
  - Compute regional market trends

### Deliverables
- Complete OAuth2 flow (Google, GitHub, Apple)
- Let's Encrypt production SSL
- Full observability stack (traces, logs, metrics, alerts)
- Automated knowledge base pipeline
- Security audit report

---

## Phase 6: Scale & Launch (January – February 2027)

**Goal:** Kubernetes deployment, horizontal scaling, and public launch.

### 6A: Kubernetes Migration

- [ ] 6A.1 Kubernetes manifests (populate `k8s/` directory)
  - Deployments for all services (NestJS, AI Engine, Nginx)
  - StatefulSets for databases (PostgreSQL, Neo4j, Qdrant, Redis)
  - ConfigMaps + Secrets for all environment variables
- [ ] 6A.2 Helm charts for deployment automation
- [ ] 6A.3 HPA (Horizontal Pod Autoscaler) for AI engine
  - Scale on GPU utilization + request queue depth
  - Min: 1 pod, Max: 4 pods
- [ ] 6A.4 GPU node pools (NVIDIA device plugin)
- [ ] 6A.5 PersistentVolumeClaims for database storage

### 6B: CI/CD

- [ ] 6B.1 GitHub Actions pipeline
  - Lint (ESLint + Pylint) → Test → Build → Push Docker images
  - Automated database migrations on deploy
  - Branch protection rules
- [ ] 6B.2 Docker image registry (GitHub Container Registry / Harbor)
- [ ] 6B.3 Zero-downtime deployments (rolling update strategy)
- [ ] 6B.4 Preview environments (PR-based)

### 6C: Scale & Launch

- [ ] 6C.1 Multi-tenancy (region/organization isolation)
- [ ] 6C.2 API documentation (OpenAPI 3.1 + developer portal)
- [ ] 6C.3 Load testing (k6/Locust → 1000 concurrent users target)
- [ ] 6C.4 Disaster recovery (backup strategy, failover, RTO < 4h, RPO < 1h)
- [ ] 6C.5 Beta program — 50 early users, feedback collection
- [ ] 6C.6 App Store submission (iOS + Google Play)
- [ ] 6C.7 Landing page + documentation site

### Deliverables
- Production-ready Kubernetes deployment
- Complete CI/CD pipeline
- 1000+ concurrent users support
- Public API documentation
- App Store presence
- Beta program launched

---

## Timeline Summary

| Phase | Period | Focus | Status |
|-------|--------|-------|--------|
| **Phase 1** | March 2026 | Foundation Hardening (OCR, Neo4j, Bug Fixes) | ✅ COMPLETE |
| **Phase 2** | March 2026 | IVS-Compliant Reports, Multi-Book RAG Chain, gRPC | ✅ COMPLETE |
| **Phase 2.5** | March 2026 | Bug Fixes & Integration Stabilization | 🔶 IN PROGRESS |
| **Phase 3** | Apr–Jun 2026 | Frontend Applications (Consumer, Admin, Partner) + Mobile Polish | ⏭️ NEXT |
| **Phase 4** | Jul–Sep 2026 | Intelligence & Optimization (MLflow, Graph-RAG, Testing) | ⏭️ PLANNED |
| **Phase 4.5** | Sep–Oct 2026 | Green Mortgage & Bank Integration (10+ banks, LTV, EPC) | 📋 PLANNED |
| **Phase 5** | Oct–Dec 2026 | Production Hardening (Security, Observability, Data Pipeline) | ⏭️ PLANNED |
| **Phase 6** | Jan–Feb 2027 | Scale & Launch (K8s, CI/CD, App Store, Beta) | ⏭️ PLANNED |

---

## Architecture (Current vs Target)

### Current Architecture (March 2026)
```
                Mobile App (React Native/Expo) ✅ 85%
                         │
                    ┌────▼────┐
                    │  Nginx  │ SSL + Rate Limiting ✅
                    └────┬────┘
                         │
               ┌─────────▼──────────┐
               │  NestJS Backend    │ Auth ✅, CRUD ✅, WebSocket ✅
               │  :4000             │ BullMQ ✅, Prisma ✅
               └─────┬──────┬──────┘
                gRPC  │      │ HTTP
          ┌───────────▼──────▼───────────┐
          │     AI Engine (FastAPI)       │ 14 endpoints ✅
          │     :8000 / :50051           │ 8/8 gRPC methods ✅
          │  ┌───────────────────────┐   │
          │  │ Vision ✅│Physics ✅│RAG ✅│
          │  │ OCR ✅   │Neo4j ⚠️ │LLM ⚠️│
          │  └───────────────────────┘   │
          └──┬──────┬──────┬──────┬──────┘
             │      │      │      │
    ┌────────▼┐ ┌───▼──┐ ┌▼────┐ ┌▼──────┐
    │Postgres │ │Qdrant│ │Neo4j│ │RustFS │
    │+PostGIS │ │  ✅  │ │  ⚠️ │ │  ✅   │
    └─────────┘ └──────┘ └─────┘ └───────┘
         Redis ✅ │ Ollama ⚠️ │ MLflow ❌
```

### Target Architecture (Post Phase 6)
```
┌─────────────────────────────────────────────────────────────┐
│                    Clients / Frontends                       │
│  Consumer Web │ Partner Portal │ Admin Dashboard │ Mobile    │
│    (Next.js)  │   (Next.js)    │   (Next.js)    │ (Expo)    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                    ┌────▼────┐
                    │  Nginx  │ Let's Encrypt SSL
                    │  + CDN  │ Rate Limiting + Caching
                    └────┬────┘
                         │
           ┌─────────────▼──────────────┐
           │  NestJS Backend (K8s HPA)  │ Horizontal Scale
           │  Auth, CRUD, WebSocket     │ OpenTelemetry Tracing
           │  BullMQ, Prisma, RBAC      │ Partner API Keys
           └─────┬──────┬──────────────┘
            gRPC  │      │ HTTP
       ┌──────────▼──────▼───────────────┐
       │  AI Engine — K8s HPA (GPU pods)  │
       │  ┌─────────────────────────┐     │
       │  │ Vision  │ Physics │ RAG  │     │
       │  │ TensorRT│ Neo4j   │ CLIP │     │
       │  │ OCR     │ Graph   │ LLM  │     │
       │  └─────────────────────────┘     │
       └──┬──────┬──────┬──────┬─────────┘
          │      │      │      │
 ┌────────▼┐ ┌──▼───┐ ┌▼────┐ ┌▼───────┐
 │Postgres │ │Qdrant│ │Neo4j│ │RustFS  │
 │+PostGIS │ │CLIP+ │ │Graph│ │  S3    │
 │ (HA)    │ │BM25  │ │ RAG │ │Backups │
 └─────────┘ └──────┘ └─────┘ └────────┘
    Redis (Sentinel) │ Ollama │ MLflow │ Loki
                     │        │        │
              ┌──────▼────────▼────────▼──────┐
              │        Observability            │
              │  Prometheus → Grafana → Alerts  │
              │  OpenTelemetry → Jaeger         │
              │  Loki → Log Aggregation         │
              └────────────────────────────────┘
```

---

## File Inventory (March 8, 2026)

### AI Engine (`greenvalue-ai/`) — 53 source files, ~10,000 LOC
| Module | Files | Key Classes | Status |
|--------|-------|-------------|--------|
| `main.py` | 1 | FastAPI app, 14 endpoints | ✅ |
| `config/` | 1 | `Settings` (Pydantic) | ✅ |
| `modules/pipeline.py` | 1 | `AnalysisPipeline` (5-step) | ✅ |
| `modules/vision/` | 2 | `YOLOInferenceEngine`, `HeatmapGenerator` | ✅ |
| `modules/physics/` | 1 | `PhysicsEngine`, 7 component classes | ✅ |
| `modules/rag/` | 17 | `Ultimate100RAGPipeline`, `SemanticCache`, `LLMDomainRouter`, `RetrievalEngine`, `EmbeddingManager`, `GreenValueDocumentStore`, `RealTimeLearningEngine`, `CorrectiveRAG`, `PropTechQueryExpander`, `CrossEncoderReranker`, `KnowledgeGraph`, `PropertyGraph`, `SQLiteMemory`, `AdvancedAnalyticsDashboard` | ✅ 90% |
| `modules/report/` | 8 | `ReportEngine`, `SectionGenerator`, `ChainOfThoughtEngine`, `WeasyPrint renderer` | ✅ 85% |
| `modules/ocr/` | 6 | `OCREngine` (4 strategies), `ImagePreprocessor`, `LayoutAnalyzer`, `TableExtractor` | ✅ 95% |
| `modules/graph/` | 4 | `PropertyKnowledgeGraph` (Neo4j), `Client`, `Schema` | ⚠️ 80% |
| `modules/grpc_server/` | 3 | `AIServiceServicer` (8 methods) | ✅ 90% |
| `modules/queue/` | 2 | `QueueConsumer` (BullMQ) | ✅ |
| `modules/storage/` | 2 | `StorageService` (MinIO/RustFS) | ✅ |
| `scripts/` | 4 | `ingest_books.py`, `init_qdrant.py`, `generate_proto.py`, `debug_api.py` | ✅ |
| `tests/` | 2 | `TestPhysicsEngine` (9 tests), `TestHeatmapGenerator` (3 tests) | ⚠️ 40% |

### NestJS Backend (`greenvalue-be/`) — 50+ source files, ~5,000 LOC
| Module | Files | Endpoints | Status |
|--------|-------|-----------|--------|
| `auth/` | 8 | 13 | ✅ 95% (resetPassword incomplete) |
| `user/` | 7 | 9 | ✅ 100% |
| `property/` | 4 | 7 | ✅ 100% |
| `report/` | 6 | 7 | ✅ 95% (BullMQ worker fixed) |
| `ai-proxy/` | 5 | 5 | ✅ 90% |
| `audit/` | 3 | 3 | ✅ 100% |
| `websocket/` | 2 | 4 handlers | ✅ 95% |
| `health/` | 2 | 3 | ✅ 100% |
| `metrics/` | 4 | 1 (Prometheus) | ✅ 95% |
| `core/` | 8 | — | ✅ 100% (Prisma, Redis, BullMQ, Storage) |
| `common/` | 5 | — | ✅ 100% (Filters, Interceptors, Guards) |

### Mobile App (`greenvalue-fe/greenvalue-mobile/greenvalue/`) — 50+ files, ~8,000 LOC
| Area | Status | Coverage |
|------|--------|----------|
| Authentication (login/register/guards) | ✅ | 100% |
| Dashboard (stats, property list, recent scans) | ✅ | 100% |
| Map Explorer (OSM, clustering, filters, geocoding) | ✅ | 100% |
| Scan Wizard (5 steps: capture → results) | ✅ | 100% |
| Reports (list, download, preview) | ✅ | 100% |
| Notifications (audit log mapping, deep links) | ✅ | 100% |
| Profile Settings (5 sub-screens) | ✅ | 95% |
| Offline Mode (SQLite, sync, cache) | ✅ | 90% |
| API Services (6 service files, 40+ methods) | ✅ | 100% |
| Zustand Stores (6 stores) | ✅ | 100% |
| Shared Components (6 UI components) | ✅ | 100% |
| Subscription Payments | ❌ | 0% (placeholder) |
| Investment Prefs Backend Sync | ❌ | 0% (local only) |
| Green Mortgage & Bank Integration | 📋 | 0% (Phase 4.5 planned) |

### Web Apps — ALL EMPTY
| App | Path | Files | Status |
|-----|------|-------|--------|
| Consumer | `greenvalue-consumer/` | 0 | ❌ Empty directory |
| Partner | `greenvalue-partner/` | 0 | ❌ Empty directory |
| Admin | `greenvalue-admin/` | 0 | ❌ Empty directory |

### Infrastructure — 15+ config files
| Component | Status | Issue |
|-----------|--------|-------|
| `docker-compose.yml` (14 services) | ✅ | Latest, preferred |
| `Dockerfile` (AI Engine, CUDA 12.4) | ✅ | Multi-stage |
| `Dockerfile` (NestJS, Node 20) | ✅ | Multi-stage |
| `nginx.conf` (SSL, rate limiting) | ✅ | Production-grade |
| `prometheus.yml` (6 scrape targets) | ✅ | — |
| `alerting_rules.yml` | ⚠️ | References undefined metrics |
| `Grafana dashboards` | ⚠️ | Datasources directory empty |
| `init-postgis.sql` (5 extensions) | ✅ | — |
| `qdrant_collection.json` | ✅ | — |
| Knowledge base (15 PDFs) | ✅ | Books present |
| `gRPC generated stubs` | ✅ | Compiled March 10 |
| `k8s/` manifests | ❌ | Empty directory |
| SSL certificates | ❌ | Self-signed script only |

---

## Risk Register

| Risk | Impact | Mitigation | Phase |
|------|--------|------------|-------|
| GPU memory limits (GTX 1650 Ti = 4GB) | High | Use YOLO11m (not x), TensorRT optimization | 4 |
| Neo4j memory growth | Medium | Set heap/pagecache limits, partition by city | 2.5 |
| Unstructured API timeout on large PDFs | Medium | Batched processing (15 pages), PyPDF2 fallback | ✅ Done |
| Ollama LLM quality | Medium | Fine-tune on PropTech data, test multiple models | 4 |
| Single-node deployment | High | Phase 6 K8s migration, health checks | 6 |
| Three empty web apps (large scope) | High | Shared component library, parallel development | 3 |
| ~~gRPC stubs not compiled~~ | ✅ Fixed | ~~Resolved March 10~~ | 2.5 |
| ~~Report queue broken~~ | ✅ Fixed | ~~Resolved March 10~~ | 2.5 |
| Zero E2E test coverage | Medium | Phase 4D dedicated testing sprint | 4 |
| App Store review timeline | Medium | Start iOS review process 4+ weeks before launch | 6 |
| Bank rule changes (BDDK / EU) | Medium | Store rules as configurable seed data, version-controlled | 4.5 |
| EPC/EKB accuracy disclaimer | Medium | Clearly mark as estimate, require certified assessor for official cert | 4.5 |
| Multi-country regulatory compliance | High | Start with TR + UK + DE, expand per market demand | 4.5 |

---

## KPI Targets

| Metric | Current (Mar 8) | Phase 2.5 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|--------|-----------------|-----------|---------|---------|---------|---------|
| YOLO inference time | ~2s | < 2s | < 2s | < 1.4s | < 1.2s | < 1s |
| RAG response time | ~5s | < 3s | < 2.5s | < 2s | < 1.5s | < 1.5s |
| OCR accuracy (tables) | 85% | 85% | 85% | 90% | 92% | 95% |
| API uptime | N/A | 95% | 97% | 98% | 99% | 99.9% |
| Concurrent users | 1 | 10 | 25 | 50 | 100 | 1000+ |
| Knowledge base books | 15 PDFs | 15 | 15 | 20+ | 30+ | 50+ |
| Knowledge base chunks | 5,000+ | 5,000+ | 5,000+ | 10,000+ | 20,000+ | 50,000+ |
| Neo4j graph nodes | 100+ | 200+ | 500+ | 2,000+ | 3,000+ | 5,000+ |
| IVS report compliance | IVS-2025 | IVS-2025 | IVS-2025 | IVS-2025 | IVS-2025 | IVS-2025 |
| Report generation time | ~30s | < 25s | < 20s | < 15s | < 12s | < 10s |
| Test coverage (AI) | ~15% | 30% | 40% | 70% | 75% | 80% |
| Test coverage (Backend) | ~5% | 20% | 40% | 80% | 85% | 90% |
| Web app completion | 0% | 0% | 75% | 90% | 95% | 100% |
| Mobile app completion | 85% | 85% | 95% | 97% | 100% | 100% |
