# PROJECT CONTEXT: GREENVALUE AI (Bootstrap Edition)

## 1. PROJECT OVERVIEW
GreenValue AI is a PropTech platform that automates property valuation and energy efficiency retrofitting analysis. The system analyzes user-uploaded property photos using Computer Vision to identify energy inefficiencies (e.g., old windows, uninsulated facades) and generates a financial ROI report for renovations.

**CRITICAL CONSTRAINT:** This project follows a "Zero Cost / Bootstrap" strategy.
- **NO** Paid Cloud Services (AWS, Google Cloud, Azure).
- **NO** Paid APIs (Google Maps, Auth0, OpenAI).
- **USE** Self-hosted Open Source alternatives (RustFS/MinIO, Leaflet/OSM, Passport.js, Local YOLO).

---

## 2. TECHNOLOGY STACK

### A. Infrastructure (Dockerized)
| Service | Image | Port(s) | Description |
|---------|-------|---------|-------------|
| PostgreSQL 16 + PostGIS | `postgis/postgis:16-3.4` | 5432 | Primary spatial database |
| Redis Stack | `redis/redis-stack:latest` | 6379, 8001 | BullMQ queue + Session cache |
| RustFS | `rustfs/rustfs:latest` | 9000, 9001 | S3-compatible storage (2.3x faster than MinIO) |
| Qdrant | `qdrant/qdrant` | 6333, 6334 | Visual similarity vector search |
| MLflow | `ghcr.io/mlflow/mlflow:v2.18.0` | 5000 | Model registry & experiment tracking |
| Nginx | `nginx:1.25-alpine` | 80, 443 | Reverse proxy + SSL termination |
| Prometheus | `prom/prometheus:v2.48.0` | 9091 | Metrics collection |
| Grafana | `grafana/grafana:10.2.2` | 3003 | Monitoring dashboards |

**Storage Buckets (RustFS):** `raw-uploads`, `pdf-reports`, `ai-heatmaps`

---

### B. Backend API (`greenvalue-be/`)
- **Framework:** NestJS v11 (Node.js 20, Fastify adapter)
- **Language:** TypeScript 5
- **ORM:** Prisma 5 with PostGIS extensions
- **Auth:** Passport-JWT with RBAC (Roles: OWNER, CONTRACTOR, ADMIN)
- **Queue:** BullMQ (Redis-backed job queue)
- **Storage:** AWS SDK S3 (configured for RustFS/MinIO)
- **Realtime:** Socket.IO with Redis adapter
- **gRPC:** Communication with AI Engine
- **Port:** 4000 (host) → 3000 (container)

**Backend Modules:**
| Module | Description |
|--------|-------------|
| `auth/` | JWT authentication, RBAC, OAuth strategies, guards |
| `user/` | User profile management, stats |
| `property/` | Property CRUD, geolocation |
| `audit/` | Audit logging for all actions |
| `ai-proxy/` | Bridge to AI Engine (gRPC/HTTP) |
| `websocket/` | Real-time notifications |
| `health/` | Liveness/readiness probes |
| `metrics/` | Prometheus metrics endpoint |

---

### C. AI Engine (`greenvalue-ai/`)
- **Framework:** Python 3.12 + FastAPI 0.115
- **Runtime:** CUDA 12.4 (GPU-enabled container)
- **Vision:** YOLO11 Instance Segmentation (`ultralytics` 8.3.40)
- **Physics:** NumPy + SciPy (U-Value thermal calculations)
- **Reports:** ReportLab (PDF) + Matplotlib (heatmaps)
- **Vector Search:** Qdrant client ("Homes Like This" feature)
- **Ports:** 8000 (HTTP), 50051 (gRPC), 9090 (Metrics)

**AI Modules:**
| Module | Description |
|--------|-------------|
| `vision/` | YOLO inference, object detection |
| `physics/` | U-Value calculation, thermal analysis |
| `queue/` | BullMQ job consumer |
| `storage/` | MinIO/RustFS file operations |
| `pipeline.py` | Main analysis orchestration |

