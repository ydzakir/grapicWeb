# Prompt Perbaikan — Remediasi Aplikasi Monitoring (Agar Sesuai PRD)

> **Gunakan dokumen ini sebagai prompt induk** untuk sesi perbaikan (oleh AI agent / engineer).
> Baca seluruh dokumen di bawah ini **sebelum** menyentuh kode.

---

## A. Konteks & Sumber Kebenaran

Baca dan patuhi urutan prioritas berikut jika ada konflik:

1. `docs/audit_enduser_report.md` — **daftar temuan yang wajib diperbaiki** (basis prompt ini).
2. `docs/PRD.md` — tujuan produk yang harus dicapai.
3. `docs/Rules.md` — aturan wajib (keamanan, interval, retensi, dsb).
4. `docs/Architecture.md` & `docs/Design.md` — desain & arsitektur.
5. `docs/Antigravity-Build-Prompt.md` — kontrak MVP & stage gate.
6. `docs/requirement_traceability_matrix.md` — status requirement, perbarui setelah perbaikan.
7. `SESSION.md` — catatan master status proyek, **wajib diperbarui** setiap selesai modul.

---

## B. Tugas Utama & Definisi Selesai

Tujuannya: **aplikasi benar-benar berjalan end-to-end sesuai PRD** (inventarisasi, status real-time, metrics via Prometheus, alerting otomatis, topologi, laporan periodik terjadwal, dan web UI yang build & berfungsi).

**Definisi Selesai (harus semua):**
- [ ] `docker compose config` valid, dan `docker compose up -d --build` sukses dengan semua service `healthy`.
- [ ] Worker benar-benar mem-bootstrap Prometheus exporter, memproses status, mengirim alert, dan menjalankan cron report.
- [ ] WebSocket mengirim delta nyata; UI menampilkan update live.
- [ ] `alembic upgrade head` sukses pada **PostgreSQL kosong**.
- [ ] `backend\.venv\Scripts\pytest.exe backend/tests` → **100% pass**.
- [ ] `cd frontend && npm run build` → **0 error**; `npm test` → **100% pass**.
- [ ] `SESSION.md`, `docs/task_checklist_*.md`, dan RTM diperbarui; setiap modul **di-commit & di-push ke GitHub** (`origin`, branch `main`).
- [ ] Tidak ada secret/kredensial default yang bocor; tidak ada fitur "mati" (dead code yang tidak dipanggil).

---

## C. Aturan Kerja & Workflow Wajib

1. **Satu modul per sesi kerja.** Selesaikan, verifikasi, baru lanjut ke modul berikut. Jangan melompat.
2. **Setelah setiap modul selesai, lakukan "Stage Gate" wajib:**
   - Jalankan formatter/lint/type check: backend `ruff` + `mypy`, frontend `npm run lint` + `tsc`.
   - Jalankan seluruh test: `backend\.venv\Scripts\pytest.exe backend/tests` dan `npm test`.
   - Jalankan `docker compose config` bila menyentuh Docker.
   - Catat hasil aktual (bukan perkiraan). Jika gagal, perbaiki di modul yang sama sampai hijau.
3. **Update SESSION.md setiap selesai modul:**
   - Perbarui: ringkasan eksekutif, status subproyek, skema DB (jika berubah), hasil audit, panduan untuk AI berikutnya, dan tanggal.
   - Jangan menghapus riwayat; tambahkan bagian "Changelog Perbaikan" yang baru.
4. **Commit & Push ke GitHub setelah setiap modul hijau:**
   - `git status` → `git diff` → hanya stage file yang relevan → commit dengan pesan jelas (`fix(metrics): wire Prometheus exporter into worker`).
   - `git push origin main`.
   - Jangan commit file secret, `reports_storage/`, `*.db`, `node_modules`, `.venv`, `.env`.
