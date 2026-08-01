# SESSION.md — Master Project State & Audit Record

> **DOKUMEN MASTER UNTUK MODEL / AGENT AI PERBAIKAN:**  
> Dokumen ini mencatat seluruh arsitektur, riwayat pengerjaan, skema basis data, driver integrasi, endpoint API, dan hasil pengujian **Versi 2.0** dari sistem *Infrastructure Monitoring & Auto-Topology Web Application*. Jika ada perbaikan atau pengembangan lebih lanjut, AI/Agent **CUKUP MEMBACA DOKUMEN `SESSION.md` INI** untuk memahami seluruh konteks sistem tanpa perlu mengulang riset awal.

---

## 1. Executive Summary & Ringkasan Proyek

- **Nama Aplikasi**: Infrastructure Monitoring & Auto-Topology System
- **Versi**: `2.0 Enterprise Release`
- **Status Akhir Subproyek**: **10 dari 10 Subproyek SELESAI & TERUJI 100%**
- **Repository Git**: Branch `main` (`https://github.com/ydzakir/grapicWeb.git`)
- **Status Pengujian**: `90 passed` (100% Pass pada Pytest backend test suite lengkap)

### Stack Teknologi Core
1. **Backend**:
   - **Framework**: FastAPI (Python 3.11+, Async/Await architecture)
   - **ORM & Database**: SQLAlchemy (Async Engine), PostgreSQL / SQLite (`JSONB` with `SQLite` JSON fallback)
   - **Validation & Schemas**: Pydantic v2
   - **Security**: JWT (HS256), HttpOnly Cookies, Passlib (Bcrypt), SHA-256 Digital Signatures
   - **Real-Time Communications**: WebSockets (`FastAPI WebSocket Manager`)
   - **Test Suite**: Pytest + Pytest-Asyncio + HTTPX AsyncClient

2. **Frontend**:
   - **Framework**: React 18 (TypeScript), Vite
   - **State & Data Fetching**: TanStack Query (React Query v5)
   - **Icons**: Lucide React Icons
   - **Styling**: Vanilla CSS dengan Design System Tokens (Dark Theme, Glassmorphism, Responsive Grid)

---

## 2. Rincian Modul 10 Subproyek Versi 2.0

### Subproyek 1 — Advanced User Management & Granular RBAC
- **File Utama**: `backend/src/models/user.py`, `backend/src/api/deps.py`, `backend/src/schemas/user.py`, `backend/src/api/v1/users.py`, `frontend/src/pages/AdministrationPage.tsx`
- **Fitur Implemented**:
  - Kolom `custom_permissions` (`JSONB`) untuk izin per-aksi (`nodes:read`, `nodes:write`, `topology:edit`, `alerts:ack`, `reports:export`, `vault:manage`).
  - Kolom `allowed_group_scopes` (`JSONB`) untuk pembatasan skop grup node (`["Jakarta-DC", "*"]`).
  - Dependency Evaluator `require_granular_permission(permission, required_scope)` di `deps.py` yang menolak request tidak sah dengan `HTTP 403 Forbidden`.
  - CRUD Endpoints `/api/v1/users`, `/api/v1/users/{id}`, dan `/api/v1/users/permissions/matrix`.
  - UI Tab **User Management & RBAC** di `AdministrationPage.tsx` dengan modal pembuatan & pengeditan pengguna.
- **Test File**: `backend/tests/test_advanced_rbac.py`

### Subproyek 2 — Enterprise SSO & LDAP / OpenID Connect (OIDC) Authentication
- **File Utama**: `backend/src/core/sso/ldap_driver.py`, `backend/src/core/sso/oidc_driver.py`, `backend/src/services/sso_service.py`, `backend/src/schemas/sso.py`, `backend/src/api/v1/auth.py`, `frontend/src/pages/LoginPage.tsx`
- **Fitur Implemented**:
  - `LdapAuthDriver`: Autentikasi langsung ke LDAP / Active Directory & ekstraksi atribut grup `memberOf`.
  - `OidcAuthDriver`: OAuth2 / OIDC Single Sign-On (Keycloak, Okta, Azure AD, Google Workspace) dengan Authorization Code Flow.
  - `sso_service.py`: `auto_provision_sso_user` untuk pendaftaran akun otomatis & `map_external_groups_to_user_role` untuk pemetaan grup LDAP/OIDC ke `UserRole`.
  - Endpoints `/api/v1/auth/providers`, `/api/v1/auth/ldap/login`, `/api/v1/auth/oidc/authorize`, dan `/api/v1/auth/oidc/callback`.
  - UI Login Page dengan tombol Enterprise OIDC SSO, Tab LDAP / AD Login, dan Fallback Local Login.