---

### D. Mobile App (`greenvalue-fe/greenvalue-mobile/greenvalue/`)
- **Framework:** React Native (Expo SDK 52)
- **Language:** TypeScript
- **State:** Zustand (client state)
- **Navigation:** Expo Router (file-based)
- **Storage:** SQLite (offline mode), Expo SecureStore (tokens)
- **Camera:** Expo Camera API
- **Maps:** react-native-maps with OSM tiles

**App Structure:**
```
app/
├── (auth)/           # Auth screens (login, register)
│   ├── login.tsx
│   └── register.tsx
├── (tabs)/           # Main tab navigation
│   ├── index.tsx     # Dashboard
│   ├── map.tsx       # Property map explorer
│   ├── scan.tsx      # Camera scan
│   ├── reports.tsx   # Analytics & reports
│   └── profile.tsx   # User profile
└── _layout.tsx       # Root layout with auth guard
```

**API Services:**
| Service | Endpoints |
|---------|-----------|
| `auth.api.ts` | login, register, me, updateProfile, changePassword |
| `property.api.ts` | getAll, getById, create, update, delete, getForMap |
| `analysis.api.ts` | analyze, status, report |
| `user.api.ts` | getProfile, getStats |
| `report.api.ts` | getMyHistory |

**Zustand Stores:**
| Store | Purpose |
|-------|---------|
| `auth.store.ts` | User auth state, login/logout actions |
| `property.store.ts` | Property list from API |
| `report.store.ts` | Audit history from API |
| `app.store.ts` | Global app state (theme, network) |

---

### E. Frontend Web Apps (`greenvalue-fe/`)
| App | Description | Port | Status |
|-----|-------------|------|--------|
| `greenvalue-consumer/` | Consumer Web (Homeowners) | 3001 | Scaffolded |
| `greenvalue-partner/` | B2B Partner Portal | 3002 | Scaffolded |
| `greenvalue-admin/` | Admin Dashboard | - | Empty |

**Stack:** Next.js 14, Mantine UI, React-Leaflet, TanStack Query, Zustand

---

## 3. DATABASE SCHEMA (Prisma)

> File: `greenvalue-be/prisma/schema.prisma`

### Enums
| Enum | Values |
|------|--------|
| `Role` | OWNER, CONTRACTOR, ADMIN |
| `AnalysisStatus` | PENDING, PROCESSING, COMPLETED, FAILED |
| `EnergyLabel` | A_PLUS, A, B, C, D, E, F, G |
| `ReportFormat` | PDF, JSON |

### Models
| Model | Key Fields | Relations |
|-------|------------|-----------|
| **User** | id, email, password, fullName, phone, role, isActive, lastLogin | → Property[], Analysis[], Report[], AuditLog[] |
| **Property** | id, title, address, city, latitude, longitude, buildingYear, floorArea | → Owner (User), Analysis[], Report[] |
| **Analysis** | id, jobId, status, imageKey, heatmapKey, detections, overallUValue, energyLabel, renovations | → Property, User, Report? |
| **Report** | id, format, fileKey, fileSize, title | → Analysis, Property, User |
| **AuditLog** | id, action, entity, entityId, metadata, ip, userAgent | → User? |

---

## 4. ARCHITECTURE

