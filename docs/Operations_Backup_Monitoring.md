# Infrastructure Operations: Security, Reliability, Backup, and Monitoring

Dokumen panduan operasional untuk pengelolaan keamanan, pencadangan database, keandalan sistem, serta pemantauan independen (*external uptime checking*) pada sistem **Infrastructure Monitoring & Auto-Topology**.

---

## 1. Keamanan & Hardening (*Security Hardening*)

### 1.1 Isolasi Network & Akses Publik
- **Private Internal Bridge Network**: PostgreSQL (`infra_postgres`) dan Prometheus (`infra_prometheus`) berjalan secara terisolasi pada `internal_network` tanpa mempublikasikan port ke host publik (`ports` dibatasi).
- **Reverse Proxy Gateway**: Seluruh lalu lintas HTTP dan WebSocket dari luar disalurkan secara terpusat melalui Nginx reverse proxy (`infra_reverse_proxy`, port 80).
- **Security Headers**:
  - `X-Frame-Options: DENY` (Mencegah Clickjacking)
  - `X-Content-Type-Options: nosniff` (Mencegah MIME-type sniffing)
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`

### 1.2 Pengelolaan Credential Secret
- **No Plain Secret Disclosure**: Parameter kredensial target collector (password SSH/WinRM, TLS key) disimpan menggunakan **Credential Reference** (misal `secret:ssh-prod-key`). API backend dan UI Frontend **tidak pernah** menampilkan kembali isi plain text secret.
- **Non-Root Container Execution**:
  - Backend/Worker berjalan di bawah user non-root `appuser:appgroup` (UID/GID 10001).
  - Frontend Nginx berjalan di bawah `nginx-unprivileged` (port 8080 internal).

---

## 2. Prosedur Backup & Restore PostgreSQL

### 2.1 Jadwal Backup Otomatis Harian
Backup database dikonsolidasikan melalui script `deploy/scripts/backup_db.py` (atau `pg_dump`).

**Contoh Command Backup (Manual / Cron Job)**:
```bash
# Cron job harian (02:00 AM)
0 2 * * * python3 /app/deploy/scripts/backup_db.py --db-url "postgresql://monitoring_admin:PASSWORD@postgres:5432/monitoring_db" --output-dir /var/backups/postgres
```

### 2.2 Prosedur Restore ke Database Disposable
Untuk memverifikasi keabsahan berkas backup:
```bash
# 1. Buat database disposable sementara
docker exec -it infra_postgres psql -U monitoring_admin -c "CREATE DATABASE monitoring_db_disposable;"

# 2. Jalankan restore ke database disposable
python3 deploy/scripts/restore_db.py --backup-file ./backups/infra_backup_20260731_120000.sql --target-db-url "postgresql://monitoring_admin:PASSWORD@postgres:5432/monitoring_db_disposable"

# 3. Verifikasi jumlah record tabel
docker exec -it infra_postgres psql -U monitoring_admin -d monitoring_db_disposable -c "SELECT count(*) FROM nodes;"
```

---

## 3. Strategi Storage Prometheus (Named Volume & DR)

### 3.1 Prometheus Retention & Storage
- Prometheus dikonfigurasikan dengan `--storage.tsdb.retention.time=90d` untuk menyimpan time-series telemetry selama 90 hari.
- Berkas TSDB disimpan pada Named Volume Docker `prometheus_data`.

### 3.2 Batasan High Availability (HA) & Disaster Recovery
- **Disclaimer**: MVP Prometheus berjalan sebagai *single-instance Prometheus*. Tidak dijanjikan High-Availability (HA) cluster otomatis.
- **Strategi Backup Volume Prometheus**:
  - Untuk lingkungan produksi, disarankan melakukan snapshot harian pada volume `prometheus_data` atau mereplikasi folder `/prometheus` ke storage S3/block storage eksternal.
  - Jika container Prometheus crash atau di-restart, data time-series tetap persisten di Named Volume `prometheus_data`.

---

## 4. Pemantauan Eksternal (*External Uptime Checker*)

Untuk mendeteksi apabila keseluruhan stack monitoring mengalami pemadaman (*monitoring system outage*), gunakan external uptime checker independen yang berada di luar infrastruktur monitoring (contoh: **Blackbox Exporter**, **Uptime Kuma**, atau **Better Stack**).

### 4.1 Endpoint Health Probe
Targetkan probe eksternal ke endpoint liveness/readiness backend:
- `GET http://<PUBLIC-IP>/api/v1/health/live` (Exposed via Reverse Proxy)
- Expected Response: `HTTP 200 OK` `{"status": "live"}`
- Failure Alert Trigger: Uptime checker memberikan peringatan alert jika endpoint merespons `HTTP 5xx` atau `Timeout > 5s` selama 3 kali berturut-turut.

---

## 5. Metodologi Pengukuran Overhead CPU Collector (< 2% CPU)

Untuk memvalidasi bahwa agen/collector-worker tidak membebani host terkelola (target overhead CPU < 2%):

1. **Metode Baseline Measurement**:
   - Catat penggunaan CPU rata-rata pada host target sebelum collector run (`docker stats` / `top` / `cgroup`).
2. **Execution Monitoring**:
   - Jalankan polling collector (`SSH`, `WinRM`, atau `Docker TLS API`).
   - Ukur alokasi CPU time yang dikonsumsi oleh proses SSHD/WinRM daemon selama pengumpulan telemetry (1-3 detik).
3. **Formula Threshold**:
   $$\text{CPU Overhead Ratio} = \frac{\text{CPU Seconds Consumed by Collector Daemon}}{\text{Poll Interval Seconds} \times \text{Total CPU Cores}} \times 100\%$$
   Dengan interval poll 60 detik pada 4-core CPU, overhead daemon yang mengonsumsi 2 CPU seconds = $\frac{2}{60 \times 4} \times 100\% = 0.83\% < 2\%$.