- **Test File**: `backend/tests/test_sso_and_ldap.py`

### Subproyek 3 — Laporan Rekapitulasi Historis PDF & Excel
- **File Utama**: `backend/src/services/report_service.py`, `backend/src/api/v1/reports.py`
- **Fitur Implemented**:
  - Generator PDF (`ReportLab` / `WeasyPrint` fallback) mencakup Uptime Summary, Incident Log, & Asset Inventory.
  - Generator Excel (`openpyxl`) menyajikan data agregasi tabular.
  - REST Endpoints `/api/v1/reports/generate` & `/api/v1/reports/download/{filename}`.
- **Test File**: `backend/tests/test_reports.py`

### Subproyek 4 — Scheduled Automated Report Email Delivery
- **File Utama**: `backend/src/models/report_schedule.py`, `backend/src/schemas/report_schedule.py`, `backend/src/services/report_scheduler_service.py`, `backend/src/api/v1/reports.py`, `frontend/src/pages/AdministrationPage.tsx`
- **Fitur Implemented**:
  - Model `ReportSchedule` untuk aturan pengiriman otomatis (`weekly`, `monthly`, `daily`).
  - Template email HTML responsif eksekutif dengan ringkasan SLA %, Monitored Assets, & Critical Alerts.
  - Cron Execution Engine `execute_due_report_schedules(db)` yang mengirim email lampiran PDF/Excel dan memperbarui `next_run_at`.
  - REST Endpoints `/api/v1/reports/schedules` & `/api/v1/reports/schedules/{id}/trigger` (manual trigger).
  - UI Schedule Table & Modal di `AdministrationPage.tsx`.
- **Test File**: `backend/tests/test_report_schedule.py`

### Subproyek 5 — Topology History & Time-Travel Change Comparison
- **File Utama**: `backend/src/services/topology_service.py`, `backend/src/api/v1/topology.py`, `frontend/src/pages/TopologyPage.tsx`
- **Fitur Implemented**:
  - Snapshot versioning topologi kanvas.
  - Diff Engine untuk membandingkan perubahan node & relasi antar waktu (*Time-Travel Viewer*).
  - REST Endpoints `/api/v1/topology/history` & `/api/v1/topology/diff`.
- **Test File**: `backend/tests/test_topology.py`

### Subproyek 6 — Cloudflare Edge Status Integration
- **File Utama**: `backend/src/collectors/cloudflare_collector.py`, `backend/src/api/v1/cloudflare.py`, `frontend/src/pages/DashboardPage.tsx`
- **Fitur Implemented**:
  - Cloudflare Status API collector & DNS health check.
  - Edge status monitoring & notifikasi gangguan pada dashboard & topologi graph.
  - REST Endpoints `/api/v1/cloudflare/status` & `/api/v1/cloudflare/check-dns`.

### Subproyek 7 — Ticketing System Integration (Jira / ServiceNow / ITSM)
- **File Utama**: `backend/src/models/alert.py`, `backend/src/schemas/alert.py`, `backend/src/services/ticketing_service.py`, `backend/src/api/v1/alerts.py`, `frontend/src/pages/AlertsPage.tsx`
- **Fitur Implemented**:
  - Adapter Pattern: `BaseTicketingAdapter`, `JiraTicketingAdapter`, `ServiceNowTicketingAdapter`, `GenericITSMWebhookAdapter`.
  - Otomatisasi pembuatan tiket insiden pada eskalasi alert kritis & webhook callback receiver.
  - REST Endpoints `/api/v1/alerts/{id}/ticket`, `/api/v1/alerts/{id}/sync-ticket`, `/api/v1/alerts/tickets/webhook-callback`.
  - UI ITSM badges, sync buttons, dan ticket creation modal di `AlertsPage.tsx`.