### 7-Layer Enterprise Stack
```
Layer 1: Presentation (Omnichannel)
  ├── Consumer Web (Next.js 14) :3001
  ├── Partner Portal (Next.js 14) :3002  
  ├── Admin Dashboard (Next.js 14)
  └── Mobile App (React Native/Expo)

Layer 2: Edge & Gateway (Nginx) :80/:443
  └── SSL Termination, Rate Limiting, Static Cache

Layer 3: Application Core (NestJS) :4000
  ├── Modules: Auth, Property, User, Audit, AI-Proxy
  └── Adapters: BullMQ, S3, Prisma, WebSocket

Layer 4: AI Intelligence (Python FastAPI) :8000
  ├── YOLO11 Vision + Physics Engine
  ├── GPU Acceleration (CUDA 12.4)
  └── MLflow Model Registry :5000

Layer 5: Data Persistence (PostgreSQL + PostGIS) :5432

Layer 6: Storage & Vectors
  ├── RustFS S3 :9000 — Photos, Reports, Heatmaps
  ├── Qdrant :6333 — Visual Similarity Search
  └── Redis :6379 — Queue + Cache

Layer 7: Observability
  ├── Prometheus :9091
  └── Grafana :3003
```

### Scan-to-Value Pipeline
1. **Upload** → User uploads property photo via Mobile/Web
2. **Store** → NestJS validates & uploads to RustFS (`raw-uploads`)
3. **Queue** → Job pushed to Redis (BullMQ)
4. **Process** → AI Engine pulls job, downloads image
5. **Inference** → YOLO11 detects windows/facade, calculates U-Value
6. **Heatmap** → Thermal overlay generated, uploaded to RustFS
7. **Report** → PDF with ROI analysis, uploaded to RustFS
8. **Notify** → Result saved to PostgreSQL, WebSocket notification
9. **Similarity** → Property embedding stored in Qdrant

---

## 5. FOLDER STRUCTURE

```
GreenValue AI/
├── PROJECT_CONTEXT.md          # This file
├── docker-compose.yml          # Full-stack compose (root level)
├── .env                        # Environment variables
│
├── greenvalue-be/              # NestJS Backend
│   ├── prisma/schema.prisma    # Database schema
│   ├── proto/ai_service.proto  # gRPC definitions
│   ├── src/
│   │   ├── auth/               # JWT + RBAC
│   │   ├── property/           # Property CRUD
│   │   ├── user/               # User management
│   │   ├── audit/              # Audit logging
│   │   ├── ai-proxy/           # AI Engine bridge
│   │   ├── websocket/          # Real-time
│   │   ├── health/             # Health checks
│   │   └── metrics/            # Prometheus
│   └── Dockerfile
│
├── greenvalue-ai/              # Python AI Engine
│   ├── main.py                 # FastAPI app
│   ├── modules/
│   │   ├── vision/             # YOLO inference
│   │   ├── physics/            # U-Value calc
│   │   ├── queue/              # BullMQ consumer
│   │   └── storage/            # S3 operations
│   ├── infrastructure/
│   │   ├── docker/Dockerfile   # CUDA image
│   │   ├── nginx/              # Reverse proxy config
│   │   └── prometheus/         # Metrics config
│   └── requirements.txt
│
├── greenvalue-fe/              # Frontend Applications
│   ├── greenvalue-mobile/greenvalue/  # React Native/Expo
│   │   ├── app/                # Expo Router screens
│   │   │   ├── (auth)/         # Login, Register
│   │   │   └── (tabs)/         # Dashboard, Map, Scan, Reports, Profile
│   │   └── src/
│   │       ├── services/api/   # API client & services
│   │       ├── stores/         # Zustand state
│   │       ├── core/types/     # TypeScript types
│   │       └── shared/         # Components & hooks
│   ├── greenvalue-consumer/    # Web (Homeowners)
│   ├── greenvalue-partner/     # Web (Contractors)
│   └── greenvalue-admin/       # Web (Admin) - empty
│
└── reference_files/            # Architecture examples
```

---

## 6. DOCKER COMPOSE

**Location:** `GreenValue AI/docker-compose.yml`

| Command | Services |
|---------|----------|
| `docker compose up -d` | Core: PostgreSQL, Redis, RustFS, Backend, AI Engine, Qdrant |
| `--profile ml` | + MLflow |
| `--profile monitoring` | + Prometheus, Grafana |
| `--profile gateway` | + Nginx |

---

