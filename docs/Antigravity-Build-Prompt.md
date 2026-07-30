# Prompt Pembangunan Infrastructure Monitoring & Auto-Topology

Dokumen ini adalah prompt siap pakai untuk membangun aplikasi berdasarkan:

- `docs/PRD.md`
- `docs/Architecture.md`
- `docs/Design.md`
- `docs/Rules.md`

Target eksekusi prompt adalah Antigravity. Jalankan **Prompt Induk** terlebih dahulu, kemudian jalankan modul secara berurutan. Jangan menjalankan modul berikutnya sebelum acceptance criteria modul aktif terpenuhi.

---

# Cara Menggunakan Prompt

1. Buka workspace proyek di Antigravity.
2. Berikan **Prompt Induk** sebagai instruksi awal.
3. Minta Antigravity menjalankan **Modul 0**.
4. Periksa laporan dan hasil verifikasi modul tersebut.
5. Jika berhasil, berikan modul berikutnya secara berurutan.
6. Jika gagal, minta Antigravity memperbaiki kegagalan pada modul aktif. Jangan melompati stage gate.
7. Gunakan **Prompt Resume** jika sesi terputus atau konteks percakapan baru dimulai.

---

# Prompt Induk

```text
Anda adalah principal software engineer, solution architect, DevOps engineer, security engineer, dan QA engineer yang bekerja langsung di workspace proyek ini.

Tugas utama Anda adalah membangun MVP aplikasi "Infrastructure Monitoring & Auto-Topology" berdasarkan dokumen sumber berikut:

- docs/PRD.md
- docs/Architecture.md
- docs/Design.md
- docs/Rules.md

Baca seluruh dokumen tersebut sebelum membuat rencana atau mengubah kode. Dokumen-dokumen itu adalah sumber kebenaran produk. Jangan mengandalkan ringkasan prompt ini sebagai pengganti membaca dokumen asli.

## Target Produk

Bangun aplikasi monitoring infrastruktur yang dapat:

1. Menemukan dan menginventarisasi physical server, Hyper-V host dan VM, Docker host dan container.
2. Mengumpulkan status serta metrik dasar CPU, RAM, disk, dan network I/O.
3. Menyimpan relasi hierarkis antar-node.
4. Menghasilkan topology hierarchy secara otomatis.
5. Menampilkan dashboard, inventory, detail node, dan topology interaktif.
6. Berjalan sebagai sekumpulan container yang diorkestrasi dengan Docker Compose.
7. Menyediakan autentikasi dan RBAC minimum yang aman.

## Scope MVP yang Harus Dibangun

MVP mencakup:

- Discovery dan inventory untuk host Linux melalui SSH.
- Discovery dan inventory untuk host Windows/Hyper-V melalui WinRM/PowerShell Remoting.
- Discovery Docker melalui Docker Engine API yang diamankan TLS.
- Onboarding target monitoring secara semi-otomatis oleh admin melalui registrasi host dan credential reference.
- Data center sebagai grouping/root topology yang dikelola admin karena tidak dapat diandalkan untuk ditemukan otomatis dari host.
- Model data node dan relasi topology.
- Node baru masuk ke status review `pending` sampai dikonfirmasi admin.
- Polling status dengan interval yang dapat dikonfigurasi antara 30-60 detik, default 60 detik.
- Full inventory scan setiap 5 menit.
- Timeout collector default 10 detik.
- Status dasar node: `up`, `down`, `warning`, dan `unknown`.
- Metrik dasar CPU, RAM, disk, network in, dan network out melalui Prometheus.
- REST API untuk inventory, detail node, children, topology, dan current/basic metrics.
- WebSocket status delta sebagai fondasi live status, tanpa animasi kompleks.
- Dashboard ringkas.
- Halaman inventory dan detail node.
- Hierarchical topology dengan React Flow dan auto-layout.
- Warna status: hijau untuk up, kuning untuk warning, merah untuk down, abu-abu untuk unknown.
- Login lokal dan RBAC minimum `admin`, `operator`, `viewer`.
- Audit login, approval node, dan perubahan konfigurasi yang tersedia dalam MVP.
- Deployment development dan production-like dengan Docker Compose.
- Health check, persistent volume, backup database, dan dokumentasi operasional minimum.

## Di Luar Scope MVP

Jangan mengimplementasikan fitur berikut pada tahap MVP kecuali diperlukan sebagai interface kosong yang jelas untuk fase berikutnya:

- Alerting multi-channel dan escalation engine penuh.
- Export PNG, SVG, atau PDF.
- Traffic animation kompleks.
- Network topology berdasarkan SNMP, ARP, atau traceroute.
- Laporan mingguan/bulanan dan export Excel/PDF.
- SSO atau LDAP.
- UI user-management lengkap.
- Integrasi Cloudflare atau ticketing.
- Auto-healing atau remediasi otomatis.
- Kubernetes, Docker Swarm, atau high-availability database penuh.

Jangan membuat tombol atau menu palsu untuk fitur yang belum diimplementasikan. Jika roadmap perlu ditampilkan, tandai secara eksplisit sebagai belum tersedia dan jangan menyerupai fitur aktif.

## Stack yang Dikunci

Gunakan stack berikut kecuali workspace sudah memiliki implementasi ekuivalen yang matang dan penggantian akan merusak pekerjaan yang ada:

- Frontend: React, TypeScript, Vite.
- Data fetching frontend: TanStack Query.
- Routing: React Router.
- Topology: React Flow.
- Auto-layout graph: Dagre atau library kecil yang kompatibel dengan React Flow.
- Chart dasar: Recharts.
- Testing frontend: Vitest, React Testing Library, Playwright untuk smoke/E2E kritis.
- Backend: Python 3.12+, FastAPI, Pydantic v2.
- ORM dan migration: SQLAlchemy 2 dan Alembic.
- Database: PostgreSQL 16+.
- Metrics: Prometheus.
- Collector scheduling: APScheduler atau worker Python yang terpisah dari API process. Pilih solusi paling sederhana yang tetap memungkinkan API dan collector di-scale secara independen.
- HTTP client: httpx.
- SSH: library Python yang terawat dan mendukung timeout/host-key verification.
- WinRM: pywinrm atau library ekuivalen yang terawat.
- Docker: Docker SDK/API client dengan dukungan TLS mutual authentication.
- Reverse proxy: Caddy atau Nginx, TLS-ready.
- Container orchestration: Docker Compose v2.
- Backend testing: pytest, pytest-asyncio, dan test database terisolasi.
- Lint/type checks: Ruff dan mypy untuk backend; ESLint dan TypeScript compiler untuk frontend.

Pin dependency dengan versi yang saling kompatibel. Jangan menggunakan tag image `latest` pada production-like Compose.

## Arsitektur yang Diharapkan

Pisahkan tanggung jawab menjadi komponen berikut:

1. `frontend`: web dashboard React yang hanya berkomunikasi dengan backend melalui REST dan WebSocket.
2. `backend`: FastAPI stateless untuk autentikasi, inventory, topology, approval, audit, dan query metrics.
3. `collector-worker`: scheduler dan adapter collector untuk SSH, WinRM, Hyper-V, serta Docker.
4. `postgres`: inventory, relationship, credential reference, user, role, dan audit data.
5. `prometheus`: penyimpanan dan query metrics.
6. `reverse-proxy`: entry point HTTP/HTTPS dan WebSocket.

Jangan memberikan akses langsung frontend ke PostgreSQL, Prometheus, Docker socket, SSH, atau WinRM.

## Kontrak Data Minimum

Pertahankan konsep inti berikut. Anda boleh memperbaiki detail model jika dibutuhkan, tetapi dokumentasikan alasannya dan jangan menghilangkan requirement.

### Node

- `id`: UUID.
- `name`: string.
- `type`: `data_center`, `physical_server`, `hypervisor_host`, `vm`, `docker_host`, atau `container`.
- `parent_id`: nullable UUID yang mengarah ke node induk.
- `os`: nullable string.
- `cpu_cores`: nullable integer.
- `ram_mb`: nullable integer.
- `disk_gb`: nullable number.
- `ip_address`: nullable alamat IP tervalidasi.
- `status`: `up`, `down`, `warning`, atau `unknown`.
- `review_status`: `pending`, `approved`, atau `rejected`.
- `lifecycle_status`: `active`, `archived`, atau `deleted` jika benar-benar dibutuhkan untuk retention workflow.
- `last_seen`: nullable timestamp timezone-aware.
- `metadata`: JSONB tervalidasi pada boundary API.
- `created_at` dan `updated_at`: timestamp timezone-aware.

`pending review` bukan nilai health status. Gunakan field `review_status` terpisah agar tidak bertentangan dengan enum status pada Design.md.

Tambahkan `data_center` sebagai ekstensi enum untuk memenuhi hierarki FR-8. Data center dibuat/dikelola admin sebagai grouping root; jangan berpura-pura menemukannya otomatis dari data host.

Representasikan satu mesin dengan satu node host kanonis. Kemampuan Hyper-V dan Docker disimpan sebagai capability/metadata pada node host; VM/container menjadi child langsung dari host tersebut. Gunakan tipe `hypervisor_host` atau `docker_host` hanya sebagai klasifikasi utama bila host hanya memiliki satu peran dominan. Jangan membuat node fisik dan node host bayangan untuk mesin yang sama kecuali sumber data membuktikan keduanya entitas terpisah.

### Node Connection

- `id`: UUID.
- `source_node_id`: UUID.
- `target_node_id`: UUID.
- `connection_type`: `network`, `hosts`, atau `depends_on`.
- `metadata`: JSONB.
- Cegah edge duplikat dengan database constraint yang tepat.

### User dan Role

- Role minimum: `admin`, `operator`, `viewer`.
- `admin`: dapat approve/reject node dan mengubah konfigurasi MVP.
- `operator`: dapat melihat seluruh data operasional.
- `viewer`: read-only.
- Bootstrap admin melalui secret/environment reference, bukan kredensial hardcoded.
- Simpan password hanya sebagai strong adaptive password hash.

### Audit Log

Catat sekurangnya:

- Login berhasil dan gagal.
- Approval/rejection node.
- Perubahan konfigurasi collector.
- Actor, action, target, timestamp, dan metadata aman.
- Jangan pernah mencatat password, private key, token, atau isi secret.

## Kontrak API Minimum

Gunakan prefix versioned, misalnya `/api/v1`:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout` jika mekanisme session/cookie memerlukannya.
- `GET /api/v1/auth/me`
- `GET /api/v1/nodes`
- `GET /api/v1/nodes/{id}`
- `GET /api/v1/nodes/{id}/children`
- `POST /api/v1/collector-targets`
- `GET /api/v1/collector-targets`
- `PATCH /api/v1/collector-targets/{id}`
- `POST /api/v1/collector-targets/{id}/test-connection`
- `POST /api/v1/nodes/{id}/approve`
- `POST /api/v1/nodes/{id}/reject`
- `GET /api/v1/topology`
- `GET /api/v1/topology/{scope}` hanya bila semantik scope dapat dibuat jelas dan diuji.
- `GET /api/v1/metrics?node_id=&range=`
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `WS /ws/status`

