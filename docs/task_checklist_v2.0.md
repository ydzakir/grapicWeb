# Task Checklist — Version 2.0 (Enterprise Governance, SSO, History, & High Availability)

Dokumen pelacakan tugas untuk perencanaan dan implementasi **Versi 2.0** aplikasi *Infrastructure Monitoring & Auto-Topology*.

---

## Modul Subproyek V2.0

### [x] Subproyek 1 — Advanced User Management & Granular RBAC (**SELESAI & TERUJI 100%**)
- [x] Implementasi Perizinan Granular (Node Group Scoping, Custom Role Definitions)
- [x] Interface Manajemen Pengguna & Peran Administratif
- [x] Pengujian Integrasi Access Control

### [x] Subproyek 2 — Enterprise SSO & LDAP / OpenID Connect (OIDC) Authentication (**SELESAI & TERUJI 100%**)
- [x] Driver Autentikasi LDAP / Active Directory & OAuth2/OIDC
- [x] Auto-provisioning User Profile & Role Mapping
- [x] Single Sign-On Flow & Fallback Authentication

### [x] Subproyek 3 — Laporan Rekapitulasi Historis PDF & Excel (**SELESAI & TERUJI 100%**)
- [x] Generator Laporan PDF (Uptime Summary, Incident Log, Asset Inventory)
- [x] Generator Export Data Excel / CSV
- [x] Endpoint REST API Download Laporan

### [x] Subproyek 4 — Scheduled Automated Report Email Delivery (**SELESAI & TERUJI 100%**)
- [x] Cron Engine Pengiriman Laporan Periodik (Mingguan / Bulanan)
- [x] Template Email Laporan Eksekutif HTML
- [x] Dashboard Pengaturan Jadwal Laporan

### [x] Subproyek 5 — Topology History & Time-Travel Change Comparison (**SELESAI & TERUJI 100%**)
- [x] Engine Versioning Snapshot Topologi (Diff Canvas)
- [x] UI Visualisasi Perbandingan Topologi Antar Waktu (Time-Travel Viewer)
- [x] Audit Log Perubahan Relasi & Perangkat

### [x] Subproyek 6 — Cloudflare Edge Status Integration (**SELESAI & TERUJI 100%**)
- [x] Collector Provider Cloudflare Status API & DNS Health Check
- [x] Tampilan Status Edge Cloudflare pada Dashboard & Topologi
- [x] Notifikasi Gangguan Edge Cloudflare


### [x] Subproyek 7 — Ticketing System Integration (Jira / ServiceNow / ITSM) (**SELESAI & TERUJI 100%**)
- [x] Adapter Webhook Ticketing (Otomasikan Pembuatan Tiket Insiden)
- [x] Sinkronisasi Status Tiket & Link Rujukan
- [x] Modal Membuat Tiket Manual dari Alert Detail

### [x] Subproyek 8 — External Secrets Provider (HashiCorp Vault) (**SELESAI & TERUJI 100%**)
- [x] Integrasi HashiCorp Vault Client (Transit Secret Engine)
- [x] Rotasi Kunci & Penyimpanan Kredensial Target Terenkripsi
- [x] Skrip Mobilisasi & Fallback Environment Secrets

### [x] Subproyek 9 — High Availability & Multi-Node Disaster Recovery (**SELESAI & TERUJI 100%**)
- [x] PostgreSQL Streaming Replication & PgBouncer Connection Pooling
- [x] Prometheus HA Cluster & Thanos Querier
- [x] Docker Compose High Availability Stack Architecture


### [x] Subproyek 10 — Governance Workflow & Quarterly Audit Review (**SELESAI & TERUJI 100%**)
- [x] Approval Workflow Review Akses RBAC Kuartalan
- [x] Audit Compliance Reporting & Sign-off Tracking
- [x] Reminder & Escalation Engine untuk Reviewer
