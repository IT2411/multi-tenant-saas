# Enterprise Multi-Tenant SaaS Project Management Platform

[![CI/CD Quality Pipeline](https://github.com/IT2411/multi-tenant-saas/actions/workflows/ci.yml/badge.svg)](https://github.com/IT2411/multi-tenant-saas/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis)](https://redis.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-grade, highly concurrent multi-tenant project management backend (Linear / Jira / Trello architecture) engineered with **FastAPI**, **PostgreSQL 16 (SQLAlchemy 2.0 Async / asyncpg)**, **Redis 7**, **MinIO / AWS S3**, **ARQ Background Task Queue**, **Distributed WebSockets**, and **Prometheus Observability**.

---

## Key Architectural Features

* **Strict Tenant Isolation**: Shared-database, shared-schema tenancy model with repository-level scoping enforcing tenant boundaries on every read/write operation via `organization_id`.
* **Optimistic Concurrency Control (OCC)**: Version-based conflict detection (`version_id`) across Tasks and Projects returning `HTTP 409 Conflict` on concurrent collisions to prevent silent overwrites.
* **Distributed Real-Time Engine**: WebSocket rooms backed by a **Redis Pub/Sub** horizontal broadcast bus for live event synchronization across multiple FastAPI instances.
* **Direct-to-S3 Object Storage**: Client uploads and downloads offloaded directly to MinIO / S3 using AWS SigV4 presigned URLs with strict file-size ($\le 50\text{ MB}$) and MIME-type validation.
* **Sliding-Window Rate Limiting**: Token-bucket and sliding-window traffic shaping on authentication endpoints backed by Redis Sorted Sets with `Retry-After` headers.
* **Stateful Token Revocation & RBAC**: Quantum/GPU-resistant **Argon2id** password hashing, short-lived JWT access tokens (`15m`), rotating refresh tokens (`7d`) with Redis blacklisting, and hierarchical role enforcement (`Owner > Admin > Manager > Member > Viewer`).
* **Asynchronous Task Queue & Sweepers**: Native `asyncio` background task processing via **ARQ** with exponential backoff retries and automated daily database garbage collection sweepers.
* **Enterprise Error Handling & Tracing**: RFC 7807 Problem Details error formatting with `X-Request-ID` correlation tracking and microsecond latency measurement.
* **Production Observability**: Built-in Prometheus `/metrics` exposition, dedicated `/healthz` (liveness) and `/readyz` (readiness) probes, and structured JSON logging with `structlog`.

---

## System Architecture

```
                                  ┌────────────────────────────────────────┐
                                  │      Ingress Load Balancer / Nginx     │
                                  └──────────────────┬─────────────────────┘
                                                     │
                   ┌─────────────────────────────────┴─────────────────────────────────┐
                   │                                                                   │
          ┌────────▼────────────────┐                                         ┌────────▼──────────────┐
          │  FastAPI API Cluster    │                                         │  ARQ Background Worker│
          │  (4 Uvicorn Workers)    │                                         │  - Email Dispatcher   │
          │  - REST Endpoints       │                                         │  - Scheduled Sweepers │
          │  - WebSocket Hub        │                                         │  - Notification Tasks │
          │  - /metrics & /readyz   │                                         └────────┬──────────────┘
          └────────┬────────────────┘                                                  │
                   │                                                                   │
                   └─────────────────────────────────┬─────────────────────────────────┘
                                                     │
                       ┌─────────────────────────────┼─────────────────────────────┐
                       │                             │                             │
            ┌──────────▼──────────┐       ┌──────────▼──────────┐       ┌──────────▼──────────┐
            │    PostgreSQL 16    │       │   Redis 7 Cluster   │       │   MinIO / AWS S3    │
            │ (SQLAlchemy 2 Async │       │  - Cache-Aside      │       │ (Presigned Object   │
            │  Tenant Partition)  │       │  - Sliding Rate-Lim │       │  Storage Bucket)    │
            │  - Asyncpg Engine   │       │  - Pub/Sub WS Bus   │       │                     │
            └─────────────────────┘       │  - ARQ Task Queue   │       └─────────────────────┘
                                          └─────────────────────┘
```

---

## Technology Stack

| Component | Technology | Version / Tooling |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.111+` |
| **Runtime** | Python | `3.11` / `3.12` |
| **Database & ORM** | PostgreSQL 16 | SQLAlchemy `2.0+` (Async / `asyncpg`) |
| **Schema Migrations** | Alembic | `1.13+` (Async Migration Runner) |
| **Cache & Pub/Sub** | Redis | `7.0+` (`redis-py` async + hiredis) |
| **Object Storage** | MinIO / AWS S3 | `aioboto3` (SigV4 Presigned URLs) |
| **Task Queue** | ARQ | `0.25+` (Async Redis Worker) |
| **Password Security** | Argon2id | `argon2-cffi` |
| **Token Auth** | JWT | `PyJWT` (Crypto Backend) |
| **Real-Time WebSockets**| WebSockets | ASGI + Redis Pub/Sub Hub |
| **Telemetry & Metrics** | Prometheus | `prometheus-fastapi-instrumentator` |
| **Structured Logging** | Structlog | Newline-Delimited JSON / Console Dev |
| **Linter & Formatter** | Ruff | `0.5+` |
| **Type Safety** | Mypy | Strict Type Analysis |
| **Testing Harness** | Pytest | `pytest-asyncio` + `pytest-cov` |
| **Containerization** | Docker | Multi-Stage Non-Root Dockerfile + Compose |

---

## Project Layout

```text
multi-tenant-saas/
├── alembic                                       # Database migrations package (Alembic)
│   ├── versions                                  # Linear migration history (DDL revisions)
│   │   ├── 745e36ac4031_create_core_domain_tables.py   # Migration 1: Initial 9 relational domain tables
│   │   ├── 84d61c534314_add_project_occ_version_id.py  # Migration 2: Adds version_id to projects for OCC
│   │   └── .gitkeep                              # Git tracking placeholder for empty directory
│   ├── env.py                                    # Async migration runtime using asyncpg + Base.metadata
│   └── script.py.mako                            # Mako template for generating new migration scripts
├── app                                           # Core application root package
│   ├── api                                       # HTTP Presentation & routing layer
│   │   ├── v1                                    # API Version 1 routes
│   │   │   ├── endpoints                         # Individual domain route controllers
│   │   │   │   ├── attachments.py                # S3 Presigned upload/download URLs & metadata CRUD
│   │   │   │   ├── audit.py                      # Audit trail querying & JSONB state diff filtering
│   │   │   │   ├── auth.py                       # User auth (/register, /login, /refresh, /logout, /me)
│   │   │   │   ├── comments.py                   # Task comments CRUD with real-time room broadcasts
│   │   │   │   ├── health.py                     # Liveness (/healthz) & Readiness (/readyz) probes
│   │   │   │   ├── __init__.py                   # Endpoints package initializer
│   │   │   │   ├── organizations.py              # Org profile, member invites & role management
│   │   │   │   ├── projects.py                   # Project CRUD with OCC & Cache-Aside lookups
│   │   │   │   ├── tasks.py                      # Task CRUD (Offset + Keyset pagination, OCC updates)
│   │   │   │   ├── teams.py                      # Team management & team membership associations
│   │   │   │   └── ws.py                         # Authenticated WebSocket stream (/ws/projects/{id})
│   │   │   ├── api.py                            # V1 Router aggregator (mounts all endpoint routers)
│   │   │   └── __init__.py                       # V1 package initializer
│   │   ├── deps.py                               # Dependency injection: TenantContext, Auth, RequireRole
│   │   └── __init__.py                           # API package initializer
│   ├── core                                      # Cross-cutting foundational modules
│   │   ├── cache.py                              # Redis CacheService (Typed Pydantic models, SCAN deletion)
│   │   ├── config.py                             # Pydantic v2 settings & computed DSN properties
│   │   ├── database.py                           # SQLAlchemy 2.0 AsyncEngine & QueuePool manager
│   │   ├── exceptions.py                         # Domain exception hierarchy (RFC 7807 problem details)
│   │   ├── __init__.py                           # Core package initializer
│   │   ├── logging.py                            # Structlog JSON processor & request context bindings
│   │   ├── middleware.py                         # Request tracing (X-Request-ID), timing & error handler
│   │   ├── pagination.py                         # Base64 Keyset Cursor encoder & decoder
│   │   ├── rate_limit.py                         # Sliding-window RateLimiter using Redis Sorted Sets
│   │   ├── redis.py                              # Async Redis client & TokenBlacklistService (revocation)
│   │   ├── security.py                           # Argon2id password hashing & JWT token encoder/decoder
│   │   └── telemetry.py                          # Prometheus metrics & Instrumentator configuration
│   ├── models                                    # Declarative SQLAlchemy 2.0 async domain models
│   │   ├── audit.py                              # Notification & JSONB AuditLog models
│   │   ├── base.py                               # Reusable mixins: UUID, Timestamp, SoftDelete, TenantScoped
│   │   ├── enums.py                              # Python 3.11 StrEnums: OrgRole, TaskStatus, Priority, etc.
│   │   ├── __init__.py                           # Central model registry (exported to Base.metadata)
│   │   ├── organization.py                       # Organization & OrganizationMember (Role matrix) models
│   │   ├── project.py                            # Project model (with OCC version_id)
│   │   ├── task.py                               # Task, Subtask, Comment, Attachment models
│   │   ├── team.py                               # Team & TeamMember models
│   │   └── user.py                               # User identity model with hashed credentials
│   ├── repositories                              # Data access layer (Tenant-scoped database queries)
│   │   ├── attachment.py                         # AttachmentRepository (task-scoped queries)
│   │   ├── audit.py                              # AuditLogRepository (filtering by entity, actor, date)
│   │   ├── base.py                               # Generic BaseRepository & TenantScopedRepository
│   │   ├── comment.py                            # CommentRepository with chronological cursor feeds
│   │   ├── __init__.py                           # Repositories package initializer
│   │   ├── organization.py                       # Organization & OrganizationMember repositories
│   │   ├── project.py                            # ProjectRepository with key uniqueness checks
│   │   ├── task.py                               # TaskRepository with dual pagination & filter builders
│   │   ├── team.py                               # TeamRepository with member eager-loading
│   │   └── user.py                               # UserRepository with email lookups & eager loading
│   ├── schemas                                   # Pydantic v2 validation & serialization contracts
│   │   ├── attachment.py                         # Presigned upload/download & attachment schemas
│   │   ├── audit.py                              # AuditLogResponse & AuditLogFilterParams schemas
│   │   ├── auth.py                               # Registration, Login, Token, UserResponse schemas
│   │   ├── comment.py                            # Comment request and response schemas
│   │   ├── common.py                             # RFC 7807 ProblemDetailResponse, HealthResponse, Readiness
│   │   ├── __init__.py                           # Schemas package initializer
│   │   ├── organization.py                       # Organization update & member invite schemas
│   │   ├── pagination.py                         # Generic OffsetPageResponse & CursorPageResponse envelopes
│   │   ├── project.py                            # Project request/response with expected_version
│   │   ├── task.py                               # Task request/response, filter & sorting schemas
│   │   └── team.py                               # Team request and response schemas
│   ├── services                                  # Business logic & UnitOfWork transaction boundaries
│   │   ├── auth.py                               # AuthService (Atomic registration, token rotation, logout)
│   │   ├── base.py                               # BaseService & UnitOfWork transaction context manager
│   │   ├── comment.py                            # CommentService with author/admin permission guards
│   │   ├── __init__.py                           # Services package initializer
│   │   ├── organization.py                       # Organization membership management service
│   │   ├── project.py                            # ProjectService with OCC version check & AuditLog recording
│   │   ├── queue.py                              # JobQueueService (ARQ async client dispatcher)
│   │   ├── storage.py                            # S3StorageService (AWS SigV4 Presigned PUT/GET URLs)
│   │   ├── task.py                               # TaskService with OCC atomic status updates & AuditLog
│   │   └── team.py                               # TeamService with team member associations
│   ├── websockets                                # Real-time communication subsystem
│   │   ├── hub.py                                # WebSocketHub with dynamic Redis Pub/Sub horizontal bus
│   │   └── __init__.py                           # WebSockets package initializer
│   ├── workers                                   # Background asynchronous task queue (ARQ)
│   │   ├── arq_app.py                            # ARQ WorkerSettings & scheduled cron maintenance config
│   │   ├── __init__.py                           # Workers package initializer
│   │   └── tasks.py                              # Background worker jobs & soft-delete GC sweepers
│   ├── __init__.py                               # App package initializer
│   └── main.py                                   # FastAPI ASGI factory, lifespan manager & Prometheus mount
├── docker                                        # Containerization & orchestration files
│   ├── docker-compose.yml                        # Multi-service stack (API, Worker, Postgres, Redis, MinIO)
│   ├── Dockerfile                                # Multi-stage minimal runner with non-root saasuser
│   ├── .dockerignore                             # Build context exclusion rules (Docker context folder)
│   └── entrypoint.sh                             # Container startup entrypoint (runs Alembic migrations)
├── .github                                       # CI/CD Automation
│   └── workflows
│       └── ci.yml                                # GitHub Actions workflow (Lint, Type, Migrations, Test)
├── tests                                         # Automated async integration & security test suite
│   ├── conftest.py                               # Isolated NullPool & Redis cleanup test harness
│   ├── test_audit_occ_maintenance.py             # Phase 7: Audit queries, Project OCC, and Sweeper tests
│   ├── test_auth_rbac.py                         # Phase 3: Registration, login, token rotation, RBAC tests
│   ├── test_caching_rate_limit_jobs.py           # Phase 5: Cache-Aside & 429 rate limit tests
│   ├── test_concurrency_race.py                  # Phase 8: 10x simultaneous OCC race condition tests
│   ├── test_domain_models.py                     # Phase 2: Database constraints & OCC concurrency tests
│   ├── test_files_and_websockets.py              # Phase 6: S3 Presigned URLs & Attachments tests
│   ├── test_foundation.py                        # Phase 1: Middleware & RFC 7807 error format tests
│   ├── test_multi_tenant_api.py                  # Phase 4: Multi-tenant isolation & REST API tests
│   ├── test_observability.py                     # Phase 9: /healthz, /readyz & Prometheus /metrics tests
│   └── test_security_hardening.py                # Phase 8: Cross-tenant attack, JWT tampering & SQLi tests
├── alembic.ini                                   # Alembic CLI & logging configuration
├── .dockerignore                                 # Root build context exclusion rules
├── .env                                          # Local environment variables (Ignored by Git)
├── .env.example                                  # Template for required environment variables
├── .gitignore                                    # Git exclusion rules
├── .pre-commit-config.yaml                       # Git pre-commit hooks (Ruff, Mypy)
├── pyproject.toml                                # Build system, dependency bounds, Ruff & Mypy configs
└── README.md                                     # Production documentation & architecture manual
```

---

## Quickstart & Local Development

### Prerequisites
* **Python 3.11+**
* **Docker & Docker Compose**

### 1. Clone Repository & Setup Environment
```bash
git clone https://github.com/IT2411/multi_tenant_saas.git
cd multi_tenant_saas

# Copy configuration template
cp .env.example .env
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python3.11 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev]"
```

### 3. Launch Infrastructure (PostgreSQL, Redis, MinIO)
```bash
docker compose -f docker/docker-compose.yml up -d postgres redis minio
```

### 4. Apply Database Migrations
```bash
alembic upgrade head
```

### 5. Start Development Server & Background Worker
```bash
# Terminal 1: FastAPI API Server (Hot-Reload)
uvicorn app.main:app --reload --port 8000

# Terminal 2: ARQ Background Task Worker
arq app.workers.arq_app.WorkerSettings
```

---

## Production Deployment via Docker Compose

To boot the complete production stack (4-Worker API Server, ARQ Background Worker, PostgreSQL 16, Redis 7, and MinIO):

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

Verify service health:
```bash
docker compose -f docker/docker-compose.yml ps
```

---

## Interactive Documentation & Telemetry

* **Interactive Swagger UI**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
* **ReDoc Documentation**: [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)
* **Liveness Probe**: [http://localhost:8000/api/v1/healthz](http://localhost:8000/api/v1/healthz)
* **Readiness Probe**: [http://localhost:8000/api/v1/readyz](http://localhost:8000/api/v1/readyz)
* **Prometheus Metrics**: [http://localhost:8000/metrics](http://localhost:8000/metrics)
* **MinIO Storage Console**: [http://localhost:9001](http://localhost:9001) (`minioadmin` / `minioadminpassword`)

---

## Testing & Quality Control Gates

Run the comprehensive linting, type-checking, and test harness:

```bash
# 1. Linting & Formatting Quality Gate
ruff check app tests && ruff format --check app tests

# 2. Strict Static Type Analysis
mypy app

# 3. Full Async Pytest Suite with Coverage Report
pytest --cov=app --cov-report=term-missing tests/
```

---

## API Summary & Key Capabilities

### 1. Authentication (`/api/v1/auth`)
* `POST /register`: Registers user with Argon2id hashing, creates workspace, and assigns `owner` role.
* `POST /login`: Validates credentials with sliding-window rate limiting (5 attempts/min) and returns access (`15m`) and refresh (`7d`) tokens.
* `POST /refresh`: Rotates refresh tokens and blacklists previous token in Redis.
* `POST /logout`: Revokes refresh token immediately in Redis.
* `GET /me`: Returns profile and active organization memberships.

### 2. Multi-Tenant Projects & Teams (`/api/v1/projects`, `/api/v1/teams`)
* `POST /projects`: Provisions project with unique key validation per organization.
* `GET /projects/{id}`: High-speed Cache-Aside read from Redis.
* `PATCH /projects/{id}`: Optimistic Concurrency Control update with `expected_version` validation and cache invalidation.
* `POST /teams` & `POST /teams/{id}/members`: Organizes members into collaborative units.

### 3. Tasks & Real-Time Comments (`/api/v1/tasks`)
* `POST /tasks`: Creates task, commits atomic transaction, and broadcasts `TASK_CREATED` to WebSocket room.
* `GET /tasks`: Offset-paginated query with multi-field sorting, ILIKE search, and filter criteria.
* `GET /tasks/feed`: Keyset/Cursor pagination for high-volume infinite scroll feeds.
* `PATCH /tasks/{id}`: OCC concurrency status update emitting `TASK_UPDATED` event.
* `POST /tasks/{id}/comments`: Adds comment and broadcasts `COMMENT_ADDED` event.

### 4. S3 / MinIO Presigned File Storage (`/api/v1/tasks/{id}/attachments`)
* `POST /presigned-upload`: Generates AWS SigV4 presigned `PUT` upload URL.
* `POST /`: Confirms upload and records metadata.
* `GET /`: Returns presigned `GET` download URLs with expiration.

### 5. Real-Time WebSockets (`/api/v1/ws`)
* `WS /ws/projects/{project_id}?token=<JWT>`: Authenticated WebSocket stream with Redis Pub/Sub horizontal scaling.

### 6. Audit Trail (`/api/v1/audit-logs`)
* `GET /audit-logs`: Queries complete before/after state diffs stored in PostgreSQL JSONB with actor eager loading.

---

## Security Hardening Matrix

- [x] **Password Security**: Quantum/GPU-resistant Argon2id password hashing.
- [x] **Token Lifecycle**: Short-lived JWT access tokens (`15m`) with rotating refresh tokens (`7d`).
- [x] **Stateful Revocation**: Instant token blacklisting in Redis with automatic TTL expiration.
- [x] **Tenant Scoping**: All queries strictly constrained by `organization_id`.
- [x] **Direct S3 Isolation**: File uploads/downloads bypass the API server via presigned URLs.
- [x] **SQL Injection Defense**: Parameterized SQLAlchemy 2.0 query compilation.
- [x] **Traffic Shaping**: Sliding-window rate limiters backed by Redis Sorted Sets.
- [x] **Concurrency Guard**: Optimistic Concurrency Control (`version_id`) on Projects and Tasks.
- [x] **Container Hardening**: Multi-stage minimal runtime running under non-root user `saasuser:10001`.

---

## License

Distributed under the MIT License. See `LICENSE` for details.