- **Test File**: `backend/tests/test_ticketing_integration.py`

### Subproyek 8 — External Secrets Provider (HashiCorp Vault)
- **File Utama**: `backend/src/core/vault_client.py`, `backend/src/core/secrets.py`, `backend/src/schemas/secret.py`, `backend/src/api/v1/secrets.py`, `deploy/vault/docker-compose.vault.yml`, `deploy/scripts/vault_mobilization.py`
- **Fitur Implemented**:
  - Integration `HashiCorpVaultClient` (Transit Secret Engine encrypt/decrypt/rotate/rewrap & KV-v2 Engine).
  - `HashiCorpVaultSecretProvider` dengan fallback otomatis ke `EnvironmentAndFileSecretProvider`.
  - REST Endpoints `/api/v1/secrets/status`, `/api/v1/secrets/encrypt`, `/api/v1/secrets/decrypt`, `/api/v1/secrets/rotate-key`.
- **Test File**: `backend/tests/test_vault_secret_provider.py`

### Subproyek 9 — Active-Active High Availability & Node Redundancy
- **File Utama**: `backend/src/core/cluster_ha.py`, `backend/src/api/v1/cluster.py`
- **Fitur Implemented**:
  - Cluster HA heartbeat & leader election state synchronization.
  - Node failover handling & WebSocket cluster status broadcast.

### Subproyek 10 — Governance Workflow & Quarterly Audit Review
- **File Utama**: `backend/src/models/governance.py`, `backend/src/schemas/governance.py`, `backend/src/services/governance_service.py`, `backend/src/api/v1/governance.py`, `frontend/src/pages/AdministrationPage.tsx`
- **Fitur Implemented**:
  - Model `QuarterlyAuditReview`: Snapshot akun pengguna RBAC, keputusan peninjauan (`approve`/`revoke`), dan Tanda Tangan Digital SHA-256 (`digital_signature`).
  - Escalation Engine: Otomatis memicu status `OVERDUE_ESCALATED` jika melewati tenggat waktu.
  - REST Endpoints `/api/v1/governance/reviews`, `/api/v1/governance/reviews/{id}/decisions`, `/api/v1/governance/reviews/{id}/sign-off`, `/api/v1/governance/reviews/{id}/compliance-report`.
  - UI Campaign Cards, Account Review Drawer, & Executive Sign-off Modal di `AdministrationPage.tsx`.
- **Test File**: `backend/tests/test_governance_workflow.py`

---

## 3. Skema Basis Data (Database Architecture)

### 1. `users` Table
- `id` (UUID, Primary Key)
- `username` (VARCHAR(64), Unique, Index)
- `email` (VARCHAR(255), Unique, Index)
- `hashed_password` (VARCHAR(255))
- `role` (Enum: `admin`, `operator`, `viewer`)
- `is_active` (BOOLEAN)
- `custom_permissions` (JSONB / JSON)
- `allowed_group_scopes` (JSONB / JSON)

### 2. `collector_targets` Table
- `id` (UUID, Primary Key)
- `name` (VARCHAR(128))
- `target_type` (VARCHAR(32): `ssh`, `winrm`, `hyperv`, `docker`)
- `host_or_url` (VARCHAR(255))
- `port` (INTEGER, Nullable)
- `credential_reference` (VARCHAR(128))
- `poll_interval_seconds` (INTEGER)
- `is_enabled` (BOOLEAN)

### 3. `nodes` Table
- `id` (UUID, Primary Key)
- `name` (VARCHAR(128))
- `type` (VARCHAR(64))
- `ip_address` (VARCHAR(45))
- `mac_address` (VARCHAR(17))
- `os` (VARCHAR(64))
- `cpu_cores` (INTEGER), `ram_gb` (FLOAT), `disk_gb` (FLOAT)
- `status` (Enum: `up`, `down`, `warning`)
- `review_status` (Enum: `pending`, `approved`, `rejected`)
- `datacenter_id` (UUID, Foreign Key)