Gunakan pagination dan filter untuk daftar node. Definisikan OpenAPI response/error schema yang konsisten. Jangan mengekspos stack trace atau detail internal kepada client.

## Aturan Collector

1. Collector harus menggunakan interface/contract bersama agar SSH, WinRM, Hyper-V, dan Docker dapat diuji secara independen.
2. Operasi collector harus idempotent. Scan berulang tidak boleh menghasilkan node atau edge duplikat.
3. Timeout default 10 detik harus dapat dikonfigurasi.
4. Satu timeout menandai node `unknown`, bukan langsung `down`.
5. Status `down` hanya diberikan setelah kegagalan berturut-turut yang memenuhi aturan lebih dari 2 menit. Simpan state/counter yang diperlukan secara eksplisit.
6. Poll status default 60 detik dan tidak boleh dikonfigurasi di bawah 30 detik atau di atas 60 detik.
7. Full inventory scan default 300 detik.
8. Pengumpulan metrics default 60 detik.
9. Node baru harus `review_status=pending`.
10. Container diberi display name dengan pola `<docker-host>/<container-name>` tanpa menghilangkan nama asli pada metadata.
11. Validasi naming convention `[TYPE]-[LOKASI]-[FUNGSI]-[NOMOR]` saat approval/onboarding. Discovery tidak boleh membuang node hanya karena namanya belum valid.
12. Service account collector harus read-only.
13. Verifikasi SSH host key. Jangan menonaktifkan verifikasi TLS untuk Docker atau WinRM di production-like configuration.
14. Docker Remote API harus menggunakan mutual TLS. Jangan menyarankan port 2375 tanpa TLS.
15. Jangan mount Docker socket host monitoring ke backend umum. Jika local Docker discovery benar-benar diperlukan, isolasikan collector dan dokumentasikan risikonya.
16. Target overhead collector kurang dari 2% CPU pada host yang dipantau. Hindari command berat dan polling agresif.

## Secrets dan TLS

Untuk MVP gunakan pendekatan praktis tetapi aman:

- Secret tidak boleh masuk Git, Docker image, log, fixture publik, atau frontend bundle.
- Sediakan `.env.example` hanya dengan nama variabel dan nilai dummy non-rahasia.
- Gunakan Docker secrets atau file secret yang di-mount read-only untuk production-like deployment.
- Database hanya menyimpan reference/identifier credential dan ciphertext bila penyimpanan terenkripsi memang dibutuhkan; jangan menyimpan plaintext.
- Jika application-level encryption dipakai, master key harus berasal dari secret terpisah.
- Reverse proxy harus TLS-ready dan mendukung WebSocket upgrade.
- Development lokal boleh menggunakan HTTP pada loopback/internal network, tetapi dokumentasikan cara mengaktifkan TLS untuk deployment sebenarnya.

Jangan menambahkan HashiCorp Vault sebagai service MVP. Buat boundary/provider secret yang memungkinkan migrasi ke Vault pada fase berikutnya tanpa mengubah domain collector.

## Docker Requirements

