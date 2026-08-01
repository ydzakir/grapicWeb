# Laporan Audit Aplikasi — Perspektif End-User / Operator

> **Tanggal Audit**: 1 Agustus 2026
> **Auditor**: AI Code Review (berperan sebagai end-user / IT Operations yang menjalankan aplikasi)
> **Metode**: Perbandingan dokumentasi (`docs/`) terhadap implementasi aktual (`backend/`, `frontend/`, `deploy/`), eksekusi test suite, dan verifikasi konfigurasi.

---

## Ringkasan Eksekutif

Aplikasi **Infrastructure Monitoring & Auto-Topology (V2.0 Enterprise)** memiliki fondasi arsitektur dan autentikasi yang **kuat**, dan **seluruh 90 test backend lulus**. Namun dari sudut pandang end-user yang mencoba **menjalankan dan memakai aplikasi**, ditemukan **banyak kesalahan penerapan (implementation gaps) antara dokumentasi dan kode**, termasuk beberapa **fitur yang diklaim selesai tetapi tidak berfungsi sama sekali** karena tidak pernah dipanggil/diwirless-kan:

| Klaim | Realita |
|---|---|
| "10/10 subproyek SELESAI & TERUJI 100%" | 2 fitur **mati total** (metrics exporter, HA cluster), beberapa fitur hanya "partial/kosmetik" |
| "90/90 test passing" | Benar (backend), tapi **frontend build GAGAL** (TypeScript error) dan 1 test frontend **gagal** |
| "Prometheus memantau metrics" | Prometheus di-setup untuk scrape port 8001 yang **tidak pernah dijalankan** → **tidak ada data metrics** |
| "Live WebSocket status delta" | Manager & endpoint ada, tapi **tidak ada kode yang memanggil broadcast** → UI **tidak pernah menerima update live** |
| "Scheduled report email delivery" | Engine ada, tapi **tidak pernah dijadwalkan/di-cron** oleh worker → email laporan **tidak pernah terkirim** |
| "Alerting engine" | Evaluasi alert **tidak pernah dipanggil** oleh worker/backend → **tidak ada alert yang muncul** secara otomatis |

**Kesimpulan**: Aplikasi saat ini adalah **"MVP + fitur jalan di level kode/tests, tetapi belum terintegrasi menjadi sistem yang berfungsi end-to-end"**. End-user yang mencoba menjalankan stack produksi akan menemukan dashboard kosong (tanpa metrics, tanpa alert, tanpa update live).

---

## 1. Temuan KRITIS — Fitur Klaim Selesai Tetapi Mati Total

### 🔴 K-1. Metrics Prometheus Tidak Pernah Dihidupkan (Pelanggaran REQ-M5-01, REQ-M5-04)
- **Dok**: `prometheus.yml` di-scrape `collector-worker:8001`; RTM menandai `metrics_exporter.py` sebagai IMPLEMENTED_VERIFIED.
- **Kode**: Fungsi `start_worker_metrics_server()` di `backend/src/collectors/metrics_exporter.py:102` **tidak pernah dipanggil**. `worker.py` hanya menulis file heartbeat, tanpa memanggil exporter atau `update_node_metrics()`.
- **Dampak end-user**: Endpoint `/api/v1/metrics` selalu mengembalikan **"No telemetry data recorded"** di panel detail node; grafik historis kosong; dashboard metrics tidak bermakna. Fitur inti monitoring **tidak berfungsi**.
- **Bukti**: `backend/src/worker.py:1-64` tidak ada import/call `metrics_exporter`. `rg` hanya menemukan definisi, bukan pemanggilan.

### 🔴 K-2. WebSocket "Live Status" Tidak Pernah Mengirim Delta (Pelanggaran REQ-M5-04)
- **Dok**: `WS /ws/status` mengirim `status_delta`; RTM menandai test lulus.
- **Kode**: `broadcast_status_delta()` di `websocket_manager.py:31` **tidak dipanggil di mana pun** kecuali definisinya. Worker setelah mengubah status node tidak mengirim delta.
- **Dampak end-user**: Status node berubah di DB, tetapi browser **tidak pernah diperbarui secara real-time**. Animasi "status pulse / traffic flow" di Topology **tidak pernah terpicu** oleh data live. Indikator "Live WS" hanya menunjukkan koneksi terbuka, bukan data mengalir.

### 🔴 K-3. Alert Engine Tidak Pernah Dijalankan (Pelanggaran REQ-V11-01 s.d. REQ-V11-08)
- **Dok**: Threshold CPU/RAM/Disk + DOWN>2m, dedup 15m, eskalasi 15m, notifikasi, auto-resolve.
- **Kode**: `evaluate_node_telemetry_alerts()` (`alert_service.py:20`) **hanya dipanggil dari test**, tidak dari worker maupun scheduler. `worker.py` tidak memanggilnya.
- **Dampak end-user**: Halaman `/alerts` selalu kosong; **tidak ada peringatan saat server down / resource tinggi** — fitur utama "monitoring" ini buta. Acknowledge/escalation/ticketing otomatis tidak pernah terpicu.

