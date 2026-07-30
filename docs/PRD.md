# PRD — Infrastructure Monitoring & Auto-Topology Application

## 1. Latar Belakang & Masalah
Saat ini, tidak ada sistem terpusat untuk mengetahui:
- Server apa saja yang ada di data center (fisik & virtual/Hyper-V).
- Aplikasi/container apa yang berjalan di masing-masing server (terutama Docker, dengan banyak aplikasi di dalamnya).
- Bagaimana topologi jaringan dan hubungan antar-server saat ini.

Akibatnya, proses inventarisasi masih manual, rawan human error, cepat basi (data langsung outdated begitu ada perubahan), dan menyulitkan perencanaan untuk migrasi, integrasi Cloudflare, maupun implementasi High Availability.

## 2. Tujuan (Goals)
1. Menyediakan **inventaris real-time** seluruh server (fisik, Hyper-V host+VM, Docker host+container) beserta spesifikasi (OS, CPU, RAM, Disk).
2. Menyediakan **status kesehatan** (up/down, resource usage) tiap server & aplikasi secara berkala.
3. **Otomatis menghasilkan diagram topologi** infrastruktur berdasarkan data yang terkumpul, tanpa perlu digambar manual di draw.io/Visio.
4. Menyediakan **visualisasi animasi** yang menunjukkan status live (mis. traffic, alur koneksi, indikator warna sehat/bermasalah).
5. Menjadi **single source of truth** yang menggantikan spreadsheet manual.

## 3. Non-Goals (Di luar Scope Awal)
- Bukan APM (Application Performance Monitoring) mendalam seperti New Relic/Datadog (fokus di infra & container level, bukan trace-level kode aplikasi).
- Bukan tools remediasi otomatis (auto-healing) di versi awal — hanya observasi & alerting.
- Tidak menggantikan backup/DR tools yang sudah ada.

## 4. Target Pengguna (Persona)
| Persona | Kebutuhan |
|---|---|
| IT Operation & Infrastruktur (Anda) | Melihat kondisi seluruh infra dalam satu dashboard, dapat alert jika ada anomali, punya diagram topologi selalu up-to-date untuk dokumentasi & perencanaan |
| Manajemen/Atasan (opsional, read-only) | Laporan ringkas kondisi infrastruktur, tanpa perlu detail teknis |

## 5. Functional Requirements

### 5.1 Discovery & Inventory
- FR-1: Sistem dapat mendeteksi seluruh Hyper-V host dan VM di dalamnya (nama, status, resource allocation).
- FR-2: Sistem dapat mendeteksi seluruh Docker host dan container yang berjalan di dalamnya (image, port, status, resource usage).
- FR-3: Sistem mencatat OS, CPU, RAM, dan disk space tiap server/VM secara otomatis (bukan input manual).
- FR-4: Sistem mendukung penambahan server baru secara semi-otomatis (agent install / registrasi credential untuk agentless).

### 5.2 Monitoring
- FR-5: Sistem menampilkan status up/down tiap server dan container secara real-time (interval polling dikonfigurasi, mis. 30–60 detik).
- FR-6: Sistem menampilkan metrik dasar: CPU usage %, RAM usage %, Disk usage %, network I/O.
- FR-7: Sistem dapat mengirim alert (email/Telegram/WhatsApp/Slack) jika threshold terlampaui atau server down.

### 5.3 Topology & Visualisasi
- FR-8: Sistem otomatis menghasilkan diagram topologi berjenjang: **Data Center → Physical Server → Hyper-V Host → VM** dan **Docker Host → Container → Aplikasi di dalamnya**.
- FR-9: Sistem otomatis menghasilkan diagram topologi jaringan (koneksi antar-server, VLAN/subnet jika terdeteksi).
- FR-10: Diagram diperbarui otomatis ketika ada perubahan topologi (server baru, container baru/mati).
- FR-11: Sistem menyediakan mode "animasi" — indikator visual bergerak/berubah warna untuk merepresentasikan status live (hijau=sehat, kuning=warning, merah=down).
- FR-12: User dapat export diagram (PNG/SVG/PDF) untuk keperluan dokumentasi/presentasi ke management.

### 5.4 Dashboard & Reporting
- FR-13: Dashboard ringkasan: total server, total container, jumlah yang bermasalah, uptime rata-rata.
- FR-14: Halaman detail per-server: histori resource usage (grafik time-series).
- FR-15: Laporan periodik (mingguan/bulanan) yang bisa di-generate/download.

## 6. Non-Functional Requirements
- NFR-1: **Ringan** — agent/collector tidak boleh membebani resource server yang dipantau (target overhead < 2% CPU).
- NFR-2: **Aman** — kredensial akses (WinRM, SSH, Docker API) disimpan terenkripsi, akses berbasis role (RBAC).
- NFR-3: **Skalabel** — mampu memantau minimal 50 server/VM dan 200+ container tanpa degradasi performa signifikan.
- NFR-4: **Availability** — dashboard tetap dapat diakses meski satu collector/agent down (tidak single point of failure untuk sistem monitoring itu sendiri).
- NFR-5: Data historis disimpan minimal 90 hari untuk kebutuhan analisis trend.

## 7. Success Metrics
- 100% server & container di data center ter-mapping otomatis dalam sistem (dibanding sebelumnya 0%/manual).
- Waktu untuk menghasilkan diagram topologi terbaru: dari berjam-jam manual → < 1 menit otomatis.
- Mean Time to Detect (MTTD) insiden server down: turun signifikan berkat alerting real-time.

## 8. Assumptions & Constraints
- Server-server yang ada dapat diakses via WinRM (Windows) atau SSH (Linux) dari server monitoring — tidak semua environment mengizinkan ini, perlu koordinasi network/firewall.
- Docker API/socket dapat diakses dari collector (baik lokal maupun remote via TCP dengan TLS).
- Fase awal (MVP) fokus ke observability, fitur animasi kompleks bisa menyusul di iterasi berikutnya.

## 9. Roadmap Fitur (High Level)
| Fase | Fitur |
|---|---|
| MVP | Discovery server/VM/container, dashboard status dasar, diagram topologi statis (auto-generate, belum animasi) |
| V1.1 | Alerting, historical metrics, export diagram |
| V1.2 | Animasi status live, network topology diagram |
| V2 | Role-based access, laporan otomatis, integrasi dengan sistem lain (mis. Cloudflare API status, ticketing) |
