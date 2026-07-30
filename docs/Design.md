# Design.md — Infrastructure Monitoring & Auto-Topology Application

## 1. Data Model (Skema Database Inti)

### Tabel: `nodes` (representasi semua entitas: physical server, hyper-v host, VM, docker host, container)
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| name | varchar | Nama server/VM/container |
| type | enum | `physical_server`, `hypervisor_host`, `vm`, `docker_host`, `container` |
| parent_id | UUID (nullable, FK → nodes.id) | Relasi hierarki (mis. container → docker_host, VM → hypervisor_host) |
| os | varchar | OS yang terdeteksi |
| cpu_cores | int | Jumlah core CPU |
| ram_mb | int | Total RAM (MB) |
| disk_gb | int | Total disk (GB) |
| ip_address | varchar | IP utama |
| status | enum | `up`, `down`, `warning`, `unknown` |
| last_seen | timestamp | Terakhir kali berhasil di-poll |
| metadata | jsonb | Data tambahan fleksibel (image docker, port, dsb) |
| created_at / updated_at | timestamp | Audit |

### Tabel: `node_connections` (edges untuk topology graph)
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| source_node_id | UUID (FK) | Node asal |
| target_node_id | UUID (FK) | Node tujuan |
| connection_type | enum | `network`, `hosts`, `depends_on` |
| metadata | jsonb | mis. port, protocol |

### Tabel: `metrics` (time-series — jika tidak pakai Prometheus terpisah)
| Kolom | Tipe |
|---|---|
| node_id | UUID (FK) |
| metric_name | varchar (`cpu_usage`, `ram_usage`, `disk_usage`, `network_in`, `network_out`) |
| value | float |
| timestamp | timestamp |

### Tabel: `alerts`
| Kolom | Tipe |
|---|---|
| id | UUID |
| node_id | UUID (FK) |
| rule | varchar (mis. `cpu_usage > 90%`) |
| severity | enum (`info`, `warning`, `critical`) |
| status | enum (`active`, `resolved`) |
| triggered_at / resolved_at | timestamp |

### Tabel: `users` & `roles`
Standar RBAC: `admin`, `operator` (bisa lihat + acknowledge alert), `viewer` (read-only, untuk management).

## 2. API Design (Ringkas — REST)

```
GET    /api/nodes                    → daftar semua node (filter by type, status)
GET    /api/nodes/:id                → detail satu node + histori metrik
GET    /api/nodes/:id/children       → child nodes (mis. VM di dalam host)
GET    /api/topology                 → seluruh graph (nodes + edges) siap divisualisasikan
GET    /api/topology/:scope          → subset topology (mis. per data center/per host)
GET    /api/metrics?node_id=&range=  → data time-series untuk chart
GET    /api/alerts?status=active     → daftar alert aktif
POST   /api/alerts/:id/acknowledge   → acknowledge alert
GET    /api/reports/weekly           → generate laporan periodik
WS     /ws/status                    → live push status update (untuk animasi real-time)
```

## 3. Topology Auto-Generation — Logika

1. **Collection**: tiap collector (Hyper-V, Docker, Host) mengirim data mentah ke backend secara periodik → disimpan/update di tabel `nodes`.
2. **Relationship Inference**: backend menyusun `parent_id` otomatis berdasarkan sumber data:
   - Docker container → parent = docker host tempat ia berjalan (dari hasil `docker inspect` di host tsb).
   - VM → parent = Hyper-V host (dari `Get-VM -ComputerName <host>`).
   - Physical server yang menjalankan Hyper-V/Docker → root node.
3. **Graph Build**: endpoint `/api/topology` menyusun query rekursif (`WITH RECURSIVE` di PostgreSQL) dari root node ke seluruh descendant, hasilnya di-serialize jadi format nodes+edges (kompatibel dengan React Flow / D3).
4. **Rendering**: frontend menerima JSON graph → render otomatis dengan layout algorithm (mis. dagre.js untuk hierarchical layout) — **tidak perlu digambar manual**, posisi node dihitung otomatis berdasarkan struktur data.
5. **Live Update**: WebSocket mengirim delta perubahan status (`node_id`, `status_baru`) → frontend update warna node tanpa reload/refetch seluruh graph → inilah yang memberi efek "animasi live".

## 4. UI/UX — Struktur Halaman

### 4.1 Dashboard Utama
- Ringkasan kartu: Total Server, Total Container, Alert Aktif, Uptime rata-rata.
- Mini-topology overview (seluruh data center, zoomable).

### 4.2 Topology View (fitur inti)
- Canvas interaktif (pan/zoom) menampilkan hierarki: Data Center → Physical Server → Hypervisor/Docker Host → VM/Container.
- Warna node: hijau (sehat), kuning (warning/resource tinggi), merah (down), abu-abu (unknown).
- Klik node → panel detail muncul di samping (metrics, aplikasi berjalan, histori status).
- Toggle "Network View" vs "Hierarchy View".
- Tombol Export (PNG/SVG/PDF).

### 4.3 Metrics & History
- Grafik time-series per node (line chart CPU/RAM/Disk, range selector: 1h/24h/7d/30d).

### 4.4 Alerts
- Tabel alert aktif & histori, filter by severity/node.
- Konfigurasi threshold per node/grup.

### 4.5 Reports
- Generate & download laporan periodik (PDF/Excel) — ringkasan kondisi infra untuk dilaporkan ke management.

## 5. Animasi — Detail Implementasi
- **Status pulse**: node dengan status baru berubah akan "berdenyut" (CSS animation/keyframe) selama beberapa detik agar mudah terlihat perubahan.
- **Traffic flow (opsional, iterasi lanjut)**: garis edge antar-node menampilkan partikel bergerak sepanjang garis untuk merepresentasikan adanya traffic/koneksi aktif — bisa pakai library seperti `react-flow` dengan custom edge animation, atau Canvas/SVG animation manual.
- Semua animasi harus punya **opsi disable** (untuk device low-spec / preferensi user, dan agar tidak mengganggu saat screenshot untuk dokumentasi).

## 6. Wireframe Tekstual (ASCII)

```
┌────────────────────────────────────────────────────────┐
│ [Logo]   Dashboard | Topology | Metrics | Alerts | ...  │
├────────────────────────────────────────────────────────┤
│  [Total Server: 24] [Container: 187] [Alert: 3] [Up:99%]│
├────────────────────────────────────────────────────────┤
│                                                          │
│     ┌───────────┐        ┌───────────┐                  │
│     │ HV-HOST-01│        │ HV-HOST-02│                  │
│     └─────┬─────┘        └─────┬─────┘                  │
│      ┌────┼────┐            ┌──┼───┐                    │
│    [VM1] [VM2] [VM3]      [VM4]  [VM5]                  │
│                                                          │
│     ┌───────────┐                                       │
│     │DOCKER-HOST │                                       │
│     └─────┬─────┘                                       │
│    ┌───────┼────────┬─────────┐                          │
│  [app1] [app2-db] [app3-api] [app4-web]                 │
│                                                          │
└────────────────────────────────────────────────────────┘
```
