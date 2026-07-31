# Task Checklist — Version 2.0 (Enterprise Governance, SSO, History, & High Availability)

Dokumen pelacakan tugas untuk perencanaan dan implementasi **Versi 2.0** aplikasi *Infrastructure Monitoring & Auto-Topology*.

---

## Modul Subproyek V2.0

### [ ] Subproyek 1 — Advanced User Management & Granular RBAC
- [ ] Implementasi Perizinan Granular (Node Group Scoping, Custom Role Definitions)
- [ ] Interface Manajemen Pengguna & Peran Administratif
- [ ] Pengujian Integrasi Access Control

### [ ] Subproyek 2 — Enterprise SSO & LDAP / OpenID Connect (OIDC) Authentication
- [ ] Driver Autentikasi LDAP / Active Directory & OAuth2/OIDC
- [ ] Auto-provisioning User Profile & Role Mapping
- [ ] Single Sign-On Flow & Fallback Authentication

### [x] Subproyek 3 — Laporan Rekapitulasi Historis PDF & Excel
- [x] Generator Laporan PDF (Uptime Summary, Incident Log, Asset Inventory)
- [x] Generator Export Data Excel / CSV
- [x] Endpoint REST API Download Laporan

### [ ] Subproyek 4 — Scheduled Automated Report Email Delivery
- [ ] Cron Engine Pengiriman Laporan Periodik (Mingguan / Bulanan)
- [ ] Template Email Laporan Eksekutif HTML
- [ ] Dashboard Pengaturan Jadwal Laporan

### [ ] Subproyek 5 — Topology History & Time-Travel Change Comparison
- [ ] Engine Versioning Snapshot Topologi (Diff Canvas)
- [ ] UI Visualisasi Perbandingan Topologi Antar Waktu (Time-Travel Viewer)
- [ ] Audit Log Perubahan Relasi & Perangkat

### [ ] Subproyek 6 — Cloudflare Edge Status Integration
- [ ] Collector Provider Cloudflare Status API & DNS Health Check
- [ ] Tampilan Status Edge Cloudflare pada Dashboard & Topologi
- [ ] Notifikasi Gangguan Edge Cloudflare

### [ ] Subproyek 7 — Ticketing System Integration (Jira / ServiceNow / ITSM)
- [ ] Adapter Webhook Ticketing (Otomasikan Pembuatan Tiket Insiden)
- [ ] Sinkronisasi Status Tiket & Link Rujukan
- [ ] Modal Membuat Tiket Manual dari Alert Detail

### [ ] Subproyek 8 — External Secrets Provider (HashiCorp Vault)
- [ ] Integrasi HashiCorp Vault Client (Transit Secret Engine)
- [ ] Rotasi Kunci & Penyimpanan Kredensial Target Terenkripsi
- [ ] Skrip Mobilisasi & Fallback Environment Secrets

### [ ] Subproyek 9 — High Availability & Multi-Node Disaster Recovery
- [ ] PostgreSQL Streaming Replication & PgBouncer Connection Pooling
- [ ] Prometheus HA Cluster & Thanos Querier
- [ ] Docker Compose High Availability Stack Architecture

### [ ] Subproyek 10 — Governance Workflow & Quarterly Audit Review
- [ ] Approval Workflow Review Akses RBAC Kuartalan
- [ ] Audit Compliance Reporting & Sign-off Tracking
- [ ] Reminder & Escalation Engine untuk Reviewer