## 7. API ENDPOINTS

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/register` | Create new user | No |
| POST | `/login` | Login, returns JWT | No |
| GET | `/me` | Get current user | Yes |
| PUT | `/profile` | Update profile | Yes |
| POST | `/change-password` | Change password | Yes |
| POST | `/forgot-password` | Request password reset | No |

### Properties (`/api/v1/properties`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/` | List user's properties | Yes |
| POST | `/` | Create property | Yes |
| GET | `/:id` | Get property by ID | Yes |
| PUT | `/:id` | Update property | Yes |
| DELETE | `/:id` | Delete property | Yes |

### Analysis (`/api/v1/analysis`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/analyze` | Submit photo for analysis | Yes |
| GET | `/status/:jobId` | Get analysis status | Yes |
| GET | `/report/:analysisId` | Get analysis report | Yes |

### Users (`/api/v1/users`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/me/stats` | Get user statistics | Yes |

### Audit (`/api/v1/audit`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/my-history` | Get user's audit log | Yes |

---

## 8. PORT MAP

| Service | Host | Container | Protocol |
|---------|------|-----------|----------|
| NestJS Backend | 4000 | 3000 | HTTP/WS |
| AI Engine (HTTP) | 8000 | 8000 | HTTP |
| AI Engine (gRPC) | 50051 | 50051 | gRPC |
| AI Metrics | 9090 | 9090 | HTTP |
| PostgreSQL | 5432 | 5432 | TCP |
| Redis | 6379 | 6379 | TCP |
| RedisInsight | 8001 | 8001 | HTTP |
| RustFS API | 9000 | 9000 | S3/HTTP |
| RustFS Console | 9001 | 9001 | HTTP |
| Qdrant HTTP | 6333 | 6333 | HTTP |
| Qdrant gRPC | 6334 | 6334 | gRPC |
| MLflow | 5000 | 5000 | HTTP |
| Prometheus | 9091 | 9090 | HTTP |
| Grafana | 3003 | 3000 | HTTP |
| Nginx HTTP | 80 | 80 | HTTP |
| Nginx HTTPS | 443 | 443 | HTTPS |

---

## 9. ENVIRONMENT VARIABLES

### Backend (`.env`)
```env
DATABASE_URL=postgresql://user:pass@postgres:5432/greenvalue
JWT_SECRET=your-jwt-secret
JWT_EXPIRES_IN=7d
REDIS_URL=redis://redis:6379
S3_ENDPOINT=http://rustfs:9000
S3_ACCESS_KEY=admin
S3_SECRET_KEY=secret
AI_ENGINE_URL=http://greenvalue-ai:8000
```

### Mobile App (`src/config/env.ts`)
```env
API_BASE_URL=http://<YOUR_IP>:4000
STORAGE_URL=http://<YOUR_IP>:9000
WS_URL=ws://<YOUR_IP>:4000
```

---

## 10. DEVELOPMENT STATUS

| Component | Status | Completion | Notes |
|-----------|--------|------------|-------|
| **Backend API** | ✅ Production-ready | **~85%** | 17 modules imported, full CRUD, JWT auth, RBAC, WebSocket, BullMQ, gRPC proxy, audit logging |
| **Mobile App** | 🔶 Core working | **~70%** | Auth, scan→upload→process→result flow wired end-to-end. 5 profile sub-screens are mock data. |
| **AI Engine** | 🔶 Functional (with caveats) | **~75%** | 27 real endpoints. YOLO inference runs but uses COCO pretrained (not custom building classes). Full RAG pipeline operational. |
| **Docker Compose** | ✅ Complete | **~95%** | 14 services, GPU support, health checks, profiles for ml/monitoring/gateway |
| **Consumer Web** | 🔶 Scaffolded | **~5%** | Next.js structure only |
| **Partner Portal** | 🔶 Scaffolded | **~5%** | Next.js structure only |
| **Admin Dashboard** | ❌ Empty | **0%** | Not started |