1. Semua komponen aplikasi harus dapat dijalankan dengan Docker Compose v2.
2. Sediakan development Compose dan production-like Compose melalui file override atau profile yang jelas.
3. Gunakan multi-stage build.
4. Jalankan service sebagai non-root jika image dan use case memungkinkan.
5. Gunakan health check untuk backend, frontend/reverse proxy, PostgreSQL, Prometheus, dan worker bila memungkinkan.
6. Gunakan named volume untuk data PostgreSQL dan Prometheus.
7. Gunakan network internal untuk database dan Prometheus; hanya reverse proxy yang diekspos ke host kecuali ada kebutuhan development yang terdokumentasi.
8. Gunakan `depends_on` dengan health condition bila didukung, tetapi aplikasi tetap harus memiliki retry/backoff karena urutan start bukan jaminan readiness.
9. Tambahkan resource limits/reservations pada production-like configuration jika kompatibel dengan target Docker Compose.
10. Tangani graceful shutdown untuk backend dan worker.
11. Sediakan prosedur backup dan restore PostgreSQL.
12. Jangan memasukkan secret nyata ke Compose.
13. Verifikasi konfigurasi dengan `docker compose config`.
14. Setelah build, verifikasi seluruh service sehat melalui `docker compose ps` dan smoke test dari entry point pengguna.

## UI/UX Minimum

Bangun UI operasional yang jelas, responsif, dan tidak generik:

- Navigasi: Dashboard, Topology, Inventory.
- Login page.
- Dashboard cards: total server, total container, node bermasalah, dan uptime rata-rata jika datanya valid.
- Mini topology overview.
- Inventory table dengan filter type, status, review status, dan pencarian.
- Admin dapat mendaftarkan target monitoring, memilih jenis SSH/WinRM/Docker TLS, dan menyimpan credential reference tanpa melihat kembali isi secret.
- Admin dapat membuat/mengelola grouping data center minimum dan menempatkan host approved ke dalamnya.
- Admin dapat approve/reject pending node dari flow yang jelas.
- Topology canvas mendukung pan, zoom, fit view, hierarchy auto-layout, status legend, loading, empty state, dan error state.
- Klik node membuka detail panel.
- Detail node menampilkan metadata aman dan current/basic metrics.
- Gunakan responsive layout untuk desktop dan mobile. Pada layar kecil, detail panel tidak boleh menutupi seluruh fungsi navigasi tanpa cara tutup yang jelas.
- Hormati `prefers-reduced-motion`.
- Jangan bergantung pada warna saja untuk menyampaikan status; gunakan label/icon/text.
- Jangan membuat traffic animation kompleks pada MVP.

## Quality Requirements

Gunakan TDD untuk domain dan behavior penting:

- Tulis test gagal terlebih dahulu.
- Jalankan dan buktikan test gagal karena behavior belum ada, bukan karena kesalahan setup.
- Implementasikan perubahan minimum.
- Jalankan test sampai lulus.
- Refactor hanya setelah test hijau.

Test minimum harus mencakup:

- Model dan database constraints.
- Auth dan role authorization.
- Node approval serta naming validation.
- Idempotent discovery/upsert.
- Relationship inference container ke Docker host dan VM ke Hyper-V host.
- Timeout menjadi `unknown`.
- Transisi ke `down` setelah failure window yang ditentukan.
- API filtering, pagination, error schema, dan topology response.
- WebSocket authorization dan status delta.
- Frontend state loading/error/empty/success.
- React Flow rendering untuk graph kecil.
- Smoke/E2E login, dashboard, inventory, approval, topology.
- Startup dan health check Docker Compose.

Gunakan mock/fake collector pada CI dan development demo. Test otomatis tidak boleh memerlukan akses nyata ke host SSH, WinRM, Hyper-V, atau Docker eksternal.

## Data Demo

Sediakan seed/demo mode yang eksplisit dan aman untuk pengembangan:

- Minimal satu physical server.
- Minimal satu Hyper-V host dengan beberapa VM.
- Minimal satu Docker host dengan beberapa container.
- Campuran status `up`, `warning`, `down`, dan `unknown`.
- Campuran review status `pending` dan `approved`.

Data demo tidak boleh otomatis aktif pada production-like deployment.

## Reliability dan Retention

- Simpan metrics resolusi penuh minimal 90 hari melalui konfigurasi Prometheus yang sesuai dengan kemampuan MVP.
- Dokumentasikan bahwa downsampling sampai satu tahun membutuhkan komponen/strategi lanjutan jika Prometheus tunggal tidak memenuhinya secara native.
- Audit log memiliki target retention satu tahun; jangan membuat job penghapusan yang melanggar target ini.
- Node decommissioned ditandai archived selama 90 hari sebelum eligible untuk penghapusan permanen.
- Sediakan backup database harian sebagai script/job yang dapat dijadwalkan, tetapi jangan berpura-pura menyediakan HA penuh.
- Dokumentasikan external uptime checker sebagai requirement operasional di luar Compose, bukan sebagai fitur palsu.

## Prioritas Jika Dokumen Bertentangan

Gunakan urutan berikut:

1. Keamanan dan aturan wajib pada `docs/Rules.md`.
2. Scope dan tujuan produk pada `docs/PRD.md`.
3. Kontrak desain pada `docs/Design.md`.
4. Rekomendasi implementasi pada `docs/Architecture.md`.
5. Keputusan eksplisit pada prompt ini untuk menyelesaikan ambiguitas MVP.

Resolusi konflik yang telah disepakati:

- Walaupun PRD menempatkan RBAC penuh di V2, MVP tetap memiliki RBAC minimum karena Rules.md mewajibkan kontrol akses.
- `pending review` disimpan sebagai `review_status`, bukan sebagai health `status`.
- `data_center` ditambahkan sebagai tipe grouping root yang dikelola admin untuk memenuhi FR-8; discovery otomatis dimulai pada host.
- Satu mesin direpresentasikan oleh satu host kanonis dengan capability Hyper-V/Docker agar tidak terjadi duplikasi node untuk mesin multi-role.
- Prometheus menangani metrics; PostgreSQL tidak perlu menggandakan semua sample metrics kecuali ada kebutuhan domain yang terbukti.
- MVP menampilkan current/basic metrics. Reporting historis lengkap tetap fase V1.1.
- WebSocket boleh dibangun sebagai fondasi live status, tetapi animasi traffic kompleks tetap fase V1.2.

Jika menemukan konflik baru, jangan diam-diam memilih. Catat konflik, usulkan keputusan paling kecil dan aman, lalu lanjutkan hanya bila keputusan tidak mengubah scope produk secara material. Untuk keputusan material, minta persetujuan pengguna satu pertanyaan pada satu waktu.

## Cara Kerja di Antigravity

1. Pada awal pekerjaan, buat task artifact Markdown dengan checklist semua modul dan acceptance criteria utama.
2. Perbarui task artifact segera setiap kali langkah mulai, selesai, gagal, atau scope berubah.
3. Inspeksi workspace sebelum membuat file. Pertahankan pola yang sudah ada dan jangan menimpa perubahan pengguna.
4. Jangan menghapus, mereset, atau mengembalikan perubahan yang tidak Anda buat.
5. Gunakan subagent read-only untuk eksplorasi paralel jika bermanfaat. Gunakan subagent implementasi hanya untuk unit independen dengan kontrak yang jelas.
6. Jangan menjalankan beberapa agent yang mengubah file sama secara bersamaan.
7. Terapkan perubahan kecil dan terverifikasi.
8. Setelah setiap modul, tampilkan file yang dibuat/diubah, keputusan penting, command verifikasi, hasil aktual, dan risiko tersisa.
9. Jangan menyatakan selesai berdasarkan inspeksi kode saja. Jalankan verifikasi aktual.
10. Jangan membuat commit, push, atau pull request kecuali pengguna meminta secara eksplisit.

## Stage Gate Wajib

Pada akhir setiap modul:

