# Architecture.md — Infrastructure Monitoring & Auto-Topology Application

## 1. Gambaran Umum Arsitektur

Sistem terdiri dari 4 lapisan utama:

```
┌──────────────────────────────────────────────────────────┐
│                     LAYER 4: PRESENTATION                 │
│   Web Dashboard (React/Vue) — Topology View, Metrics,     │
│   Alerts, Reports                                          │
└──────────────────────────────────────────────────────────┘
                         │ REST/WebSocket API
┌──────────────────────────────────────────────────────────┐
│                     LAYER 3: API & PROCESSING              │
│   Backend API Service — Auth, Data Aggregation,             │
│   Topology Builder Engine, Alert Engine                    │
└──────────────────────────────────────────────────────────┘
                         │
┌──────────────────────────────────────────────────────────┐
│                     LAYER 2: DATA STORE                    │
│   Time-series DB (metrics) + Relational/Document DB        │
│   (inventory & topology state)                             │
└──────────────────────────────────────────────────────────┘
                         │
┌──────────────────────────────────────────────────────────┐
│                LAYER 1: COLLECTION / DISCOVERY              │
│   - Hyper-V Collector (PowerShell Remoting/WMI)            │
│   - Docker Collector (Docker API per host)                 │
│   - Host Collector (SSH/WinRM — CPU/RAM/Disk)               │
└──────────────────────────────────────────────────────────┘
                         │
      ┌──────────────┬──────────────┬───────────────┐
      │ Hyper-V Host  │ Docker Host  │ Physical/VM    │
      │ (VM1, VM2..)  │ (Container..)│ Servers        │
      └──────────────┴──────────────┴───────────────┘
```

## 2. Komponen Utama

### 2.1 Collection Layer (Data Gathering)
Pendekatan: **hybrid — agentless untuk kesederhanaan awal, opsi agent untuk data lebih granular di iterasi lanjut.**

| Sumber Data | Metode | Tools/API |
|---|---|---|
| Hyper-V Host & VM | Agentless — PowerShell Remoting (WinRM) | `Get-VM`, `Get-VMHost`, `Get-VMNetworkAdapter` |
| Docker Host & Container | Agentless — Docker Remote API (TCP+TLS) atau socket lokal | Docker Engine API `/containers/json`, `/info` |
| Physical/VM OS metrics (CPU/RAM/Disk) | Agentless (SSH untuk Linux, WinRM untuk Windows) atau lightweight agent | `node_exporter` (opsional, jika mau prometheus-native) |
| Network topology | Kombinasi: ARP table, traceroute antar-subnet, atau input manual untuk switch/router (karena SNMP ke perangkat network butuh akses khusus) | SNMP (jika perangkat mendukung), fallback manual mapping |

Collector berjalan sebagai **scheduled job/service** (interval default 60 detik untuk status, 5 menit untuk full inventory scan) supaya tidak membebani resource.

### 2.2 Data Store
Disarankan 2 jenis penyimpanan (bisa 1 mesin di awal, dipisah saat skala membesar):

1. **Time-series database** — untuk metrik CPU/RAM/Disk/network historis.
   - Rekomendasi: **Prometheus** (open-source, ringan, ekosistem besar) atau **InfluxDB**.
2. **Relational/Document database** — untuk data inventory, relasi topologi (host → VM → container), user, alert rules.
   - Rekomendasi: **PostgreSQL** (relational, mendukung JSON field untuk fleksibilitas topologi).

### 2.3 API & Processing Layer
- Backend service (mis. **Node.js/NestJS** atau **Python/FastAPI**) yang:
  - Menerima data dari collector (push) atau menarik data collector (pull) sesuai desain.
  - Menjalankan **Topology Builder Engine**: mengolah data mentah (host, VM, container, network) menjadi struktur graph (nodes & edges) yang siap divisualisasikan.
  - Menjalankan **Alert Engine**: evaluasi threshold, kirim notifikasi.
  - Menyediakan REST API untuk dashboard, dan **WebSocket** untuk update status real-time (agar "animasi" di frontend bisa live tanpa polling terus-menerus).

### 2.4 Presentation Layer
- Web dashboard (**React** direkomendasikan, sesuai ekosistem visualisasi graph yang matang).
- Library visualisasi graph/topologi:
  - **React Flow** atau **D3.js** — untuk render diagram topologi interaktif, mendukung animasi status (perubahan warna node, garis koneksi berdenyut untuk menunjukkan traffic).
  - **Mermaid.js** — opsional, cocok untuk generate diagram statis/export cepat (mis. dokumentasi otomatis dalam format markdown+diagram).
- Charting untuk metrik historis: **Recharts** atau **Grafana** (jika ingin embed Grafana panel langsung, mempercepat development karena tidak perlu bangun chart engine sendiri).

## 3. Alternatif Arsitektur: Build vs Leverage Existing Tools

Karena kebutuhan mencakup monitoring + auto-topology, ada 2 opsi strategi:

**Opsi A — Build custom (sesuai PRD di atas)**
- Kelebihan: sepenuhnya sesuai kebutuhan spesifik (Hyper-V + Docker + auto-diagram + animasi custom).
- Kekurangan: effort development lebih besar, perlu maintenance jangka panjang.

**Opsi B — Kombinasi tools existing + custom topology layer**
- Gunakan **Prometheus + Grafana** untuk metrics & alerting (sudah matang, banyak exporter siap pakai untuk Docker & Windows/Hyper-V).
- Bangun **custom topology/diagram engine** di atasnya (karena Grafana tidak punya fitur auto-topology diagram bawaan yang kuat) — mengambil data dari Prometheus API lalu render graph.
- Kelebihan: development jauh lebih cepat (metrics & alerting "gratis" dari tools existing), fokus effort hanya di bagian yang benar-benar custom (topology visualization).
- **Rekomendasi:** mulai dari Opsi B untuk MVP, migrasi ke custom penuh jika kebutuhan berkembang.

## 4. Deployment Architecture
- Aplikasi monitoring sebaiknya **tidak** dijalankan di server yang sama dengan yang dipantau (untuk menghindari single point of failure & bias resource).
- Deploy sebagai container terpisah (Docker Compose untuk awal, bisa naik ke k8s/Swarm jika skala membesar):
  - `monitoring-backend`
  - `monitoring-frontend`
  - `postgres`
  - `prometheus` (jika Opsi B)
  - `grafana` (opsional, jika Opsi B)
- Pertimbangkan menempatkan di server terpisah dengan akses network ke seluruh data center (butuh firewall rule khusus untuk WinRM/SSH/Docker API ke semua host target).

## 5. Keamanan
- Kredensial akses ke tiap host (WinRM/SSH/Docker API) disimpan di **secrets vault** (mis. HashiCorp Vault, atau minimal encrypted config seperti Ansible Vault) — jangan plaintext di database/config file.
- Komunikasi collector ↔ backend menggunakan TLS.
- Docker Remote API **wajib** diamankan dengan TLS mutual auth (jangan expose port 2375 tanpa TLS ke network).
- Akses dashboard menggunakan autentikasi (SSO/LDAP jika tersedia, atau minimal username/password + RBAC).

## 6. Skalabilitas & Reliability
- Prometheus/time-series DB dapat di-scale dengan retention policy & downsampling untuk data lama.
- Backend API stateless → mudah di-scale horizontal jika perlu.
- Untuk mencegah monitoring system sendiri jadi single point of failure, pertimbangkan **health-check eksternal sederhana** (mis. uptime checker pihak ketiga) sebagai lapisan kedua khusus untuk memantau sistem monitoring itu sendiri.
