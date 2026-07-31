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
| **REQ-V11-01** | Alert Rule Engine (CPU >85%/95%, RAM >85%/95%, Disk >80%/90%, Node DOWN >2m) | V1.1 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_alert_engine.py` |
| **REQ-V11-02** | 15-minute Alert Deduplication logic | V1.1 | `IMPLEMENTED_VERIFIED` | `test_alert_threshold_evaluation_and_deduplication` PASS |
| **REQ-V11-03** | Auto-resolve & Resolve notification delivery | V1.1 | `IMPLEMENTED_VERIFIED` | `test_alert_threshold_evaluation_and_deduplication` PASS |
| **REQ-V11-04** | 15-minute Critical Escalation logic | V1.1 | `IMPLEMENTED_VERIFIED` | `test_critical_alert_escalation_after_15_minutes` PASS |
| **REQ-V11-05** | Modular Notification System (Log, Webhook, Email) | V1.1 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_notification_providers.py` PASS |
| **REQ-V11-06** | Alert REST APIs & Audit Trail ACK | V1.1 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_alert_api.py` PASS |
| **REQ-V11-07** | Historical Metrics Range Selector (1h, 24h, 7d, 30d) | V1.1 | `IMPLEMENTED_VERIFIED` | `frontend/src/pages/TopologyPage.tsx` |
| **REQ-V11-08** | Alerts Active Feed, History Log, and Rules UI | V1.1 | `IMPLEMENTED_VERIFIED` | `frontend/src/pages/AlertsPage.tsx` |

| **REQ-V12-01** | Network Discovery Adapters (SNMP / ARP table parser) | V1.2 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_network_discovery.py` PASS |
| **REQ-V12-02** | Edge Provenance & Confidence Rating (`high`, `medium`, `manual`) | V1.2 | `IMPLEMENTED_VERIFIED` | `backend/src/models/network.py` |
| **REQ-V12-03** | Manual Edge Fallback API & Audit Trail | V1.2 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_topology_modes.py` PASS |
| **REQ-V12-04** | Dual Topology Modes (`mode=hierarchy` vs `mode=network`) | V1.2 | `IMPLEMENTED_VERIFIED` | `backend/tests/test_topology_modes.py` PASS |
| **REQ-V12-05** | Status Pulse Animation on Node Status Transition | V1.2 | `IMPLEMENTED_VERIFIED` | `frontend/src/index.css` |
| **REQ-V12-06** | Animated Traffic Flow for Verified Active Edges | V1.2 | `IMPLEMENTED_VERIFIED` | `frontend/src/index.css` |
| **REQ-V12-07** | Animation Toggle & `prefers-reduced-motion` Compliance | V1.2 | `IMPLEMENTED_VERIFIED` | `frontend/src/pages/TopologyPage.tsx` |

| **REQ-V20-SP03-01** | PDF Executive Summary Report Generator (`ReportLab`) | V2.0 (SP3) | `IMPLEMENTED_VERIFIED` | `backend/tests/test_report_service.py` PASS |
| **REQ-V20-SP03-02** | Excel Workbook Report Generator (`openpyxl`) | V2.0 (SP3) | `IMPLEMENTED_VERIFIED` | `backend/tests/test_report_service.py` PASS |
| **REQ-V20-SP03-03** | Report REST API Generate & File Download | V2.0 (SP3) | `IMPLEMENTED_VERIFIED` | `backend/src/api/v1/reports.py` PASS |

| **REQ-V20-SP05-01** | Topology Snapshot Versioning & Persistence | V2.0 (SP5) | `IMPLEMENTED_VERIFIED` | `backend/tests/test_topology_history.py` PASS |
| **REQ-V20-SP05-02** | Time-Travel Snapshot Comparison & Diff Engine | V2.0 (SP5) | `IMPLEMENTED_VERIFIED` | `test_topology_snapshot_save_and_diff_comparison` PASS |
| **REQ-V20-SP05-03** | Snapshot History REST APIs & Take Snapshot Action | V2.0 (SP5) | `IMPLEMENTED_VERIFIED` | `backend/src/api/v1/topology.py` PASS |

---

## Ringkasan Verifikasi Final V2.0 (Subproyek 3 & 5)
- Total Requirements: **56**
- Implemented & Verified: **53 (94.6%)**
- Deferred to Roadmap: **3 (5.4%)**
- Out of Scope: **0**