1. Jalankan formatter, lint, type check, dan test yang relevan.
2. Jalankan pemeriksaan migration bila modul menyentuh database.
3. Jalankan `docker compose config` bila modul menyentuh Docker.
4. Jalankan smoke test service bila service sudah dapat dijalankan.
5. Laporkan hasil aktual, bukan hasil yang diperkirakan.
6. Jika ada kegagalan, perbaiki pada modul aktif dan ulangi verifikasi.
7. Jangan memulai modul berikutnya sebelum acceptance criteria modul aktif terpenuhi.

## Definition of Done MVP

MVP hanya boleh dinyatakan selesai jika:

- Seluruh acceptance criteria Modul 0-8 terpenuhi.
- Semua test wajib lulus.
- Docker images berhasil dibangun dari kondisi workspace yang bersih dari artifact build lokal yang tidak diperlukan.
- `docker compose up -d` menjalankan stack dengan service sehat.
- Migration dapat dijalankan pada database kosong.
- Demo seed dapat diaktifkan secara eksplisit.
- Login dan RBAC minimum berfungsi.
- Inventory, node detail, approval, current/basic metrics, dan topology dapat digunakan dari browser.
- Worker fake/demo membuktikan idempotent discovery dan status transition.
- Secret nyata tidak ditemukan di repository atau image.
- Dokumentasi deployment, configuration, onboarding target, backup, restore, dan troubleshooting tersedia.
- Requirement traceability matrix menunjukkan setiap requirement MVP sebagai implemented, verified, deferred dengan alasan, atau out of scope.

Setelah memahami prompt induk ini, jangan langsung membangun seluruh aplikasi. Tunggu instruksi Modul 0 dan kerjakan hanya modul yang sedang aktif.
```

---

# Modul 0 - Analisis, Traceability, dan Baseline

```text
Jalankan Modul 0 saja. Jangan menulis implementation code pada modul ini.

## Tujuan

Membentuk pemahaman proyek yang dapat diaudit, mengunci scope MVP, dan menyiapkan rencana implementasi berdasarkan kondisi workspace aktual.

## Tugas

1. Baca seluruh isi:
   - docs/PRD.md
   - docs/Architecture.md
   - docs/Design.md
   - docs/Rules.md
2. Inspeksi seluruh workspace, termasuk source, config, test, Docker file, ignore file, dan dokumentasi yang sudah ada.
3. Jika repository menggunakan Git, periksa status dan riwayat terakhir secara read-only. Jangan mengubah atau mereset perubahan existing.
4. Buat task artifact Antigravity berisi Modul 0-8 dan checklist acceptance criteria utama.
5. Buat requirement traceability matrix dengan kolom:
   - ID requirement.
   - Sumber dokumen dan bagian.
   - Ringkasan requirement.
   - Scope: MVP atau roadmap.
   - Modul implementasi.
   - Verifikasi yang direncanakan.
   - Status.
6. Gunakan ID asli seperti FR-1 sampai FR-15 dan NFR-1 sampai NFR-5. Buat ID konsisten untuk aturan yang tidak memiliki ID, misalnya RULE-COL-01, RULE-SEC-01, dan seterusnya.
7. Catat konflik, ambiguitas, risiko environment, dan asumsi.
8. Resolusi konflik harus mengikuti prioritas pada Prompt Induk.
9. Petakan struktur file yang akan dibuat atau dimodifikasi. Setiap file harus memiliki satu tanggung jawab yang jelas.
10. Susun implementation plan Modul 1-8 dalam task kecil, terurut, testable, dan menggunakan TDD untuk behavior domain.
11. Tentukan exact commands untuk lint, type check, unit test, integration test, E2E, Docker build, dan smoke test berdasarkan struktur proyek yang akan digunakan.
12. Jangan menggunakan placeholder `TBD`, `TODO`, "implement later", atau instruksi kabur.

## Output Wajib

- Task artifact Antigravity yang aktif dan mutakhir.
- Requirement traceability matrix.
- Ringkasan arsitektur final MVP.
- File map.
- Implementation plan berurutan.
- Daftar risiko dan mitigasi.
- Daftar keputusan yang sudah diselesaikan oleh Prompt Induk.
- Pertanyaan pengguna hanya jika ada keputusan material yang tidak dapat diselesaikan dari dokumen.

## Acceptance Criteria

- Semua dokumen sumber telah tercakup pada traceability matrix.
- Semua FR dan NFR memiliki status scope yang eksplisit.
- Setiap requirement MVP dipetakan ke modul dan metode verifikasi.
- Konflik `pending review` versus health status sudah diselesaikan dengan `review_status`.
- Konflik RBAC roadmap versus security rule sudah diselesaikan dengan RBAC minimum pada MVP.
- Tidak ada implementation code yang dibuat.
- Rencana cukup spesifik untuk dikerjakan tanpa menebak struktur utama.

Akhiri dengan laporan stage gate Modul 0. Jangan memulai Modul 1.
```

---

# Modul 1 - Fondasi Proyek dan Docker Compose

```text
Jalankan Modul 1 saja berdasarkan Prompt Induk dan hasil Modul 0.

## Tujuan

Membuat fondasi aplikasi yang reproducible dengan frontend, backend, collector-worker, PostgreSQL, Prometheus, dan reverse proxy di Docker Compose.

## Tugas

1. Perbarui task artifact dan tandai Modul 1 aktif.
2. Buat struktur proyek sesuai file map Modul 0. Jika workspace sudah memiliki struktur, adaptasikan tanpa refactor yang tidak relevan.
3. Inisialisasi backend FastAPI minimum dengan endpoint liveness dan readiness.
4. Inisialisasi worker sebagai process/container terpisah dengan health signal yang dapat diperiksa.
5. Inisialisasi frontend React TypeScript Vite dengan halaman shell minimum.
6. Tambahkan PostgreSQL, Prometheus, dan reverse proxy.
7. Buat multi-stage Dockerfile untuk backend/worker dan frontend.
8. Gunakan user non-root pada application container bila memungkinkan.
9. Buat Docker Compose development dan production-like yang jelas.
10. Tambahkan internal network, named volumes, health checks, startup retry/backoff, dan graceful shutdown.
11. Pin semua image dan dependency penting. Jangan gunakan `latest`.
12. Buat `.env.example` tanpa secret nyata.
13. Buat directory/convention untuk local secret yang di-ignore Git serta production Docker secrets.
14. Konfigurasikan reverse proxy untuk REST dan WebSocket upgrade. TLS production harus ready tanpa memaksa sertifikat publik pada development lokal.
15. Tambahkan baseline lint, format, type check, dan test setup.
16. Tambahkan test untuk health endpoints dan smoke test frontend shell.
17. Pastikan backend tidak mengeksekusi migration secara tidak aman dari banyak replica. Sediakan migration command/job yang eksplisit.

## Acceptance Criteria

- `docker compose config` valid.
- Semua image aplikasi dapat dibangun.
- Stack dapat dijalankan dengan satu command yang terdokumentasi.
- PostgreSQL dan Prometheus menggunakan named volume.
- Database dan Prometheus tidak diekspos publik pada production-like configuration.
- Reverse proxy menjadi entry point utama.
- Backend liveness dan readiness memberikan status yang benar.
- Frontend shell dapat diakses melalui reverse proxy.
- Tidak ada secret nyata atau default password lemah di repository.
- Formatter, lint, type check, dan test baseline lulus.
- Container aplikasi tidak berjalan sebagai root kecuali ada alasan teknis yang didokumentasikan.