---

## 11. DEEP AUDIT — CURRENT STATE (March 2026)

### A. Backend (NestJS) — Detailed Status

**What Works End-to-End:**
- User registration/login → JWT → all protected routes
- Property CRUD with pagination, filtering, geolocation
- Pre-signed URL upload flow (mobile → backend → RustFS)
- AI analysis submission via HTTP or gRPC (with automatic failover)
- Analysis status polling
- Analysis result persistence to PostgreSQL
- Report generation via BullMQ queue + worker
- Report CRUD with presigned download URLs
- Audit logging (15 action types, event-driven)
- WebSocket (analysis:progress, analysis:completed, analysis:failed, report:ready, notifications)
- Kubernetes-ready health checks (liveness/readiness)
- Prometheus metrics (10+ custom counters/histograms)

**Known Issues:**
| # | Issue | Severity | File |
|---|-------|----------|------|
| 1 | `CommonModule` NOT imported in `AppModule` — global exception filters/interceptors are dead code | Medium | `app.module.ts` |
| 2 | `report.service.ts` uses `(this.prisma.report as any)` casts — Prisma client needs regeneration | Medium | `report.service.ts` |
| 3 | Metrics middleware imports Express types but app runs on Fastify | Low | `metrics.middleware.ts` |
| 4 | Password reset generates token but never sends email | High | `auth.service.ts` |
| 5 | 3 of 5 BullMQ queues have no workers (notifications, email, cleanup) | Medium | `queue.service.ts` |
| 6 | `ScheduleModule` imported but no `@Cron()` decorators exist | Low | `app.module.ts` |
| 7 | OAuth strategies use `'your-client-id'` placeholders | Low | `google.strategy.ts` |
| 8 | Duplicate `RolesGuard` implementations (auth vs common) | Low | `roles.guard.ts` |
| 9 | `rememberMe` field accepted in DTO but ignored in logic | Low | `auth.service.ts` |
| 10 | `RefreshTokenDto`/`VerifyEmailDto` defined but unused — no refresh or email verification flow | Medium | `auth/dto/` |

**Dead Code:**
- `AppController` / `AppService` — empty shells
- `CommonModule` — never imported
- `common/guards/rate-limit.guard.ts` — unused (ThrottlerGuard handles it)
- `common/pagination/` — unused (inline pagination everywhere)
- `common/interfaces/base-response.ts` — never imported
- `common/enums/role.enum.ts` — Prisma Role used instead
- `auth/guards/optional-jwt-auth.guard.ts` — exported but never used
- `SubscriptionGuard` — exported but never used

### B. Mobile App (React Native/Expo) — Detailed Status

**What Works End-to-End:**
- Auth flow: login → JWT stored in SecureStore → auto-redirect
- Registration with client-side validation
- Dashboard: real properties from API, stats, pull-to-refresh
- Map: OSM tiles, real properties, geocoding, filter chips, clustering
- Scan: camera capture / gallery → photo grid → RustFS upload (pre-signed) → AI submission
- Processing: dual-channel progress (WebSocket + HTTP polling), auto-navigate on completion
- Valuation Result: energy donut, U-values, component details, renovation suggestions, report generation, persist to DB
- Property Detail: real data, analysis history, report list
- Reports Tab: real data from API, summary stats, delete
- Offline: SQLite schema (4 tables), sync service, local property cache