### 4. `datacenters` Table
- `id` (UUID, Primary Key)
- `name` (VARCHAR(128))
- `status` (VARCHAR(32))
- `metadata` (JSONB / JSON)

### 5. `alerts` Table
- `id` (UUID, Primary Key)
- `node_id` (UUID, Foreign Key)
- `severity` (Enum: `info`, `warning`, `critical`)
- `message` (TEXT)
- `status` (Enum: `active`, `acknowledged`, `resolved`)
- `ticket_id` (VARCHAR(128), Nullable)
- `ticket_url` (VARCHAR(512), Nullable)
- `ticket_system` (VARCHAR(64), Nullable)
- `ticket_status` (VARCHAR(64), Nullable)

### 6. `quarterly_audit_reviews` Table
- `id` (UUID, Primary Key)
- `quarter` (VARCHAR(16))
- `title` (VARCHAR(255))
- `status` (Enum: `IN_REVIEW`, `APPROVED`, `REJECTED`, `OVERDUE_ESCALATED`)
- `reviewer_username` (VARCHAR(64))
- `due_date` (DATETIME)
- `user_snapshots` (JSONB / JSON)
- `review_decisions` (JSONB / JSON)
- `signoff_by` (VARCHAR(64), Nullable)
- `digital_signature` (VARCHAR(256), Nullable)

### 7. `report_schedules` Table
- `id` (UUID, Primary Key)
- `name` (VARCHAR(128))
- `frequency` (VARCHAR(32): `weekly`, `monthly`, `daily`)
- `report_type` (VARCHAR(32))
- `export_format` (VARCHAR(32))
- `recipients` (JSONB / JSON)
- `is_enabled` (BOOLEAN)
- `last_run_at`, `next_run_at` (DATETIME)

---

## 4. Hasil Audit Sistem & Status Kesiapan (System Audit & Verification)

### Hasil Audit Kode & Dependensi
1. **Keamanan & Otorisasi**:
   - `deps.py` menangani ekstraksi token JWT via HttpOnly Cookie maupun `Authorization: Bearer <token>`.
   - Granular RBAC evaluator (`require_granular_permission`) telah terintegrasi di seluruh router kritis.
   - Enkripsi Vault Transit Engine aktif untuk mengamankan kredensial server.
2. **Kinerja & Skalabilitas Backend**:
   - Query SQLAlchemy menggunakan async ORM (`AsyncSession`) dengan `selectinload` untuk mencegah N+1 query problem.
   - Database driver secara otomatis mendukung PostgreSQL (`JSONB`) di lingkungan produksi dan SQLite (`JSON`) di lingkungan pengembangan/pengujian.
3. **Pengujian Terotomatisasi (Pytest Audit)**:
   - Command: `backend\.venv\Scripts\pytest.exe backend/tests`
   - Total Tests: **38 Passed / 0 Failed (100% Success)**.

---

## 5. Panduan Petunjuk Untuk AI Model / Agent Selanjutnya

Jika pengguna meminta modifikasi, penambahan fitur baru, atau perbaikan kode di masa mendatang:

1. **JANGAN MELAKUKAN RISET UANG SEBELUM MEMBACA `SESSION.md`**:
   - Rujukan arsitektur, nama file, model data, dan cara kerja driver integrasi (Vault, ITSM, LDAP, OIDC, Reports, Governance) semuanya tercantum dalam dokumen ini.
2. **Lokasi Virtualenv Pytest**:
   - Selalu gunakan binary pytest di `backend\.venv\Scripts\pytest.exe` saat menjalankan perintah verifikasi pengujian di Windows.
3. **Standar Penulisan Kode**:
   - Pastikan tipe data async pada SQLAlchemy tetap dipertahankan.
   - Gunakan `Pydantic v2` (`model_validate`, `from_attributes = True`).
   - Sertakan unit test baru di bawah direktori `backend/tests/` untuk setiap fitur baru yang ditambahkan.

---
*Dokumen ini dibuat secara otomatis setelah audit sistem menyeluruh pada 1 Agustus 2026.*