## Verifikasi Minimum

Jalankan command aktual yang sesuai repository untuk:

- Validasi Compose.
- Build seluruh image.
- Menjalankan stack.
- Melihat status dan health semua service.
- Memanggil backend liveness/readiness melalui reverse proxy.
- Membuka atau menguji frontend melalui entry point.
- Menjalankan lint, type check, dan test.
- Mematikan stack secara graceful tanpa menghapus persistent volume.

Akhiri dengan daftar file berubah dan laporan stage gate Modul 1. Jangan memulai Modul 2.
```

---

# Modul 2 - Database, Authentication, dan RBAC Minimum

```text
Jalankan Modul 2 saja berdasarkan Prompt Induk dan hasil modul sebelumnya.

## Tujuan

Membangun persistence inventory/topology serta autentikasi dan RBAC minimum yang aman.

## Tugas

1. Perbarui task artifact dan tandai Modul 2 aktif.
2. Dengan TDD, implementasikan model dan migration minimum untuk:
   - nodes
   - node_connections
   - users
   - roles atau role enum yang tervalidasi
   - audit_logs
   - collector_targets atau model konfigurasi target yang hanya menyimpan credential reference
   - collector run/failure state jika diperlukan untuk transisi status
3. Tambahkan database constraints dan index untuk:
   - UUID primary key.
   - Hierarki parent node.
   - Unique external identity per source/target agar discovery idempotent.
   - Pencegahan edge duplikat.
   - Filter status/type/review status.
4. Cegah hierarchy cycle pada service boundary dan tambahkan test.
5. Implementasikan migration forward dan uji migration pada database kosong.
6. Implementasikan bootstrap admin idempotent dari Docker/file secret atau environment reference aman.
7. Implementasikan login, current user, dan logout jika diperlukan oleh mekanisme auth.
8. Pilih mekanisme auth web yang aman. Prioritaskan secure HttpOnly cookie/session atau pola lain yang meminimalkan token exposure. Dokumentasikan alasan.
9. Terapkan role authorization:
   - admin: read dan approval/configuration MVP.
   - operator: read data operasional.
   - viewer: read-only.
10. Implementasikan audit login berhasil/gagal dan tindakan admin yang tersedia pada modul ini.
11. Jangan log password, hash, token, cookie, private key, atau secret.
12. Tambahkan rate limiting atau proteksi brute-force minimum pada login bila dapat dilakukan tanpa service tambahan yang berlebihan.
13. Tambahkan API error schema konsisten.
14. Tambahkan test unit/integration untuk model, migration, login, invalid login, bootstrap idempotency, role matrix, dan audit.

## Acceptance Criteria

- Migration berhasil pada PostgreSQL kosong.
- Rollback migration terbaru diuji bila aman dan sesuai strategi migration.
- Bootstrap admin tidak membuat user duplikat.
- Password disimpan sebagai adaptive hash yang kuat.
- Endpoint terproteksi menolak anonymous user.
- Viewer/operator tidak dapat menjalankan aksi admin.
- Login berhasil dan gagal tercatat tanpa membocorkan secret.
- Node dan edge duplikat dicegah oleh kombinasi service logic dan database constraint.
- Hierarchy cycle ditolak.
- Seluruh test Modul 2 lulus.
- Restart container tidak menghilangkan data PostgreSQL.

Akhiri dengan laporan stage gate Modul 2. Jangan memulai Modul 3.
```

---

# Modul 3 - Collector Framework dan Discovery Adapter

```text
Jalankan Modul 3 saja berdasarkan Prompt Induk dan hasil modul sebelumnya.

## Tujuan

Membangun framework collector yang aman, ringan, dapat diuji, dan mendukung SSH, WinRM/Hyper-V, serta Docker TLS.

## Tugas

1. Perbarui task artifact dan tandai Modul 3 aktif.
2. Definisikan contract collector yang menghasilkan normalized discovery result dan normalized metrics result.
3. Pisahkan adapter:
   - Linux host melalui SSH.
   - Windows host melalui WinRM.
   - Hyper-V discovery melalui PowerShell command read-only.
   - Docker host/container melalui Docker Engine API dengan TLS mutual authentication.
4. Semua adapter harus menerima credential melalui secret provider/reference, bukan plaintext database.
5. Implementasikan CRUD minimum collector target khusus admin dan operasi test connection yang tidak menyimpan atau mengembalikan isi secret.
6. Buat secret provider boundary dengan implementasi Docker/file secret untuk MVP dan interface yang dapat diganti Vault di masa depan.
7. Implementasikan timeout default 10 detik.
8. Implementasikan host-key verification untuk SSH dan certificate verification untuk TLS.
9. Larang insecure Docker port 2375 dan `verify=False` pada production-like mode.
10. Normalisasikan identity source agar scan berulang idempotent.
11. Implementasikan scheduler:
    - Status poll default 60 detik, valid range 30-60 detik.
    - Inventory scan default 300 detik.
    - Metrics collection default 60 detik.
12. Tambahkan bounded concurrency agar 50 server/VM dan 200 container tidak dipoll tanpa batas.
13. Tambahkan retry dengan backoff dan jitter secara terbatas. Jangan membuat retry storm.
14. Satu timeout/failure menghasilkan `unknown` dan memperbarui failure state.
15. Status `down` baru setelah kegagalan berturut-turut melewati lebih dari 2 menit.
16. Success berikutnya mereset failure state dan memperbarui `last_seen`.
17. Discovery node baru menghasilkan `review_status=pending`.
18. Tambahkan fake collector deterministik untuk test/demo.
19. Mock seluruh akses jaringan pada automated test.
20. Pastikan log terstruktur tidak memuat command output sensitif atau credential.
21. Tambahkan test untuk CRUD/authorization collector target, test connection, normalisasi, timeout, retry limit, concurrency bound, idempotency key, pending review, unknown/down transition, recovery, dan invalid interval.

## Acceptance Criteria

- Setiap adapter memenuhi contract yang sama.
- Worker dapat menjalankan fake collector end-to-end tanpa host eksternal.
- Admin dapat membuat/mengubah collector target dan menjalankan test connection; operator/viewer tidak dapat.
- API tidak pernah mengembalikan isi credential atau secret.
- Automated test tidak membutuhkan SSH/WinRM/Docker server nyata.
- Interval di bawah 30 atau di atas 60 detik ditolak untuk status polling.
- Timeout tunggal menghasilkan unknown, bukan down.
- Failure window lebih dari 2 menit menghasilkan down secara deterministik.
- Recovery menghasilkan up dan mereset failure state.
- Node baru selalu pending review.
- Docker adapter menolak konfigurasi remote yang tidak memiliki TLS production-like.
- Secret tidak muncul pada log atau exception response.
- Seluruh test Modul 3 lulus.

Akhiri dengan laporan stage gate Modul 3. Jangan memulai Modul 4.
```

---

# Modul 4 - Inventory Service dan Topology Builder

```text
Jalankan Modul 4 saja berdasarkan Prompt Induk dan hasil modul sebelumnya.

## Tujuan

Mengubah hasil collector menjadi inventory dan graph topology yang konsisten, idempotent, dan siap dikonsumsi frontend.

## Tugas