**Known Issues:**
| # | Issue | Severity |
|---|-------|----------|
| 1 | Feature Validation screen uses hardcoded mock data, disconnected from AI results | High |
| 2 | Feature Validation screen is NEVER navigated to (scan→processing skips it) | Medium |
| 3 | Notifications screen is fully mock data, no WS/API integration | High |
| 4 | 5 profile sub-screens (personal-info, investments, subscription, security, environmental) have mock data | Medium |
| 5 | Social login buttons (Google/Apple) are UI-only — no OAuth | Medium |
| 6 | "Forgot Password" link does nothing | Medium |
| 7 | No PDF viewer or download trigger for reports | High |
| 8 | Portfolio chart on Dashboard is an empty placeholder | Low |
| 9 | "Premium Member"/"Gold Badge"/"Avg Energy Score: A" hardcoded on Profile | Low |
| 10 | WebSocket only connected reactively (processing screen); not globally | Medium |
| 11 | TanStack Query installed but never used (all data via Zustand + direct API) | Low |
| 12 | NativeWind/Tailwind installed but barely used (inline StyleSheet everywhere) | Low |
| 13 | `expo-camera` installed but only used for permissions (actual capture via ImagePicker) | Low |
| 14 | No refresh token rotation (401 just logs out) | Medium |
| 15 | `properties.tsx.bak` dead file in tabs | Low |

### C. AI Engine (Python/FastAPI) — Detailed Status

**What Works:**
- All 27 endpoints have real implementations (none are stubs)
- YOLO11m-seg loads and runs inference with GPU support
- Full analysis pipeline: MinIO download → YOLO → Physics → Heatmap → MinIO upload
- U-Value calculation with 19 materials, EN ISO 6946 formulas, energy labeling (A–G)
- Heatmap generation with matplotlib (color-coded by condition)
- gRPC server with 8 RPCs (dynamic proto compilation)
- Full RAG pipeline with 18 modules: embeddings (BGE-small + BM25), corrective RAG, semantic routing, knowledge graph, user memory, query expansion, semantic caching, reranking (FlashRank + cross-encoder)
- Two RAG implementations: standard `GreenValueRAG` and `Ultimate100RAGPipeline` (850 lines)
- OCR with 4 strategies (hi_res, tesseract, hybrid, fast)
- IVS-2025 report generation (JSON + PDF)
- BullMQ-compatible Redis consumer