### 🔴 K-4. Report Scheduler (Cron Email) Tidak Pernah Dijadwalkan (Pelanggaran SP4)
- **Dok**: "Cron Engine Pengiriman Laporan Periodik".
- **Kode**: `execute_due_report_schedules()` (`report_scheduler_service.py:240`) ada, **tidak dipanggil dari worker atau proses cron apa pun**. Worker tidak menjalankannya.
- **Dampak end-user**: Jadwal laporan yang dibuat admin di UI **tidak pernah berjalan otomatis**. Email mingguan/bulanan **tidak pernah terkirim**. (Catatan: `EmailNotificationProvider` juga hanya menulis log, tidak mengirim email asli.)

### 🔴 K-5. HA Cluster (SP9) "100% Teruji" Tetapi Tidak Ada Kode-nya
- **Dok**: `SESSION.md` & `task_checklist_v2.0.md` menyatakan SP9 SELESAI; file utama `backend/src/core/cluster_ha.py` & `backend/src/api/v1/cluster.py`.
- **Kode**: **Kedua file tersebut TIDAK ADA** (`Test-Path` = False). Yang ada hanya `deploy/scripts/dr_failover.py` (skrip probe) + `docker-compose.ha.yml` + test `test_ha_dr.py` yang hanya mengetes skrip probe & config settings — **bukan cluster backend**.
- **Dampak end-user**: HA Compose memiliki 2 backend yang berbagi **state in-memory rate-limit & WebSocket manager terpisah**, tanpa leader election. Tidak ada "failover synchronization" yang diklaim.

---

## 2. Temuan TINGGI — Fitur "Kosmetik"/Tidak Lengkap

### 🟠 H-1. Database Migration Tidak Mencerminkan Skema Sebenarnya
- **Dok**: RTM REQ-M2 (Alembic migration) VERIFIED; `SESSION.md` mendokumentasikan tabel `datacenters`, `network_edges`, `subnets`, `alert_rules`, `alerts`, `notification_providers`, `report_schedules`, `quarterly_audit_reviews`, `topology_snapshots`, `topology_change_logs`, kolom `custom_permissions`, dll.
- **Kode**: Hanya **1 file migration** (`2026_07_30_0001_initial_schema.py`) yang membuat **6 tabel** (users, nodes, node_connections, collector_targets, collector_runs, audit_logs). **Tidak ada** migration untuk alert, network, report_schedule, governance, topology_history, custom_permissions.
- **Dampak end-user**: `alembic upgrade head` pada PostgreSQL kosong akan **gagal** saat query tabel `alerts`/`datacenters`/`network_edges` → **aplikasi error 500 di banyak halaman**. Yang selama ini "lulus" hanya karena test memakai SQLite `Base.metadata.create_all` (semua tabel dibuat), bukan migration.

### 🟠 H-2. Frontend Tidak Bisa Build (TypeScript Error) — README Mengklaim "0 build errors"
- **Bukti nyata**: `npm run build` gagal dengan 12 error, contoh:
  - `src/pages/AdministrationPage.tsx:389` — `apiClient.get` menerima 1 argumen, dipanggil 2 (kelebihan `responseType`).
  - `src/pages/AdministrationPage.tsx:507,510` — properti `host`/`enabled` **tidak ada** di tipe `CollectorTarget` (API mengembalikan `host`, frontend tipe memakai `host_or_url`). **Ini bug nyata**: target collector tidak akan tampil/tersusun benar di UI.
  - 7 import Lucide tidak terpakai + `getBadgeClass` tak terpakai.
- **Dampak end-user**: Developer/tim tidak bisa menghasilkan image production karena build frontend gagal; klaim README tidak akurat.

### 🟠 H-3. Frontend Test Gagal + E2E Tidak Ada Dukungan
- **Bukti nyata**: `npm test` → **1 dari 4 test gagal** (`App.test.tsx`: "redirects unauthenticated user to Login Page" tidak menemukan teks). README mengklaim "4 component tests passed".
- `frontend/e2e/smoke.spec.ts` **mengimpor `@playwright/test` tetapi Playwright TIDAK ada di devDependencies**, dan menguji teks `'InfraTopology MVP'` yang sebenarnya muncul di **Navbar (component), bukan di Login page** → E2E tidak dapat dijalankan.

