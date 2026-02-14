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

| Component | Status | Notes |
|-----------|--------|-------|
| Backend API | ✅ Complete | Auth, Property, Audit, WebSocket working |
| Mobile App | ✅ Integrated | API connected, all tabs functional |
| AI Engine | 🔶 Scaffolded | Main.py ready, needs YOLO training |
| Consumer Web | 🔶 Scaffolded | Next.js structure ready |
| Partner Portal | 🔶 Scaffolded | Next.js structure ready |
| Admin Dashboard | ❌ Empty | Not started |
| Docker Compose | ✅ Complete | All services configured |