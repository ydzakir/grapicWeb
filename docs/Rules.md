# Rules.md — Kebijakan Operasional Aplikasi Monitoring Infrastruktur

## 1. Aturan Pengumpulan Data (Data Collection)
1. Interval polling status (up/down): **maksimal 60 detik**, tidak boleh lebih cepat dari 30 detik agar tidak membebani jaringan/host target.
2. Interval full inventory scan (deteksi server/container baru): **setiap 5 menit**.
3. Interval metrik detail (CPU/RAM/Disk/network): **setiap 60 detik**, disimpan sebagai time-series.
4. Setiap collector **wajib** memiliki timeout (mis. 10 detik) — jika host tidak merespons dalam waktu tersebut, status ditandai `unknown`, bukan langsung `down` (untuk menghindari false alarm akibat network hiccup).
5. Node baru yang terdeteksi otomatis **tidak langsung dianggap valid** — masuk status `pending review` sampai dikonfirmasi admin (mencegah noise dari container sementara/testing).

## 2. Aturan Penamaan (Naming Convention)
- Format nama node: `[TYPE]-[LOKASI]-[FUNGSI]-[NOMOR]`
  - Contoh: `HV-DC1-WEB-01` (Hyper-V host, Data Center 1, fungsi Web, nomor urut 01).
- Container di-mapping menggunakan nama container Docker asli, dengan prefix host: `DOCKER-HOST01/app-nginx`.
- Konsistensi naming wajib diverifikasi saat onboarding server baru agar diagram topologi tetap terbaca rapi.

## 3. Aturan Keamanan & Akses
1. Kredensial akses ke tiap host (SSH key, WinRM credential, Docker TLS cert) **wajib disimpan di secrets vault terenkripsi** — dilarang hardcode di file konfigurasi/kode.
2. Prinsip **least privilege**: akun service yang digunakan collector hanya diberi hak baca (read-only) terhadap resource yang dipantau, tidak boleh punya hak modifikasi.
3. Docker Remote API **wajib** menggunakan TLS mutual authentication — port Docker API tidak boleh terbuka tanpa autentikasi ke jaringan luas.
4. Akses ke dashboard monitoring menggunakan **RBAC**:
   - `admin`: full access, kelola user & threshold.
   - `operator`: lihat semua data, acknowledge alert.
   - `viewer`: read-only, untuk laporan ke management.
5. Semua akses (login, perubahan konfigurasi, acknowledge alert) **wajib tercatat di audit log**.
6. Komunikasi antar-komponen (collector → backend → frontend) wajib terenkripsi (TLS/HTTPS/WSS).

## 4. Aturan Alerting
1. Threshold default (dapat disesuaikan per node/grup):
   - CPU usage > 85% selama 5 menit → `warning`; > 95% selama 5 menit → `critical`.
   - RAM usage > 85% → `warning`; > 95% → `critical`.
   - Disk usage > 80% → `warning`; > 90% → `critical`.
   - Status `down` selama > 2 menit berturut-turut → `critical` alert (setelah dikurangi kemungkinan false positive dari timeout jaringan).
2. Alert **tidak boleh spam** — gunakan mekanisme *deduplication* (alert yang sama tidak dikirim ulang dalam waktu < 15 menit selama kondisi belum berubah) dan *auto-resolve notification* ketika kondisi kembali normal.
3. Eskalasi: jika alert `critical` tidak di-acknowledge dalam 15 menit, kirim notifikasi ke channel eskalasi kedua (mis. grup WhatsApp/Telegram tim, bukan hanya individual).

## 5. Aturan Retensi Data
- Data metrik time-series disimpan **minimal 90 hari** dalam resolusi penuh, setelah itu di-downsample (mis. rata-rata per jam) untuk hemat storage, disimpan hingga 1 tahun.
- Log audit disimpan minimal **1 tahun** untuk kebutuhan investigasi/compliance internal.
- Data node yang sudah tidak aktif (decommissioned) tidak dihapus langsung, tapi ditandai `archived` selama 90 hari sebelum dihapus permanen (untuk keperluan audit historis).

## 6. Aturan Perubahan & Maintenance Topologi
1. Penambahan/penghapusan server baru **wajib** melalui proses onboarding resmi: registrasi credential + validasi naming convention, tidak sekadar "auto-discovered lalu dibiarkan".
2. Perubahan besar pada topologi (mis. migrasi host, dekomisioning server) **wajib** dicatat sebagai catatan perubahan (changelog) di sistem, agar histori topologi bisa ditelusuri.
3. Diagram yang di-export untuk dokumentasi resmi (mis. dilampirkan ke laporan management) **harus** diberi timestamp otomatis agar jelas kapan snapshot tersebut diambil (mengingat topologi bisa berubah kapan saja).

## 7. Aturan Ketersediaan Sistem Monitoring Itu Sendiri
1. Sistem monitoring **tidak boleh** dijadikan single point of failure — idealnya backend & database monitoring memiliki mekanisme backup/replikasi terpisah dari server yang dipantau.
2. Jika sistem monitoring sendiri down, **wajib** ada mekanisme notifikasi cadangan (mis. external uptime checker sederhana) yang memberi tahu tim bahwa monitoring sedang tidak berfungsi — supaya tidak terjadi "blind spot ganda".
3. Backup konfigurasi & database monitoring dilakukan **harian**, disimpan di lokasi terpisah dari server monitoring utama.

## 8. Aturan Governance & Review
- Threshold alert dan aturan RBAC direview **setiap 3 bulan** untuk memastikan masih relevan dengan kondisi infrastruktur terkini.
- Setiap penambahan tipe node baru (mis. mulai memantau perangkat network/switch) harus melalui update dokumen ini (Rules.md) agar semua tim memahami standar yang berlaku.
