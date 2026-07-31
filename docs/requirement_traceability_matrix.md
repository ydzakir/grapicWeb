# Requirement Traceability Matrix (RTM)

Matriks penelusuran kebutuhan (*Requirement Traceability Matrix*) untuk proyek **Infrastructure Monitoring & Auto-Topology**.

---

## Matriks Penelusuran Modul & Fitur MVP

| ID Kebutuhan | Deskripsi Kebutuhan | Modul | Status Implementation | Bukti Verifikasi (Test File / Command) |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-M1-01** | Inisialisasi struktur proyek monorepo backend, frontend, docs, deploy | Modul 1 | `IMPLEMENTED_VERIFIED` | Folder structure check, `docker-compose.yml` |
| **REQ-M1-02** | Stack backend FastAPI + PostgreSQL + SQLAlchemy 2 + Alembic | Modul 1 | `IMPLEMENTED_VERIFIED` | `backend/src/main.py`, `backend/alembic/` |
| **REQ-M1-03** | Local user authentication with JWT token & RBAC roles | Modul 1 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_auth_and_rbac.py` |
| **REQ-M1-04** | Admin user bootstrap idempotency | Modul 1 | `IMPLEMENTED_VERIFIED` | `test_admin_bootstrap_idempotency` PASS |
| **REQ-M2-01** | Extensible collector framework & normalized discovery schemas | Modul 2 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_collector_framework.py` |
| **REQ-M2-02** | Collector adapters (Fake, SSH Linux, WinRM Windows, Docker TLS) | Modul 2 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_collector_adapters.py` |
| **REQ-M2-03** | Collector Target Management REST API & credential vault ref | Modul 2 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_collector_api.py` |
| **REQ-M2-04** | Test connection functionality without plain secret disclosure | Modul 2 | `IMPLEMENTED_VERIFIED` | `test_test_connection_fake_target` PASS |
| **REQ-M3-01** | Collector worker scheduler with bounded concurrency & retry | Modul 3 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_scheduler_and_status.py` |
| **REQ-M3-02** | Status transition tracking (UP, DOWN, WARNING, UNKNOWN) | Modul 3 | `IMPLEMENTED_VERIFIED` | `test_status_transition_matrix` PASS |
| **REQ-M3-03** | Worker heartbeat file update & liveness probe | Modul 3 | `IMPLEMENTED_VERIFIED` | `test_worker_heartbeat` PASS |
| **REQ-M4-01** | Inventory upsert idempotency & canonical identity matching | Modul 4 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_inventory_and_topology.py` |
| **REQ-M4-02** | Canonical topology relationships (DC -> Host -> VM / Container) | Modul 4 | `IMPLEMENTED_VERIFIED` | `test_datacenter_assignment` PASS |
| **REQ-M4-03** | Single canonical host decision (No shadow nodes) | Modul 4 | `IMPLEMENTED_VERIFIED` | `test_single_canonical_host_no_shadow_nodes` PASS |
| **REQ-M4-04** | Host naming convention validation (`[TYPE]-[LOKASI]-[FUNGSI]-[NOMOR]`) | Modul 4 | `IMPLEMENTED_VERIFIED` | `test_host_naming_convention_validation` PASS |
| **REQ-M4-05** | Node lifecycle retention (`archived` 90 days before deletion) | Modul 4 | `IMPLEMENTED_VERIFIED` | `test_archive_lifecycle_retention` PASS |
| **REQ-M4-06** | Topology cycle defense algorithm (DFS cycle detection) | Modul 4 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_cycle_defense.py` PASS |
| **REQ-M5-01** | Prometheus pull model exporter worker (`:8001/metrics`) | Modul 5 | `IMPLEMENTED_VERIFIED` | `backend/src/collectors/metrics_exporter.py` |
| **REQ-M5-02** | Prometheus 90-day retention & stale-series cleanup | Modul 5 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_metrics_and_websocket.py` |
| **REQ-M5-03** | Metrics Query API (`GET /api/v1/metrics`) with allowlist validation | Modul 5 | `IMPLEMENTED_VERIFIED` | `test_metrics_query_endpoint` PASS |
| **REQ-M5-04** | WebSocket live status delta endpoint (`WS /ws/status`) | Modul 5 | `IMPLEMENTED_VERIFIED` | `test_websocket_authenticated_status_delta` PASS |
| **REQ-M6-01** | UI Auth flow, protected routing, and RBAC visibility | Modul 6 | `IMPLEMENTED_VERIFIED` | `frontend/src/tests/auth.test.tsx` PASS |
| **REQ-M6-02** | Dashboard page (Summary cards, mini-topology, unhealthy list) | Modul 6 | `IMPLEMENTED_VERIFIED` | `frontend/src/pages/DashboardPage.tsx` |
| **REQ-M6-03** | Inventory page (Paginated table, search, filters, admin approval modal) | Modul 6 | `IMPLEMENTED_VERIFIED` | `frontend/src/tests/inventory.test.tsx` PASS |
| **REQ-M6-04** | Topology canvas with React Flow + Dagre auto-layout | Modul 6 | `IMPLEMENTED_VERIFIED` | `frontend/src/pages/TopologyPage.tsx` |
| **REQ-M6-05** | Node Detail side panel with Recharts time-series chart | Modul 6 | `IMPLEMENTED_VERIFIED` | `frontend/src/pages/TopologyPage.tsx` |
| **REQ-M6-06** | WebSocket status delta integration to React Query cache | Modul 6 | `IMPLEMENTED_VERIFIED` | `frontend/src/hooks/useWebSocketStatus.ts` |
| **REQ-M6-07** | Administration page (Target CRUD, test connection, DC management) | Modul 6 | `IMPLEMENTED_VERIFIED` | `frontend/src/pages/AdministrationPage.tsx` |
| **REQ-M7-01** | Security audit, HTTP Security Headers, and non-root Docker execution | Modul 7 | `IMPLEMENTED_VERIFIED` | `backend/src/main.py`, `deploy/nginx/default.conf` |
| **REQ-M7-02** | Failure simulations (DB outage, Prometheus 504/502, collector error) | Modul 7 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_reliability_and_failures.py` PASS |
| **REQ-M7-03** | Scale benchmark (50 hosts + 200 containers = 250+ nodes) | Modul 7 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_scale_benchmark.py` PASS |
| **REQ-M7-04** | Automated PostgreSQL daily backup & disposable restore test | Modul 7 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_backup_restore.py` PASS |
| **REQ-M7-05** | Operations guide & external uptime checking documentation | Modul 7 | `IMPLEMENTED_VERIFIED` | `docs/Operations_Backup_Monitoring.md` |
| **REQ-RM-01** | Multi-Prometheus HA cluster & Thanos 1-year downsampling | Roadmap | `DEFERRED_TO_ROADMAP` | Documented in `Deployment_and_Operations_Guide.md` |
| **REQ-RM-02** | Dynamic network packet traffic animation on topology canvas | Roadmap | `DEFERRED_TO_ROADMAP` | Documented in `Deployment_and_Operations_Guide.md` |
| **REQ-RM-03** | Advanced alerting notification engine (PagerDuty/Slack webhooks) | Roadmap | `DEFERRED_TO_ROADMAP` | Documented in `Deployment_and_Operations_Guide.md` |

---

## Ringkasan Verifikasi
- Total Requirements: **35**
- Implemented & Verified: **32 (91.4%)**
- Deferred to Roadmap: **3 (8.6%)**
- Out of Scope: **0**