5. **TDD untuk behavior penting:** tulis test gagal dulu → implementasi minimal → test hijau → refactor.
6. **Jangan menghapus/perubahan yang tidak Anda buat.** Laporkan file berubah + keputusan + bukti verifikasi di akhir setiap modul.

---

## D. Modul Perbaikan (Urut)

### MODUL R1 — Metrics Pipeline (P0) 🔴
**Target:** FR-5, FR-6, NFR-1, REQ-M5-01/02/03; memperbaiki temuan K-1.

Tugas:
1. Di `backend/src/worker.py`: panggil `start_worker_metrics_server(8001)` saat startup (guard `try/except`).
2. Setelah setiap siklus poll berhasil: untuk setiap node, kumpulkan `NormalizedMetricsResult` (panggil `adapter.collect_metrics()` di `backend/src/collectors/scheduler.py`) lalu kirim ke `update_node_metrics(node_id, status, cpu_usage_ratio=..., ram_usage_bytes=..., ...)` dari `backend/src/collectors/metrics_exporter.py`.
3. Panggil `remove_node_metrics(node_id)` untuk node yang di-archive/dihapus (stale-series cleanup) — pastikan dipanggil dari alur archive.
4. Pastikan label prometheus memakai **stable node UUID** sebagai label identity (bukan hostname bebas).
5. Pastikan `deploy/prometheus/prometheus.yml` scrape target `collector-worker:8001` valid dan worker membuka port tersebut (tambahkan `EXPOSE 8001` di Dockerfile backend bila perlu).
6. Verifikasi: curl `http://collector-worker:8001/metrics` mengembalikan `infra_cpu_usage_ratio{node_id="..."}`; `/api/v1/metrics?node_id=&range=1h` mengembalikan datapoints nyata.

**AC:** Panel detail node di UI menampilkan grafik time-series yang berisi data (bukan "No telemetry data recorded").

### MODUL R2 — Alert Engine Wiring (P0) 🔴
**Target:** FR-7, Rules §4, REQ-V11-01..08; memperbaiki temuan K-3.

Tugas:
1. Di worker (`backend/src/worker.py` atau scheduler): setelah siklus poll, untuk setiap node ambil metrics terbaru lalu panggil `evaluate_node_telemetry_alerts(db, node, cpu_usage=..., ram_usage=..., disk_usage=...)` (`backend/src/services/alert_service.py`).
2. Pastikan status node `DOWN` > 2 menit memicu alert critical (jalur sudah ada, pastikan worker benar-benar menghasilkan status DOWN via `process_collector_failure`).
3. Jangan spam: pertahankan dedup 15 menit & auto-resolve (sudah ada di service — hanya perlu dipastikan dipanggil berulang).
4. Notification provider: saat ini semua provider default `log`. Untuk produksi, pastikan webhook/email provider dipilih dari konfigurasi environment (jangan hardcode `"log"` di `alert_service.py` bila env mengatur provider).
5. Verifikasi: buat node fake dengan threshold terlampaui → alert muncul di `/api/v1/alerts/active`.

**AC:** Halaman `/alerts` menampilkan alert otomatis tanpa aksi manual admin.

### MODUL R3 — WebSocket Live Delta (P0) 🔴
**Target:** FR-5, FR-11 (animasi), REQ-M5-04, REQ-V12-05/06; memperbaiki temuan K-2.

Tugas:
1. Setiap kali status sebuah node berubah (UP/DOWN/UNKNOWN/WARNING), bangun `StatusDeltaMessage` (`backend/src/schemas/metrics.py`) lalu panggil `await status_ws_manager.broadcast_status_delta(delta)` dari `backend/src/services/websocket_manager.py`.
   - Titik panggil yang paling tepat: `process_collector_success` / `process_collector_failure` di `backend/src/services/collector_service.py`, atau setelah update status di scheduler.
