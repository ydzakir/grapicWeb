# Task Checklist — Version 1.1 (Alerting Engine, Exports, & Historical Metrics)

Dokumen pelacakan tugas untuk pengembangan fitur **Versi 1.1** aplikasi *Infrastructure Monitoring & Auto-Topology*.

---

## Stage Gates V1.1

### [x] V1.1 - Stage 1: Alert Rule Engine & Database Schema
- [x] Implement Alerting Database Schema (`alert_rules`, `alerts`, `notification_providers`)
- [x] Implement Alert Evaluation Engine service (CPU >85%/95% 5m, RAM >85%/95%, Disk >80%/90%, Node DOWN >2m)
- [x] Implement 15-minute Alert Deduplication logic
- [x] Implement Auto-resolve & Resolve notification delivery
- [x] Implement 15-minute Critical Escalation logic
- [x] Write unit & integration tests for Alert Engine in `backend/tests/test_alert_engine.py`

### [x] V1.1 - Stage 2: Modular Notification Provider System
- [x] Implement Base Notification Provider Interface
- [x] Implement Mock/Log Notification Provider (testable without credentials)
- [x] Implement Webhook Notification Provider
- [x] Implement Email (SMTP) Notification Provider
- [x] Write provider unit tests in `backend/tests/test_notification_providers.py`

### [x] V1.1 - Stage 3: Alert Management REST APIs
- [x] Implement Alert Rules API (`GET/POST /api/v1/alerts/rules`)
- [x] Implement Active Alerts & History API (`GET /api/v1/alerts/active`, `GET /api/v1/alerts/history`)
- [x] Implement Alert Acknowledge API (`POST /api/v1/alerts/{id}/acknowledge`) with audit tracking
- [x] Write API integration tests in `backend/tests/test_alert_api.py`

### [x] V1.1 - Stage 4: Frontend Historical Metrics & Alert Management UI
- [x] Implement Historical Metrics UI (Range 1h, 24h, 7d, 30d with Recharts)
- [x] Implement Active Alerts & History Page (`/alerts`) with filtering & ACK modal
- [x] Implement Alert Rules Management view for Admin/Operator
- [x] Write frontend component tests for Alert UI & Historical Range selector

### [x] V1.1 - Stage 5: Topology Canvas Snapshot Export (PNG/SVG/PDF)
- [x] Implement Topology Canvas Export layout with timestamp snapshot & legend
- [x] Implement Report generation view
- [x] Write frontend export utility tests

### [x] V1.1 - Stage 6: Security, Performance, & E2E Validation
- [x] Validate alert evaluation & historical query response time under 250+ node scale
- [x] Add E2E tests for Alert ACK flow, Rule creation, Historical selector
- [x] Update Requirement Traceability Matrix (`docs/requirement_traceability_matrix.md`) with V1.1 features
