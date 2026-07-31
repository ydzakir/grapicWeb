# Deployment and Operations Guide

Panduan Operasional dan Mobilisasi Produksi untuk Aplikasi **Infrastructure Monitoring & Auto-Topology**.

---

## 1. Prerequisites (Persyaratan Sistem)

### 1.1 Host Environment & Dependencies
- **Operating System**: Linux (Ubuntu 22.04 / RHEL 9 recommended) atau Windows Server 2022.
- **Docker Engine**: Version `24.0.0+`
- **Docker Compose**: Plugin version `v2.20.0+`
- **Hardware Resources Minimum**:
  - CPU: 2 Cores (4 Cores recommended for 200+ nodes)
  - RAM: 4 GB (8 GB recommended for 90-day Prometheus retention)
  - Storage: 50 GB SSD/NVMe (persisten untuk volume PostgreSQL & Prometheus TSDB)

---

## 2. Startup Development vs Production Deployment

### 2.1 Quick Development Startup
```bash
# 1. Clone repository
git clone https://github.com/organization/infra-monitoring-topology.git
cd infra-monitoring-topology

# 2. Copy environment file
cp .env.example .env

# 3. Start local development stack
docker compose up -d --build
```

### 2.2 Production-like Deployment
```bash
# 1. Configure production environment file
cp .env.example .env.production
# Secure SECRET_KEY, POSTGRES_PASSWORD, and ENVIRONMENT=production

# 2. Deploy stack with resource limits
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 3. Provisioning Confidential Secrets & TLS

### 3.1 Environment Variable Vault Provisioning
Dalam lingkungan produksi, variabel sensitif disuntikkan secara aman via Secret Manager / Environment Vault:
- `SECRET_KEY`: String acak 64-karakter (misal `openssl rand -hex 32`).
- `POSTGRES_PASSWORD`: Password PostgreSQL produksi.
- `CREDENTIAL_ENCRYPTION_KEY`: Kunci AES-256 untuk enkripsi kredensial target.

### 3.2 TLS HTTPS Configuration pada Nginx Reverse Proxy
Letakkan sertifikat SSL/TLS di `deploy/nginx/certs/` dan perbarui `deploy/nginx/default.conf`:
```nginx
server {
    listen 443 ssl http2;
    server_name monitoring.infra.company.com;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    ...
}
```

---

## 4. Target Collector Onboarding Guide

### 4.1 Onboarding Linux Host (SSH Target)
1. **Buat Dedicated Service Account**:
   ```bash
   sudo useradd -m -s /bin/bash infra_collector
   ```
2. **Konfigurasi Public Key Authentication**:
   ```bash
   sudo mkdir -p /home/infra_collector/.ssh
   echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI..." | sudo tee /home/infra_collector/.ssh/authorized_keys
   ```
3. **Registrasi Target di Web Administration**:
   - Target Type: `SSH`
   - Endpoint: `192.168.10.50` (Port `22`)
   - Credential Vault Reference: `secret:ssh-prod-key-01`

### 4.2 Onboarding Windows / Hyper-V Host (WinRM Target)
1. **Aktifkan WinRM HTTPS Listener**:
   ```powershell
   Enable-PSRemoting -Force
   New-Item -Path WSMan:\Localhost\Plugin\SendShellCommand -Value $true -Force
   ```
2. **Registrasi Target di Web Administration**:
   - Target Type: `Hyper-V / WinRM`
   - Endpoint: `https://hyperv-host.domain.local:5986/wsman`
   - Credential Vault Reference: `secret:winrm-admin-pass`

### 4.3 Onboarding Docker Host (Docker TLS Target)
1. **Konfigurasi Docker Engine TCP TLS Socket**:
   Edit `/etc/docker/daemon.json`:
   ```json
   {
     "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2376"],
     "tlsverify": true,
     "tlscacert": "/etc/docker/ca.pem",
     "tlscert": "/etc/docker/server-cert.pem",
     "tlskey": "/etc/docker/server-key.pem"
   }
   ```
2. **Registrasi Target di Web Administration**:
   - Target Type: `Docker Engine API`
   - Endpoint: `tcp://10.0.0.10:2376`
   - Credential Vault Reference: `secret:docker-tls-cert`

---

## 5. Port Requirements & Firewall Rules

| Service | Port Internal | Port Public | Protocol | Access Scope |
| :--- | :--- | :--- | :--- | :--- |
| Nginx Reverse Proxy | 80 / 443 | 80 / 443 | TCP / HTTP(S) | Public / Corporate LAN |
| Backend API | 8000 | Restricted | TCP | Internal Bridge Network |
| Collector Exporter | 8001 | Restricted | TCP | Internal Bridge Network |
| Frontend Nginx | 8080 | Restricted | TCP | Internal Bridge Network |
| PostgreSQL DB | 5432 | Restricted | TCP | Internal Bridge Network |
| Prometheus TSDB | 9090 | Restricted | TCP | Internal Bridge Network |

> [!WARNING]
> Jangan mempublikasikan port `5432` (PostgreSQL) atau `9090` (Prometheus) ke publik. Seluruh akses eksternal harus melalui Nginx Reverse Proxy (Port 80/443).

---

## 6. Database Migration, Admin Bootstrap, & Demo Seed Mode

### 6.1 Database Migrations (Alembic)
```bash
docker exec -it infra_backend alembic upgrade head
```

### 6.2 Admin User Bootstrap
Pengguna admin pertama dibootstrap secara otomatis pada startup pertama atau dijalankan via CLI:
```bash
docker exec -it infra_backend python -c "import asyncio, core.database, services.auth_service; asyncio.run(services.auth_service.bootstrap_admin_user(core.database.AsyncSessionLocal()))"
```

### 6.3 Demo Data Seed Mode (Optional)
Untuk mengisi infrastruktur data peragaan:
```bash
docker exec -it infra_backend python -m seed_demo
```

---

## 7. Disaster Recovery, Backup, & Restore

### 7.1 Automated Daily PostgreSQL Backup
```bash
python3 deploy/scripts/backup_db.py --db-url "$DATABASE_URL" --output-dir /var/backups/infra
```

### 7.2 Restoration to Disposable Target
```bash
python3 deploy/scripts/restore_db.py --backup-file /var/backups/infra/infra_backup_20260731.sql --target-db-url "$DISPOSABLE_DB_URL"
```

---

## 8. Troubleshooting & Known Limitations

### 8.1 Troubleshooting Checklist
- **WebSocket Disconnect**: Periksa log Nginx Proxy (`docker logs infra_reverse_proxy`). Pastikan header `Upgrade` dan `Connection: "Upgrade"` diteruskan secara benar.
- **Node Status Stale**: Periksa log worker (`docker logs infra_collector_worker`). Verifikasi kredensial target dan keterjangkauan IP host.

### 8.2 Known Limitations & Product Roadmap
1. **Single-Instance Prometheus**: Prometheus MVP menggunakan single instance dengan retensi 90 hari. Downsampling 1 tahun dan HA clustering dikesampingkan ke Roadmap v2.
2. **Complex Traffic Animations**: Visualisasi traffic animasi real-time pada Canvas Topology dikesampingkan ke Roadmap v2 untuk menjaga FPS canvas pada 250+ node.