2. Pastikan delta hanya berisi field aman (node_id, name, type, status, last_seen, timestamp) — jangan bocorkan metadata sensitif.
3. Frontend (`frontend/src/hooks/useWebSocketStatus.ts`) sudah siap mengkonsumsi; pastikan URL yang dipakai (`/api/v1/ws/status?token=...`) cocok dengan endpoint backend (backend sudah mendaftarkan dua alias `/ws/status` dan `/api/v1/ws/status`).
4. Verifikasi: buka 2 browser; ubah status node (mis. fake collector failure) → status berubah di kedua browser tanpa reload.

**AC:** Status node berubah secara live di UI tanpa refresh; indikator "Live WS" berfungsi dan menerima pesan.

### MODUL R4 — Report Scheduler & Email (P0) 🔴
**Target:** FR-15, SP3 & SP4, Rules §6; memperbaiki temuan K-4.

Tugas:
1. Di worker, tambahkan async loop berkala (mis. tiap 60 detik) yang memanggil `execute_due_report_schedules(db)` dari `backend/src/services/report_scheduler_service.py`.
2. Perbaiki `EmailNotificationProvider` di `backend/src/services/notification_service.py` agar benar-benar mengirim via SMTP (`smtplib`/`aiosmtplib`) dengan konfigurasi env (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_TO`). Jangan hanya menulis log.
3. Pastikan `send_executive_report_email` melampirkan file PDF/Excel (attachment MIME) bukan sekadar metadata.
4. Konfigurasi default di `.env.example`: tambahkan variabel SMTP (dummy non-rahasia) + dokumentasi.

**AC:** Jadwal laporan yang dibuat admin ter-trigger otomatis dan mengirim email berisi lampiran.

### MODUL R5 — Alembic Migration Lengkap & Skema Benar (P0) 🔴
**Target:** REQ-M1-02, REQ-M2, NFR-5; memperbaiki temuan H-1 + mismatch enum.

Tugas:
1. Buat **migration Alembic baru** (jangan ubah yang lama tanpa alasan kuat) yang membuat seluruh tabel yang belum ada:
   - `alert_rules`, `alerts`, `notification_providers`
   - `subnets`, `network_edges`
   - `topology_snapshots`, `topology_change_logs`
   - `report_schedules`
   - `quarterly_audit_reviews`
   - tambahan kolom `custom_permissions`, `allowed_group_scopes` pada `users`
2. **Perbaiki mismatch enum `node_type`** (kritis): migration lama membuat enum `('data_center','physical_server','hypervisor_host','vm','docker_host','container')`, tetapi model `NodeType` menulis nilai `hyperv_host`, `hyperv_vm`, `docker_container`, `service`. Pada PostgreSQL asli ini akan **error saat insert**. Sinkronkan enum (migration + model) — pilih satu nilai kanonik dan buat mapping/alias yang konsisten di seluruh kode & frontend.
3. Sinkronkan `target_type`: frontend mengirim `'docker'`/`'hyperv'` tetapi backend enum hanya `ssh|winrm|docker_tls`. Buat mapping (mis. `hyperv → winrm`, `docker → docker_tls`) atau perluas enum, lalu sesuaikan `frontend/src/pages/AdministrationPage.tsx` & tipe.
4. Pastikan `alembic upgrade head` sukses di PostgreSQL kosong (uji nyata, bukan SQLite `create_all`).
5. Tambahkan test migration (jalankan `alembic upgrade` pada DB kosong dalam CI jika memungkinkan).

**AC:** `alembic upgrade head` sukses di Postgres kosong; app tidak error 500 saat query tabel baru; skema SESSION.md sinkron dengan DB.

### MODUL R6 — Frontend Build & Test Hijau (P0) 🔴
**Target:** REQ-M6-01..07; memperbaiki temuan H-2, H-3, H-5, M-3 (parsial).

Tugas:
1. Perbaiki semua error `tsc`:
   - `frontend/src/types/api.ts`: ubah `CollectorTarget` agar memakai `host` & `enabled` (sesuai backend) — atau tambahkan keduanya.
   - `frontend/src/pages/AdministrationPage.tsx:389`: `handleDownloadReport` memanggil `apiClient.get(url, { responseType: 'blob' })` (2 argumen) — ganti dengan helper `download()` terpisah (mis. `fetch` langsung dengan blob) karena `request()` hanya 1 argumen.
   - Baris 507/510: pakai `target.host`/`target.enabled` sesuai tipe.
   - Bersihkan unused imports (`Calendar`, `Key`, `Info`, `Terminal`, `Search`, `Activity`, `getBadgeClass`, `setSchedReportType`).
2. Perbaiki `frontend/src/tests/App.test.tsx` agar assert benar (teks `'InfraTopology MVP'` ada di Navbar, bukan di Login) — atau sesuaikan render.
3. Tambahkan `@playwright/test` ke `devDependencies` + skrip `e2e`; perbaiki `frontend/e2e/smoke.spec.ts` (Login page tidak menampilkan brand text — sesuaikan selector, mis. `h2` `Enterprise Infrastructure Monitoring`).
4. `npm run build` harus 0 error; `npm test` 100% pass.

**AC:** `npm run build` dan `npm test` sukses tanpa error; e2e dapat dijalankan.

### MODUL R7 — Keamanan & Secret (P1) 🟠
**Target:** Rules §3, REQ-M7-01, NFR-2; memperbaiki temuan M-2.

Tugas:
1. Hapus default password/secret yang lemah dari `docker-compose*.yml`, `core/config.py` (fallback), dan jangan publikasikan kredensial di `README.md` — ganti dengan placeholder `<GANTI_SAYA>` dan wajibkan `.env`.
2. `docker-compose*.yml`: ganti fallback `${VAR:-default_password}` dengan nilai yang **tidak bisa dipakai** (mis. wajib set, atau gagal startup bila kosong).
3. Vault dev (`deploy/vault/docker-compose.vault.yml`): ganti `VAULT_DEV_ROOT_TOKEN_ID: "root"` dengan token dari env; dokumentasikan pemakaian produksi (bukan dev mode).
4. Audit ulang: `rg -n "password|secret|token" --ignore-case` pada file yang di-commit untuk memastikan tidak ada secret nyata.
5. Terapkan RBAC: `reports:export` pada `/api/v1/reports/*`, `alerts:ack` pada acknowledge (temuan M-6).

**AC:** Tidak ada secret nyata di repo/image; login dengan default password tidak lagi berhasil pada produksi; RBAC granular diterapkan.

### MODUL R8 — Worker & Compose Production Correct (P1) 🟠
**Target:** REQ-M1, Docker Requirements; memperbaiki temuan M-3.

Tugas:
1. Tambahkan `PYTHONPATH=/app/src` dan `EXPOSE 8001` pada service `collector-worker` di compose (atau set di `worker.py` sys.path).
2. Perbaiki `deploy/nginx/default.conf` untuk HA: `upstream backend_app` harus menunjuk `backend-1:8000` & `backend-2:8000` (bukan `backend:8000`).
3. Pastikan `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` jalan; `docker compose ps` semua healthy (backend, worker, prometheus, frontend, reverse-proxy, postgres).
4. Pastikan `docker-compose.ha.yml` disebut eksplisit di dokumentasi (bukan tersembunyi).

**AC:** Stack produksi jalan dari instruksi dokumentasi; worker sehat (heartbeat + exporter 8001 aktif); HA compose dapat diverifikasi.

### MODUL R9 — Demo Seed & HA Status Jujur (P1/P2) 🟠
**Target:** Data Demo, SP9; memperbaiki temuan M-1, K-5.

Tugas:
1. Buat `backend/src/seed_demo.py` sesuai dokumen (Modul 8 / Deployment Guide §6.3): minimal 1 physical server, 1 Hyper-V host + VM, 1 Docker host + container, campuran status `up/warning/down/unknown`, campuran `pending/approved`. Jangan auto-aktif di produksi (guard `ENVIRONMENT`).
2. **HA (SP9):** Pilih salah satu dengan jujur:
   - **Opsi A (implementasi nyata):** buat `backend/src/core/cluster_ha.py` + `backend/src/api/v1/cluster.py` dengan leader election (mis. advisory lock PostgreSQL) + heartbeat + sinkronisasi state (rate-limit & WS manager per instance), lalu perbarui test.
   - **Opsi B (defer jujur):** tandai SP9 sebagai **Deferred to Roadmap** di `task_checklist_v2.0.md`, `README.md`, `SESSION.md`, dan RTM dengan alasan; jangan klaim "100% selesai". Hapus klaim yang menyesatkan.
3. Perbarui dokumentasi HA Compose: nyatakan batasan (state in-memory per instance) dengan jelas.

**AC:** Seed demo berfungsi (`python -m seed_demo`); status HA dokumentasi akurat & tidak menyesatkan.

### MODUL R10 — UX & Dokumentasi (P2) 🟡
**Target:** FR-13, FR-14; memperbaiki temuan M-4, M-5, M-7.

Tugas:
1. Perbaiki `DashboardPage.tsx`: definisi "total servers" jangan menghitung `hyperv_vm` sebagai server; `unhealthyNodes` jangan menghitung node `pending`; tampilkan "average uptime" bila data valid atau sembunyikan dengan jelas.
2. Subnet auto-scan (`network_discovery_service.scan_subnet_ip_range`): nama yang dihasilkan harus lolos naming convention (mis. `[TYPE]-AUTO-<DC>-<N>`), atau tandai dengan jelas sebagai pending review.
3. Perbaiki dokumentasi operasional: nama repo (`grapicWeb`), ganti placeholder password, sinkronkan prosedur migration nyata, perbaiki command yang merujuk DB/backup.

**AC:** Angka dashboard akurat; dokumentasi dapat diikuti end-user dari nol.

---

## E. Verifikasi Akhir (Stage Gate Keseluruhan)

Setelah semua modul:
1. Hapus cache & artifact: `backend/.venv`, `node_modules` boleh tetap, tapi pastikan tidak ada artifact build lokal di repo.
2. Dari kondisi bersih: `docker compose up -d --build` → semua service healthy.
3. `alembic upgrade head` di Postgres kosong sukses.
4. Login admin → dashboard berisi data seed; topology menampilkan node; klik node → grafik metrics berisi data.
5. Trigger fake failure → status berubah live via WebSocket → alert muncul di `/alerts`.
6. Buat jadwal laporan → trigger → email terkirim (cek log SMTP).
7. Seluruh test backend & frontend pass; build frontend sukses.
8. `git status` bersih (semua sudah commit), `git push origin main` sukses.
9. `SESSION.md` + `task_checklist_*.md` + RTM memperlihatkan status akurat (tidak ada klaim berlebihan).

**Laporan akhir:** ringkasan hasil, file berubah, bukti verifikasi (output aktual), requirement yang kini sesuai PRD, dan sisa risiko.

---

## F. Perintah Verifikasi Standar (copy-paste)

```powershell
# Backend
cd backend
.\.venv\Scripts\pytest.exe tests -q
.\.venv\Scripts\ruff.exe check src
.\.venv\Scripts\mypy.exe src

# Frontend
cd ..\frontend
npm run lint
npm run build
npm test

# Docker
docker compose config
docker compose up -d --build
docker compose ps

# Database migration (dalam container / mesin dengan akses DB)
alembic upgrade head

# Secret audit
rg -n -i "password|secret|token" --glob '!node_modules/**' --glob '!.venv/**' --glob '!*.db' .

# Git
git add -A
git commit -m "fix(<area>): <deskripsi singkat>"
git push origin main
```
