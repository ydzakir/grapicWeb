# Task Checklist - Infrastructure Monitoring & Auto-Topology MVP

## Overview
Tracking status and stage gates for Modules 0 to 8 of the Infrastructure Monitoring & Auto-Topology MVP.

---

## Module Tracking

### [x] Modul 0 - Analisis, Traceability, dan Baseline
- [x] Read and analyze PRD, Architecture, Design, Rules documents
- [x] Inspect existing workspace structure and git baseline
- [x] Create Task Artifact and Requirement Traceability Matrix
- [x] Resolve design conflicts and document explicit decisions
- [x] Define project file map and component responsibilities
- [x] Draft Module 1-8 implementation plan with test strategies
- [x] Define lint, type check, unit test, integration test, E2E, Docker build, and smoke test commands
- [x] Complete Stage Gate Modul 0 report (No implementation code written)

### [x] Modul 1 - Fondasi Proyek dan Docker Compose
- [x] Scaffold backend FastAPI service (liveness & readiness endpoints)
- [x] Scaffold collector-worker service with health check signal
- [x] Scaffold frontend React TypeScript Vite shell
- [x] Configure PostgreSQL 16+ and Prometheus containers
- [x] Configure Reverse Proxy (Caddy/Nginx) for HTTP/HTTPS/WebSocket
- [x] Create multi-stage non-root Dockerfiles
- [x] Create `docker-compose.yml` (dev) & `docker-compose.prod.yml` (production-like)
- [x] Configure internal networks, named volumes, health checks, startup retry/backoff
- [x] Pin image versions and dependencies (no `latest` tags)
- [x] Create `.env.example` and secret file handling setup
- [x] Setup baseline linting, formatting, type checking, and test runners
- [x] Verify `docker compose config` and run baseline stack smoke test

### [x] Modul 2 - Database, Authentication, dan RBAC Minimum
- [x] Implement SQLAlchemy 2 models and Alembic migrations (`nodes`, `node_connections`, `users`, `roles`, `audit_logs`, `collector_targets`)
- [x] Add DB constraints (UUID PK, hierarchy parent FK, unique identity, edge deduplication)
- [x] Implement hierarchy cycle prevention logic with tests
- [x] Test migration forward and rollback on clean DB
- [x] Implement idempotent admin bootstrap from secret/env reference
- [x] Implement secure authentication (HttpOnly session/cookies, Argon2/Bcrypt hashing)
- [x] Implement RBAC enforcement (`admin`, `operator`, `viewer`)
- [x] Implement audit logging (logins, node approvals, config changes without secret leakage)
- [x] Implement rate limiting / brute-force protection on login
- [x] Create unit & integration tests for models, auth, RBAC, cycle defense, and audit

### [x] Modul 3 - Collector Framework dan Discovery Adapter
- [x] Define unified Collector interface (normalized discovery & metrics contract)
- [x] Implement SSH adapter for Linux hosts (timeout 10s, host-key verification)
- [x] Implement WinRM / PowerShell Remoting adapter for Windows hosts
- [x] Implement Hyper-V read-only discovery adapter
- [x] Implement Docker Engine API adapter (Mutual TLS mandatory for remote TCP)
- [x] Implement Admin CRUD for Collector Targets (credential references only)
- [x] Implement Secret Provider boundary (Docker secrets for MVP, Vault-ready interface)
- [x] Implement scheduler: Status polling (30-60s, default 60s), Inventory scan (300s), Metrics (60s)
- [x] Implement bounded concurrency, retry with backoff & jitter
- [x] Implement status transition rules (1 timeout -> `unknown`, >2 min failure window -> `down`, success -> reset & update `last_seen`)
- [x] Implement new node discovery -> `review_status=pending`
- [x] Implement fake collector deterministik for test/demo
- [x] Mock seluruh akses jaringan pada automated test
- [x] Pastikan log terstruktur tidak memuat command output sensitif atau credential
- [x] Tambahkan test untuk CRUD/authorization collector target, test connection, normalisasi, timeout, retry limit, concurrency bound, idempotency key, pending review, unknown/down transition, recovery, dan invalid interval