### 🟠 H-4. CORS + Auth Cookie tidak konsisten dengan frontend
- **Dok**: Auth pakai HttpOnly cookie (aman). `deps.py` mendukung cookie.
- **Kode/frontend**: `apiClient.ts` mengirim `Authorization: Bearer <token>` dari **localStorage**, sedangkan backend login men-set **HttpOnly cookie**. Cookie HttpOnly tidak bisa dibaca JS, jadi token disimpan di localStorage (rawan XSS), dan **cookie tidak dipakai** untuk request fetch. Dua mekanisme paralel = kebingungan & risiko.

### 🟠 H-5. Skema `CollectorTarget` (backend vs frontend) mismatch
- Backend model memakai `host` + `enabled`; `SESSION.md` & tipe frontend memakai `host_or_url` + `is_enabled`. Frontend menampilkan `target.host || target.host_or_url` → **"undefined"** muncul di kartu target.

---

## 3. Temuan SEDANG — Masalah Kemudahan Penggunaan End-User

### 🟡 M-1. Tidak Ada Demo/Seed Mode (Klaim Dokumen Ada)
- **Dok**: Build Prompt Modul 8 & Deployment Guide §6.3: `python -m seed_demo`.
- **Kode**: **File `seed_demo.py` TIDAK ADA**. End-user tidak bisa mengisi data demo untuk mencoba aplikasi; dashboard & topology kosong.

### 🟡 M-2. Kredensial Default Dikompromikan
- `docker-compose.yml`, `docker-compose.ha.yml`, `.env.example`, `config.py` semuanya punya **default password yang sama**: `POSTGRES_PASSWORD=change_this_in_production_secure_pass_123`, `SECRET_KEY=change_this_to_a_secure_random_64_char_string_for_production`, `BOOTSTRAP_ADMIN_PASSWORD=AdminSecurePass123!`.
- `README.md` **mempublikasikan** kredensial default admin & LDAP. Vault dev memakai token `root`. Untuk produksi publik, ini **risiko keamanan serius** (default password tidak berubah → langsung bisa login).

### 🟡 M-3. Docker Compose tidak bisa dijalankan apa adanya (runtime worker/image)
- Image `infra-monitoring-worker:0.1.0` harus di-build dari Dockerfile yang sama (berisi CMD uvicorn). Perintah compose worker `python src/worker.py` butuh `PYTHONPATH=/app/src` — di compose **tidak disetel `PYTHONPATH`** → worker kemungkinan **import error** (`ModuleNotFoundError: collectors`). (Backend saja yang disetel di Dockerfile; worker jalankan via CMD tanpa PYTHONPATH.)
- Nginx HA (`deploy/nginx/default.conf`) menunjuk `upstream backend_app { server backend:8000; }` sedangkan di HA compose service bernama `backend-1`/`backend-2` → **reverse proxy HA salah arah**.
- `docker-compose.ha.yml` **tidak disertakan** dalam alur dokumen ("docker compose up -d" di README memakai compose dasar), jadi HA stack tidak teruji.

### 🟡 M-4. Topology/Inventory menampilkan data "pending" yang salah sasaran
- Dashboard `totalServers` ikut menghitung `hyperv_vm` sebagai server → angka menyesatkan. `unhealthyNodes` juga menghitung semua node (termasuk pending).
- Subnet auto-scan (`scan_subnet_ip_range`) membuat node dengan nama `PHYSICAL-SERVER-AUTO-<suffix>` yang **langsung tidak lolos naming convention** → semua jadi pending dengan validation issue; bukan kesalahan fatal, tapi menambah pekerjaan admin.

### 🟡 M-5. Tidak Ada Uptime / Trend Data Riil
- Dashboard tidak menampilkan "average uptime" (FR-13) dan tidak ada data historis karena K-1. Panel detail hanya chart kosong.

### 🟡 M-6. Endpoint /report & /secrets tanpa proteksi scope yang konsisten
- `/api/v1/reports/generate` dan `/download` hanya `get_current_user` (semua role), sementara aturan RBAC (`reports:export`) tidak diterapkan di endpoint (hanya didaftarkan di permissions matrix). Operator/viewer tanpa izin bisa generate laporan.

### 🟡 M-7. Dokumentasi operasional tidak akurat
- `docs/Operations_Backup_Monitoring.md` merujuk restore ke database `monitoring_db_disposable` dengan `PASSWORD` placeholder; perintah `docker exec -it infra_postgres psql` memakai password **belum diganti**.
- `docs/Deployment_and_Operations_Guide.md` memakai placeholder repo `infra-monitoring-topology` (seharusnya `grapicWeb`), dan `alembic upgrade head` belum tentu jalan karena H-1.

---

## 4. Apa yang Benar-Benar Berfungsi (Poin Positif)