1. Perbarui task artifact dan tandai Modul 4 aktif.
2. Dengan TDD, implementasikan normalized inventory upsert.
3. Infer relasi:
   - Data center yang dikelola admin menjadi grouping root untuk host approved.
   - VM memiliki parent host kanonis dengan capability Hyper-V.
   - Container memiliki parent host kanonis dengan capability Docker.
   - Physical server dapat menjadi root sementara sebelum ditempatkan ke data center, tanpa menghasilkan duplikasi identitas.
4. Terapkan keputusan satu host kanonis dari Prompt Induk. Jangan membuat node bayangan untuk setiap capability.
5. Implementasikan naming validation saat approval:
   - Node host mengikuti `[TYPE]-[LOKASI]-[FUNGSI]-[NOMOR]`.
   - Container menggunakan display name `<docker-host>/<container-name>`.
   - Nama asli container tetap disimpan pada metadata.
6. Discovery dengan nama tidak valid tetap disimpan sebagai pending dan menyertakan validation issue.
7. Implementasikan endpoint daftar node dengan pagination, search, filter type, status, review status, dan lifecycle status.
8. Implementasikan endpoint detail dan children.
9. Implementasikan approval dan rejection khusus admin beserta audit log.
10. Implementasikan CRUD minimum data center dan assignment/reassignment host khusus admin beserta audit/changelog.
11. Implementasikan topology builder yang menghasilkan JSON nodes dan edges stabil.
12. Gunakan recursive query atau service traversal yang efisien, dengan perlindungan cycle.
13. Default topology hanya menampilkan node approved/active. Sediakan opsi admin untuk melihat pending jika kebutuhan UI jelas.
14. Implementasikan archive lifecycle. Jangan hard-delete node sebelum aturan retention memungkinkan.
15. Tambahkan topology changelog/event minimum untuk approval, data-center assignment, parent change, archive, dan relationship change agar perubahan besar dapat ditelusuri.
16. Tambahkan test API dan service untuk upsert, hierarchy, data center, filtering, pagination, approval, audit, graph, cycle defense, dan archive behavior.

## Kontrak Response Topology Minimum

Setiap topology node harus menyediakan sekurangnya:

- `id`
- `name`
- `type`
- `status`
- `parent_id`
- metadata presentasi minimum yang aman

Setiap edge harus menyediakan sekurangnya:

- `id`
- `source`
- `target`
- `connection_type`

Jangan mengekspos credential reference, secret path sensitif, hash, atau internal exception.

## Acceptance Criteria

- Scan fake collector berulang tidak menambah node/edge duplikat.
- Data center dapat dibuat admin dan menjadi grouping root untuk host yang ditetapkan.
- VM dan container memiliki parent host kanonis yang benar.
- Node pending tidak muncul pada topology operasional default.
- Admin dapat approve/reject; operator/viewer tidak dapat.
- Naming invalid menghasilkan validation error yang jelas pada approval.
- API list memiliki pagination dan semua filter wajib.
- Graph stabil dan bebas cycle.
- Archive tidak langsung menghapus record.
- Perubahan topology utama dapat ditelusuri melalui audit/changelog.
- Seluruh test Modul 4 lulus.

Akhiri dengan laporan stage gate Modul 4. Jangan memulai Modul 5.
```

---

# Modul 5 - Prometheus Metrics dan Live Status

```text
Jalankan Modul 5 saja berdasarkan Prompt Induk dan hasil modul sebelumnya.

## Tujuan

Mengintegrasikan current/basic metrics melalui Prometheus dan mengirim status delta secara aman melalui WebSocket.

## Tugas

1. Perbarui task artifact dan tandai Modul 5 aktif.
2. Gunakan Prometheus pull model untuk MVP: collector-worker mengekspos endpoint metrics internal yang di-scrape Prometheus. Jangan menambahkan Pushgateway kecuali ditemukan kebutuhan batch/ephemeral yang terbukti dan disetujui.
3. Hindari high-cardinality label. Gunakan stable node ID sebagai label identity utama dan metric name allowlist; jangan gunakan metadata bebas sebagai label.
4. Pastikan sample node yang tidak lagi ditemukan tidak terus diekspos selamanya. Terapkan stale-series cleanup yang teruji.
5. Konfigurasikan retention Prometheus minimal 90 hari untuk production-like deployment dan dokumentasikan konsekuensi storage.
6. Jangan menjanjikan downsampling satu tahun yang tidak didukung Prometheus tunggal. Catat sebagai roadmap operasional.
7. Implementasikan query service backend ke Prometheus dengan timeout, error mapping, dan bounded range.
8. Implementasikan endpoint metrics dengan:
   - `node_id` wajib.
   - Range allowlist yang relevan dengan MVP.
   - Metric allowlist CPU, RAM, disk, network in, network out.
   - Response schema stabil.
9. Jangan memberikan frontend akses langsung ke Prometheus.
10. Implementasikan WebSocket `/ws/status` dengan autentikasi dan authorization.
11. Kirim delta minimum: node ID, status baru, timestamp, dan field aman yang diperlukan UI.
12. Tambahkan reconnect/backoff expectation pada kontrak frontend.
13. Jangan mengirim seluruh graph pada setiap status update.
14. Tambahkan test query mapping dengan fake Prometheus server/client.
15. Tambahkan test stale-series cleanup, unauthorized WebSocket, authorized connection, delta schema, timeout Prometheus, range invalid, dan node invalid.
16. Tambahkan metrics untuk memonitor backend/worker sendiri jika sederhana dan tidak menciptakan recursion yang membingungkan.

## Acceptance Criteria

- Prometheus scrape target worker sehat dalam demo stack.
- Current/basic metrics fake/demo dapat diambil melalui backend.
- Series untuk node yang dihapus dari active exporter set menjadi stale/tidak terus diekspos.
- Frontend tidak perlu mengetahui URL internal Prometheus.
- Query invalid ditolak dengan error schema konsisten.
- WebSocket menolak anonymous user.
- Status delta tidak membocorkan metadata sensitif.
- Disconnect/reconnect tidak menjatuhkan backend.
- Retention 90 hari tercermin pada production-like configuration.
- Seluruh test Modul 5 lulus.

Akhiri dengan laporan stage gate Modul 5. Jangan memulai Modul 6.
```

---

# Modul 6 - Frontend Dashboard, Inventory, dan Topology

```text
Jalankan Modul 6 saja berdasarkan Prompt Induk dan hasil modul sebelumnya.

## Tujuan

Membangun UI MVP yang operasional, responsif, mudah dipahami, dan terhubung ke API nyata.

## Tugas

1. Perbarui task artifact dan tandai Modul 6 aktif.
2. Pertahankan visual language existing jika sudah ada. Jika belum ada, buat dashboard operasional yang padat informasi, tenang, mudah dibaca, dan bukan template SaaS generik.
3. Implementasikan auth flow dan route protection.
4. Implementasikan navigation Dashboard, Topology, Inventory, dan Administration yang hanya tampil untuk admin.
5. Implementasikan Administration minimum:
   - Registrasi dan perubahan collector target dengan credential reference.
   - Test connection dengan hasil aman.
   - Pembuatan data center dan assignment host.
   - Jangan pernah menampilkan kembali isi secret.
6. Implementasikan Dashboard:
   - Total server/VM yang definisinya dijelaskan.
   - Total container.
   - Node bermasalah.
   - Uptime rata-rata hanya bila backend menyediakan data yang valid; jangan mengarang angka.
   - Mini topology overview.