**Critical Issues:**
| # | Issue | Severity |
|---|-------|----------|
| 1 | **YOLO uses pretrained COCO weights** — detects "person/car" not "window/facade". Custom training needed. | **CRITICAL** |
| 2 | All job results stored in-memory (`_state` dict) — **lost on restart** | **CRITICAL** |
| 3 | No authentication on any endpoint | High |
| 4 | `pixel_to_m2_ratio = 0.001` is a naive fixed constant | High |
| 5 | Dead code: `similarity_search()` body after `return` in retrieval.py | Medium |
| 6 | Learning engine data ephemeral (in-memory only) | Medium |
| 7 | Prometheus metrics hand-rolled (not using `prometheus_client` lib) | Low |
| 8 | MLflow in requirements but never imported/used | Low |
| 9 | No rate limiting on endpoints | Medium |
| 10 | Vision-RAG calls itself via HTTP (http://localhost:8000) | Low |

### D. Infrastructure — Status

| Service | Status | Running? | Notes |
|---------|--------|----------|-------|
| PostgreSQL + PostGIS | ✅ | Yes | Init script ready, health check working |
| Redis Stack | ✅ | Yes | BullMQ + caching + RedisInsight UI |
| RustFS | ✅ | Yes | 3 buckets auto-created via mc init container |
| Qdrant | ✅ | Yes | RAG collection working |
| NestJS Backend | ✅ | Yes | Docker + local dev both working |
| AI Engine | ✅ | Yes | CUDA 12.4, multi-stage build |
| Ollama | ✅ | Yes | LLM serving for RAG, needs `ollama pull llama3.2:3b` |
| Neo4j | ✅ | Yes | Knowledge graph, APOC + GDS plugins |
| Unstructured API | ✅ | Yes | PDF table extraction for RAG ingestion |
| MLflow | ✅ (profile: ml) | On-demand | Not integrated with code |
| Nginx | ✅ (profile: gateway) | On-demand | SSL config ready |
| Prometheus | ✅ (profile: monitoring) | On-demand | Custom alerting rules |
| Grafana | ✅ (profile: monitoring) | On-demand | Dashboard provisioning |
| cAdvisor | ✅ (profile: monitoring) | On-demand | Container metrics |
| Node Exporter | ✅ (profile: monitoring) | On-demand | System metrics |

**Total: 15 services, 15 named volumes, 1 bridge network.**

---

## 12. ROADMAP

### Phase 0: Stabilize (NOW — Week 1-2)
> **Goal:** Fix all critical bugs preventing the demo-ready MVP.

| # | Task | Component | Priority | Effort |
|---|------|-----------|----------|--------|
| 0.1 | Run `npx prisma migrate dev` + `npx prisma generate` to fix `as any` casts in report service | Backend | **P0** | 15 min |
| 0.2 | Import `CommonModule` in `AppModule` (activates global exception filters + logging interceptor) | Backend | **P0** | 5 min |
| 0.3 | Fix Metrics middleware Express→Fastify types (`FastifyRequest`/`FastifyReply`) | Backend | **P1** | 15 min |
| 0.4 | Persist analysis results to Redis/DB instead of in-memory `_state` dict | AI Engine | **P0** | 2 hr |
| 0.5 | Connect WebSocket globally in mobile app root (not just processing screen) | Mobile | **P0** | 30 min |
| 0.6 | Wire Feature Validation screen to real AI detection data OR remove from flow | Mobile | **P1** | 2 hr |
| 0.7 | Delete `properties.tsx.bak` dead file | Mobile | **P2** | 1 min |
| 0.8 | Add AI engine authentication (forward JWT or use shared API key from backend) | AI Engine | **P1** | 2 hr |

### Phase 1: Core Experience (Week 3-6)
> **Goal:** End-to-end working product for demo day.

| # | Task | Component | Priority | Effort |
|---|------|-----------|----------|--------|
| 1.1 | **Train custom YOLO11 on building component dataset** (window, door, facade, roof, balcony, insulation, solar_panel) | AI Engine | **P0** | 2-3 weeks |
| 1.2 | Create/annotate building component dataset (Roboflow/CVAT) — min 500 images | AI Engine | **P0** | 1-2 weeks |
| 1.3 | Integrate MLflow for YOLO training experiment tracking | AI Engine | **P1** | 1 day |
| 1.4 | Implement email service (nodemailer + BullMQ email worker) — password reset, report ready notifications | Backend | **P1** | 2 days |
| 1.5 | Add report PDF viewer in mobile (expo-linking or WebView) | Mobile | **P1** | 1 day |
| 1.6 | Wire Notifications screen to WebSocket events + notification API | Mobile | **P1** | 2 days |
| 1.7 | Wire profile sub-screens to real API data (personal-info → `authApi.updateProfile()`, security → `authApi.changePassword()`) | Mobile | **P1** | 2 days |
| 1.8 | Implement camera calibration or reference-object area estimation (replace fixed `pixel_to_m2_ratio`) | AI Engine | **P1** | 3 days |
| 1.9 | Add BullMQ workers for notification + cleanup queues | Backend | **P2** | 1 day |
| 1.10 | Implement refresh token rotation (backend + mobile 401 interceptor) | Backend + Mobile | **P2** | 2 days |

### Phase 2: Intelligence & Polish (Week 7-10)
> **Goal:** Production-quality AI and polished UX.

| # | Task | Component | Priority | Effort |
|---|------|-----------|----------|--------|
| 2.1 | Implement real "Homes Like This" visual similarity (image embeddings → Qdrant, not just text) | AI Engine | **P1** | 3 days |
| 2.2 | Add Portfolio Value chart on Dashboard (D3/Victory Native or SVG) | Mobile | **P1** | 2 days |
| 2.3 | Implement push notifications (expo-notifications: push tokens → backend → FCM/APNs) | Backend + Mobile | **P1** | 3 days |
| 2.4 | Add Forgot Password flow end-to-end (email sending + reset token + mobile deep link) | Backend + Mobile | **P2** | 2 days |
| 2.5 | Replace hand-rolled Prometheus metrics with `prometheus_client` library | AI Engine | **P2** | 2 hr |
| 2.6 | Persist RAG learning engine data (SQLite/Redis instead of in-memory dicts) | AI Engine | **P2** | 1 day |
| 2.7 | Migrate from inline styles to NativeWind/Tailwind consistently across all screens | Mobile | **P3** | 3 days |
| 2.8 | Actually use TanStack Query for API calls (replace direct Zustand fetches) | Mobile | **P3** | 3 days |
| 2.9 | Add offline upload retry queue (SQLite-backed) with visual status | Mobile | **P2** | 2 days |
| 2.10 | Clean up dead code (CommonModule, unused guards, duplicate role enums, empty AppController) | Backend | **P3** | 2 hr |

### Phase 3: Multi-Platform (Week 11-16)
> **Goal:** Web frontends for different user types.

| # | Task | Component | Priority | Effort |
|---|------|-----------|----------|--------|
| 3.1 | Build Consumer Web — property dashboard, upload, results, reports (Next.js + Mantine) | Consumer Web | **P1** | 3 weeks |
| 3.2 | Build Partner Portal — contractor view, multi-property analysis, batch reports | Partner Web | **P2** | 3 weeks |
| 3.3 | Build Admin Dashboard — user management, system metrics, audit logs, AI model management | Admin Web | **P2** | 2 weeks |
| 3.4 | Implement OAuth (Google + GitHub) end-to-end with real credentials | Backend + All FE | **P2** | 2 days |
| 3.5 | Add subscription/payment system (Stripe or self-hosted) | Backend + Mobile | **P3** | 2 weeks |

### Phase 4: Scale & Deploy (Week 17-20)
> **Goal:** Production deployment with monitoring.

| # | Task | Component | Priority | Effort |
|---|------|-----------|----------|--------|
| 4.1 | Deploy to VPS/bare-metal with Docker Compose + monitoring profile | Infrastructure | **P1** | 2 days |
| 4.2 | Set up Grafana dashboards for all services | Infrastructure | **P1** | 1 day |
| 4.3 | Configure Alertmanager for critical alerts | Infrastructure | **P1** | 1 day |
| 4.4 | Set up CI/CD pipeline (GitHub Actions → Docker build → deploy) | Infrastructure | **P1** | 2 days |
| 4.5 | Implement database backup strategy (pg_dump cron → RustFS) | Infrastructure | **P2** | 1 day |
| 4.6 | Load testing with k6 or locust (identify bottlenecks) | Infrastructure | **P2** | 2 days |
| 4.7 | K8s manifests for scaling (if single-machine isn't sufficient) | Infrastructure | **P3** | 1 week |
| 4.8 | SSL certificates with Let's Encrypt auto-renewal | Infrastructure | **P2** | 1 day |

---

## 13. ARCHITECTURE DECISIONS LOG

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-10 | RustFS over MinIO | 2.3x faster, Apache 2.0 license, Rust-based |
| 2025-10 | Fastify over Express (NestJS) | Better performance, native TypeScript |
| 2025-11 | Expo Router over React Navigation | File-based routing, better DX |
| 2025-11 | Zustand over Redux | Lighter, less boilerplate |
| 2025-12 | BullMQ over RabbitMQ | Redis-backed simplicity, zero-cost |
| 2025-12 | Qdrant over Pinecone | Self-hosted, no API costs |
| 2026-01 | Ollama over OpenAI | Zero-cost, local LLM, data privacy |
| 2026-01 | Neo4j for property graph | Native graph queries, APOC plugins |
| 2026-02 | YOLO11 over YOLOv8 | Better segmentation, newer architecture |
| 2026-03 | FastEmbed over OpenAI embeddings | Zero-cost, local inference, low latency |