### [x] Modul 4 - Inventory Service dan Topology Builder
- [x] Implement normalized inventory upsert (idempotent, single canonical host node per machine)
- [x] Implement relationship inference (Data Center -> Host -> VM / Container)
- [x] Implement host naming validation on approval (`[TYPE]-[LOKASI]-[FUNGSI]-[NOMOR]`)
- [x] Implement container display name formatting (`<docker-host>/<container-name>`)
- [x] Implement Nodes API (`GET /api/v1/nodes` with search, type/status/review_status filter, pagination)
- [x] Implement Node Detail & Children API (`GET /api/v1/nodes/{id}`, `GET /api/v1/nodes/{id}/children`)
- [x] Implement Admin Approval / Rejection API (`POST /api/v1/nodes/{id}/approve`, `/reject`)
- [x] Implement Data Center grouping CRUD and host assignment
- [x] Implement Topology Builder Engine (JSON graph, cycle protection, default approved-only view)
- [x] Implement lifecycle retention (`archived` 90 days before eligible deletion)
- [x] Implement topology changelog/event tracking

### [x] Modul 5 - Prometheus Metrics dan Live Status
- [x] Implement Prometheus pull model (worker exposes internal `/metrics` endpoint)
- [x] Configure Prometheus retention (min 90 days) and stale-series cleanup
- [x] Implement backend Prometheus query service (timeout, error mapping, allowlisted metrics/ranges)
- [x] Implement Metrics API (`GET /api/v1/metrics?node_id=&range=`)
- [x] Implement WebSocket endpoint (`WS /ws/status`) with auth & status delta schema
- [x] Create tests for metric querying, stale-series cleanup, and WebSocket delta delivery

### [x] Modul 6 - Frontend Dashboard, Inventory, dan Topology
- [x] Implement UI Auth flow, session handling, and route protection
- [x] Implement Role-Based UI rendering (Admin vs Operator vs Viewer)
- [x] Implement Administration view (Collector target CRUD, test connection, DC management)
- [x] Implement Dashboard page (Total servers/containers, unhealthy nodes, mini topology)
- [x] Implement Inventory page (Table, pagination, search, status/type filters, approval action)
- [x] Implement Topology canvas using React Flow + Dagre auto-layout (pan, zoom, fit view, node status colors & icons)
- [x] Implement Node Detail side panel with current/basic Recharts time-series
- [x] Connect WebSocket status delta to React Flow graph state (no full graph refetch)
- [x] Implement responsive layout, keyboard navigation, high-contrast, and `prefers-reduced-motion` support
- [x] Write component tests & Playwright E2E smoke tests

### [x] Modul 7 - Security, Reliability, Backup, dan Scale Validation
- [x] Conduct repository, image context, and log audit for plain secrets
- [x] Audit CORS, security headers, cookie flags, and non-root Docker execution
- [x] Validate graceful shutdown and DB/Prometheus outage recovery behavior
- [x] Create scale benchmark dataset (50 servers/VMs, 200+ containers) and test API response times
- [x] Implement daily PostgreSQL backup script & disposable DB restore test
- [x] Document external uptime checker and Prometheus retention guidelines
- [x] Run security dependency/image scanning and remediate high/critical issues

### [x] Modul 8 - End-to-End Acceptance dan Handover
- [x] Run full clean-environment stack deploy via Docker Compose
- [x] Execute DB migrations on fresh database & bootstrap admin user
- [x] Enable demo seed data explicitly
- [x] Execute full backend test suite, frontend unit tests, and Playwright E2E tests
- [x] Verify fake collector multi-run idempotency & status transition simulation
- [x] Verify stack restart without data loss
- [x] Complete final operational & technical documentation (Deployment, TLS, Secret provisioning, Onboarding, Backup/Restore, Troubleshooting)
- [x] Update Requirement Traceability Matrix to final verified status