7. Implementasikan Inventory:
   - Pagination.
   - Search.
   - Filter type, status, review status.
   - Empty/loading/error state.
   - Approval/rejection hanya terlihat dan dapat digunakan admin.
   - Validation issue naming terlihat sebelum approval.
8. Implementasikan Topology dengan React Flow:
   - Hierarchical layout otomatis.
   - Pan, zoom, fit view.
   - Status colors dan label/icon agar tidak bergantung pada warna saja.
   - Status legend.
   - Node type visual distinction.
   - Klik node membuka detail panel.
   - Loading, empty, error, dan retry state.
9. Detail panel menampilkan spesifikasi, IP, last seen, metadata aman, serta current/basic metrics chart.
10. Hubungkan WebSocket status delta ke cache/state graph tanpa refetch seluruh graph setiap event.
11. Terapkan reconnect dengan exponential backoff dan cleanup connection yang benar.
12. Tambahkan responsive behavior desktop/mobile.
13. Hormati keyboard navigation, focus state, semantic controls, contrast, dan `prefers-reduced-motion`.
14. Jangan implementasikan export, network view, laporan, alert pages, atau traffic animation kompleks pada MVP.
15. Tambahkan test komponen dan integration untuk auth, administration, dashboard states, inventory filters, role visibility, topology rendering, detail panel, dan status delta.
16. Tambahkan Playwright smoke test untuk login, collector target registration/test connection, data center assignment, dashboard, inventory, admin approval, dan topology.

## Acceptance Criteria

- Anonymous user diarahkan ke login.
- Viewer/operator tidak melihat atau tidak dapat memicu aksi admin.
- Admin dapat meregistrasikan collector target, menjalankan test connection, membuat data center, dan menetapkan host tanpa secret disclosure.
- Dashboard menggunakan data API, bukan angka hardcoded.
- Inventory filter dan pagination bekerja.
- Pending node dapat di-review admin.
- Topology approved nodes dirender dengan layout otomatis.
- Status dapat dibedakan tanpa hanya mengandalkan warna.
- Klik node membuka detail dan metrics.
- Delta WebSocket memperbarui node yang tepat tanpa full graph refetch.
- UI dapat digunakan pada viewport desktop dan mobile.
- Loading, empty, error, dan retry state tersedia.
- Test frontend dan Playwright smoke test lulus.

Akhiri dengan laporan stage gate Modul 6. Jangan memulai Modul 7.
```

---

# Modul 7 - Security, Reliability, Backup, dan Scale Validation

```text
Jalankan Modul 7 saja berdasarkan Prompt Induk dan hasil modul sebelumnya.

## Tujuan

Mengeraskan MVP, memvalidasi failure behavior, dan membuktikan aplikasi siap dijalankan melalui Docker secara aman dalam skala target.

## Tugas

1. Perbarui task artifact dan tandai Modul 7 aktif.
2. Audit repository dan Docker build context untuk secret, credential, private key, token, unsafe example, dan file sensitif.
3. Audit auth, CORS, cookie/session flags, CSRF jika relevan, security headers, error disclosure, dan log redaction.
4. Audit Docker:
   - Image pinning.
   - Non-root execution.
   - Read-only filesystem bila praktis.
   - Dropped capabilities bila praktis.
   - Internal network.
   - Health checks.
   - Resource limits production-like.
   - No public database/Prometheus exposure.
5. Verifikasi graceful shutdown dan restart recovery backend/worker.
6. Simulasikan PostgreSQL belum ready dan Prometheus timeout. Pastikan retry/backoff dan error state benar.
7. Simulasikan collector timeout, intermittent failure, dan recovery.
8. Buat deterministic scale fixture untuk minimal 50 server/VM dan 200 container.
9. Jalankan benchmark/smoke performance yang mengukur:
   - Inventory list API.
   - Topology build API.
   - Frontend topology render minimum.
   - Worker bounded concurrency.
10. Gunakan threshold yang realistis berdasarkan environment dan catat hardware/runtime test. Jangan mengklaim universal performance dari satu mesin.
11. Tinjau target overhead collector kurang dari 2% CPU. Jika tidak dapat diuji pada host nyata, sediakan metodologi pengukuran dan jangan mengklaim target sudah terbukti.
12. Implementasikan backup PostgreSQL script/job yang aman dan dapat dijadwalkan harian.
13. Implementasikan prosedur restore dan uji restore ke database disposable.
14. Dokumentasikan named-volume backup consideration untuk Prometheus tanpa menjanjikan HA.
15. Dokumentasikan external uptime checker untuk mendeteksi monitoring stack down.
16. Jalankan dependency vulnerability scan dan image scan jika tool tersedia. Pisahkan finding yang benar-benar dapat ditindaklanjuti dari noise.
17. Perbaiki finding severity tinggi/kritis yang berada dalam kontrol proyek atau dokumentasikan blocker konkret.

## Acceptance Criteria

- Tidak ada secret nyata pada repository, image layer, frontend bundle, atau log test.
- Database dan Prometheus tidak publik pada production-like Compose.
- Auth/security header/cookie policy sesuai deployment mode.
- Failure PostgreSQL/Prometheus/collector menghasilkan behavior terkontrol.
- Dataset 50 server/VM dan 200+ container dapat diproses tanpa error atau unbounded concurrency.
- Klaim performa disertai command, hasil aktual, dan konteks environment.
- Backup berhasil dibuat.
- Restore ke database disposable berhasil dan diverifikasi.
- Critical/high security findings diselesaikan atau memiliki mitigasi dan blocker yang jelas.
- Semua regression test lulus.

Akhiri dengan laporan stage gate Modul 7. Jangan memulai Modul 8.
```

---

# Modul 8 - End-to-End Acceptance dan Handover

```text
Jalankan Modul 8 saja berdasarkan Prompt Induk dan hasil modul sebelumnya.

## Tujuan

Memverifikasi MVP dari kondisi deploy baru, menyelesaikan traceability, dan menghasilkan handover operasional yang dapat digunakan tim lain.

## Tugas

1. Perbarui task artifact dan tandai Modul 8 aktif.
2. Re-read semua dokumen sumber dan requirement traceability matrix.
3. Lakukan clean-environment verification tanpa menghapus data atau perubahan pengguna yang tidak terkait.
4. Validasi seluruh Compose configuration.
5. Build seluruh image tanpa bergantung pada dependency host yang tidak terdokumentasi.
6. Jalankan migration pada PostgreSQL kosong.
7. Jalankan bootstrap admin menggunakan secret dummy lokal yang aman.
8. Aktifkan demo seed secara eksplisit.
9. Jalankan seluruh stack dan tunggu health checks.
10. Jalankan seluruh backend unit/integration tests.
11. Jalankan seluruh frontend unit/integration tests.
12. Jalankan lint, formatter check, dan type check seluruh komponen.
13. Jalankan Playwright E2E melalui reverse proxy untuk:
    - Login.
    - Dashboard.
    - Inventory/filter.
    - Approval pending node sebagai admin.
    - Viewer/operator authorization.
    - Topology.
    - Node detail dan metrics.
14. Jalankan fake collector minimal dua kali dan buktikan tidak ada node/edge duplikat.
15. Trigger fake timeout, down transition, recovery, dan WebSocket status update.
16. Uji restart stack tanpa kehilangan PostgreSQL/Prometheus data yang seharusnya persisten.
17. Uji backup dan restore satu kali lagi dari prosedur dokumentasi final jika prosedur berubah.
18. Lengkapi dokumentasi:
    - Prerequisite.
    - Development startup.
    - Production-like deployment.
    - TLS setup.
    - Secret provisioning.
    - Migration.
    - Bootstrap admin.
    - Demo mode.
    - Onboarding Linux SSH target.
    - Onboarding Windows/Hyper-V target.
    - Onboarding Docker TLS target.
    - Firewall/network ports tanpa membuka Docker insecure API.
    - Backup dan restore.
    - Troubleshooting.
    - Known limitations.
    - Roadmap.
