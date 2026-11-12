# Backend Sistem Penerimaan Mahasiswa Baru (PMB) FastAPI

Repository ini berisi kode sumber backend untuk modul Penerimaan Mahasiswa Baru (PMB) yang dibangun menggunakan FastAPI dan SQLAlchemy, dikembangkan untuk memenuhi tugas mata kuliah Dasar-dasar Komputasi Awan dan Terdistribusi.

## Identitas Penyusun
- **Nama:** Nabila Latifatul Hamdah
- **NIM:** 24360006
- **Institusi:** Institut Sains dan Teknologi Nasional (ISTN) Jakarta

## Fitur Utama
1. **Registrasi Calon Mahasiswa:** Validasi input data diri dan pencegahan duplikasi email (mengembalikan status `409 Conflict`).
2. **Manajemen Status Pendaftaran:** Pengelolaan status calon mahasiswa (`pending`, `approved`, `rejected`).
3. **NIM Generator Otomatis:** Fungsi pembuatan NIM institusional berbasis format `24360006` yang aman dari *race condition* dan bersifat *idempotent*.
4. **Unit Testing:** Pengujian otomatis menggunakan `pytest`.

## Cara Menjalankan Proyek

1. **Clone repository ini:**
   ```bash
   git clone [https://github.com/username/fastapi-pmb-system.git](https://github.com/username/fastapi-pmb-system.git)
   cd fastapi-pmb-system