- ✅ **Auth lokal**: Login/logout/JWT + HttpOnly cookie + rate-limit (in-memory) + audit log bekerja & teruji.
- ✅ **RBAC dasar**: `require_role` & granular permissions evaluator di `deps.py` diterapkan konsisten; test authorization lulus.
- ✅ **Inventory API & approval flow**: list/filter/paginate, approve/reject/archive, validasi naming convention, audit trail — berfungsi (terbukti test).
- ✅ **Topology builder & React Flow canvas**: nodes+edges, hierarchy auto-layout (dagre), pan/zoom, legend, detail panel — kode matang.
- ✅ **Vault adapter**: `HashiCorpVaultSecretProvider` dengan fallback env/file, dan klien Transit/KV — rapi; test `test_vault_secret_provider.py` lulus.
- ✅ **Backup script**: `backup_db.py` + `restore_db.py` valid; test restore ke disposable DB lulus.
- ✅ **Report PDF/Excel generator**: benar-benar menghasilkan file (terbukti ada file di `reports_storage/` + test lulus).
- ✅ **Security headers & non-root container**: Nginx & backend menerapkan hardening (X-Frame-Options, nosniff, user non-root).
- ✅ **90 test backend lulus** (pytest).

---

## 5. Prioritas Perbaikan (Untuk Dijadikan Prompt)

### Prioritas P0 (Sistem tidak berfungsi tanpa ini)
1. **Wire metrics pipeline**: panggil `start_worker_metrics_server(8001)` + `update_node_metrics()` di worker; tambahkan metric endpoint health; pastikan Prometheus scrape sukses.
2. **Wire alert engine**: panggil `evaluate_node_telemetry_alerts()` pada siklus worker; buat konfigurasi threshold default ter-deploy.
3. **Wire WebSocket broadcast**: kirim `StatusDeltaMessage` setelah status node berubah (up/down/unknown) ke `status_ws_manager.broadcast_status_delta()`.
4. **Wire report scheduler**: panggil `execute_due_report_schedules()` secara periodik (APScheduler/loop di worker).
5. **Perbaiki migration**: buat migration Alembic baru untuk seluruh tabel (alerts, network, report_schedules, governance, topology_history, custom_permissions) atau pindah ke `create_all` + dokumentasi.
6. **Perbaiki frontend build**: update tipe `CollectorTarget` (host/enabled), perbaiki `apiClient.get` di `handleDownloadReport`, bersihkan unused imports; jalankan `tsc` hingga 0 error.

### Prioritas P1 (Produksi & keamanan)
7. Hapus/mengganti default credentials & secret; jangan publikasikan kredensial di README.
8. Selesaikan/mundurkan klaim SP9 (HA) — jangan klaim "selesai" tanpa file `cluster_ha.py`; perbaiki `upstream` Nginx HA agar menunjuk `backend-1`/`backend-2`.
9. Tambahkan `PYTHONPATH=/app/src` pada service worker di compose.
10. Sediakan `seed_demo.py` (dokumen sudah menyebutnya) atau tambahkan seed API.

### Prioritas P2 (Pengalaman end-user)
11. Perbaiki definisi "total servers" di Dashboard (exclude VM dari count server; exclude pending).
12. Terapkan RBAC `reports:export`/`alerts:ack` ke endpoint terkait.
13. Rapikan dokumentasi (nama repo, placeholder password, prosedur yang mencerminkan migration nyata).
14. Tambahkan Playwright ke devDependencies dan perbaiki e2e selector (Login page tidak menampilkan brand text).

---

## Lampiran: Bukti Verifikasi

| Item | Perintah | Hasil |
|---|---|---|
| Backend test | `backend\.venv\Scripts\pytest.exe backend/tests -q` | `90 passed` |
| Frontend test | `npm test` | `3 passed, 1 failed` |
| Frontend build | `npm run build` | **Gagal** (12 TS error) |
| Compose config | `docker compose config` | OK (tanpa Docker daemon) |
| Docker stack | `docker compose up -d` | Gagal (Docker Desktop daemon tidak berjalan di env audit) |
| File HA | `Test-Path backend/src/core/cluster_ha.py` | **False** |
| File seed | `Test-Path backend/src/seed_demo.py` | **False** |
| Call metrics | `rg "start_worker_metrics_server"` | hanya definisi |
| Call broadcast | `rg "broadcast_status_delta"` | hanya definisi |
| Call alert eval | `rg "evaluate_node_telemetry_alerts"` | hanya definisi + tests |
| Call report cron | `rg "execute_due_report_schedules"` | hanya definisi |

---

*Laporan ini disusun sebagai dasar penyusunan prompt perbaikan. Setiap temuan merujuk pada file/baris konkret agar dapat ditindaklanjuti.*