19. Perbarui traceability matrix dengan status final:
    - Implemented and verified.
    - Implemented but not environment-verified.
    - Deferred to roadmap dengan alasan.
    - Out of scope.
20. Jangan menandai requirement verified jika tidak ada bukti command/test aktual.
21. Tandai task artifact selesai hanya setelah semua gate lulus.

## Acceptance Criteria

- Semua Definition of Done pada Prompt Induk terpenuhi.
- Stack dapat dibangun dan dijalankan dari instruksi dokumentasi.
- Semua service wajib sehat.
- Seluruh automated test wajib lulus.
- Tidak ada migration atau setup manual tersembunyi.
- Discovery fake idempotent terbukti.
- Auth, RBAC, inventory, approval, metrics, topology, dan status delta terbukti melalui E2E/integration test.
- Persistence, backup, dan restore terbukti.
- Traceability matrix final tidak memiliki requirement MVP tanpa status dan bukti.
- Fitur roadmap tidak diklaim sebagai MVP selesai.

## Format Laporan Akhir

Laporkan:

1. Ringkasan hasil MVP.
2. Arsitektur final dan service Docker.
3. File/direktori utama.
4. Command deployment.
5. Command test dan hasil aktual.
6. Bukti acceptance utama.
7. Requirement yang diverifikasi.
8. Requirement yang belum dapat diverifikasi pada environment nyata.
9. Deferred roadmap.
10. Risiko dan known limitations.

Jangan membuat commit, push, atau pull request kecuali diminta pengguna.
```

---

# Prompt Resume Antigravity

Gunakan prompt berikut jika pekerjaan dilanjutkan pada sesi baru:

```text
Lanjutkan pembangunan aplikasi Infrastructure Monitoring & Auto-Topology pada workspace ini.

Sebelum mengubah kode:

1. Baca docs/PRD.md, docs/Architecture.md, docs/Design.md, docs/Rules.md, dan dokumen prompt pembangunan yang tersimpan di docs.
2. Temukan dan baca task artifact Antigravity serta requirement traceability matrix terbaru.
3. Inspeksi status workspace dan perubahan existing. Jangan menghapus atau mereset perubahan yang tidak Anda buat.
4. Identifikasi modul aktif terakhir dan acceptance criteria yang belum terpenuhi.
5. Jalankan verifikasi modul aktif untuk memastikan state aktual, jangan hanya mempercayai laporan sesi sebelumnya.
6. Lanjutkan hanya modul aktif. Jangan melompati stage gate.
7. Perbarui task artifact saat mulai dan setelah setiap hasil penting.
8. Setelah selesai, laporkan file berubah, keputusan, command verifikasi, hasil aktual, serta risiko tersisa.

Jika task artifact tidak ditemukan, jangan menebak progress. Rekonstruksi status dari source, test, Docker configuration, dan requirement traceability matrix, lalu minta konfirmasi sebelum melakukan perubahan material.
```

---

# Prompt Roadmap V1.1 - Alerting, Historical Metrics, dan Export

Jalankan prompt ini hanya setelah MVP Modul 0-8 selesai.

```text
Rencanakan dan implementasikan V1.1 untuk aplikasi Infrastructure Monitoring & Auto-Topology yang MVP-nya sudah selesai.

Baca ulang seluruh dokumen sumber, prompt induk, traceability matrix, dan source aktual. Buat task artifact baru khusus V1.1. Jangan mengubah kontrak MVP secara breaking tanpa migration dan alasan kuat.

Scope V1.1:

- Alert rule per node/grup.
- CPU warning >85% selama 5 menit dan critical >95% selama 5 menit.
- RAM warning >85% dan critical >95% dengan duration policy yang dibuat eksplisit.
- Disk warning >80% dan critical >90% dengan duration policy yang dibuat eksplisit.
- Down lebih dari 2 menit menjadi critical.
- Deduplication minimal 15 menit selama kondisi belum berubah.
- Auto-resolve dan resolve notification.
- Escalation critical yang belum acknowledged selama 15 menit.
- Notification provider modular, dimulai dari satu channel yang dapat diuji tanpa credential nyata; provider lain ditambahkan bertahap.
- Alerts active/history dan acknowledgement dengan audit.
- Historical metrics UI dengan range 1h, 24h, 7d, 30d.
- Export topology PNG/SVG/PDF dengan timestamp snapshot.
- Retention dan query performance validation.

Gunakan proses modular dan stage gate yang sama dengan MVP: analisis, design, TDD, implementation, security, Docker verification, E2E, dan traceability. Jangan membangun V1.2 atau V2.
```

---

# Prompt Roadmap V1.2 - Live Animation dan Network Topology

Jalankan prompt ini hanya setelah V1.1 selesai.

```text
Rencanakan dan implementasikan V1.2 untuk aplikasi Infrastructure Monitoring & Auto-Topology.

Baca seluruh dokumen sumber, keputusan MVP/V1.1, traceability matrix, dan source aktual. Buat task artifact baru khusus V1.2.

Scope V1.2:

- Status pulse pada perubahan status.
- Optional animated traffic edge berdasarkan data yang benar-benar tersedia.
- Toggle animasi dan dukungan `prefers-reduced-motion`.
- Hierarchy View dan Network View.
- Network discovery melalui capability adapter terpisah untuk SNMP/ARP/traceroute.
- Manual mapping fallback dengan audit log.
- VLAN/subnet hanya ditampilkan jika data dapat dipercaya dan source/provenance terlihat.
- Network edge deduplication, confidence/provenance, dan stale-data handling.
- Performance test topology besar.

Jangan merepresentasikan traffic palsu sebagai traffic real. Jika hanya konektivitas yang diketahui, label sebagai koneksi, bukan traffic aktif. Gunakan stage gate, TDD, security review, Docker verification, E2E, dan traceability. Jangan membangun V2.
```

---

# Prompt Roadmap V2 - Governance, Reporting, dan Integrasi

Jalankan prompt ini hanya setelah V1.2 selesai dan scope V2 disetujui kembali.

```text
Rencanakan V2 aplikasi Infrastructure Monitoring & Auto-Topology berdasarkan dokumen sumber dan implementasi aktual.

Buat task artifact baru dan proposal design sebelum coding. Pecah V2 menjadi subproyek independen karena scope besar:

1. User management dan RBAC advanced.
2. SSO/LDAP.
3. Laporan mingguan/bulanan PDF/Excel.
4. Scheduled report delivery.
5. Topology history dan change comparison.
6. Cloudflare status integration.
7. Ticketing integration.
8. Secrets provider HashiCorp Vault.
9. High availability dan disaster recovery deployment.
10. Governance workflow untuk quarterly RBAC/threshold review.

Untuk setiap subproyek, buat design, threat model, migration strategy, acceptance criteria, rollback plan, tests, dan Docker/deployment impact. Jangan mengimplementasikan semua subproyek dalam satu perubahan besar. Minta pengguna memilih prioritas subproyek pertama sebelum coding.
```
