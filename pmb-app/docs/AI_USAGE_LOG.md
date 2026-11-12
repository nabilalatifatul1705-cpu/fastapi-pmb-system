# AI Usage Log - Modul PMB (Minggu 3-4)

> Sesuaikan tanggal, ID commit, dan catatan Anda sendiri. Log ini harus
> mencerminkan penggunaan AI yang benar-benar Anda lakukan.

## Ringkasan
| Item | Keterangan |
|---|---|
| Tools AI | Claude (Anthropic) via chat |
| Bagian dibantu AI | Skema SQLAlchemy, migrasi Alembic, endpoint FastAPI, NIM generator, pytest |
| Bagian saya kerjakan/verifikasi sendiri | Menjalankan migrasi (upgrade+downgrade), uji Swagger/Postman, membaca & memahami logika race condition, menjalankan pytest + coverage |
| Perubahan terhadap output AI | Format NIM direvisi menjadi 8 digit (contoh 24360006); kode prodi disesuaikan (360-363) |

## Log Interaksi
| # | Tujuan | Prompt (ringkas) | Hasil | Verifikasi |
|---|---|---|---|---|
| 1 | Skema DB | Prompt Step 1 modul + minta 3 tabel, constraint telepon/email/status | Model + migrasi | `alembic upgrade head` lalu `downgrade base` sukses |
| 2 | Endpoint | Prompt Step 2 + minta 409 duplikat email & 400 validasi | Router + service | Uji manual di Swagger `/docs` |
| 3 | NIM | "Buat generate_nim thread-safe & idempotent" | RLock + FOR UPDATE + UNIQUE + retry | Test paralel 20 thread |
| 4 | Testing | Prompt Step 4 | `tests/test_pmb.py` | `pytest` hijau, coverage >= 80% |
| 5 | Revisi NIM | "Format NIM 24360006" | Format [Tahun:2][Prodi:3][Running:3] | Test `test_generate_nim_contoh_nabila_24360006` |

## Prompt Terbaik
```text
Bertindaklah sebagai Senior Backend Engineer Python. Implementasikan modul PMB
dengan FastAPI + SQLAlchemy 2.0 + Alembic (SQLite/MySQL).
Tabel: calon_mahasiswa, program_studi, jalur_masuk. Constraint: email unik,
telepon Indonesia (08xx / +62xx), status enum (pending/approved/rejected).
Endpoint: POST /register (409 jika email ganda), GET /status/{id} (404),
PUT /approve/{id} (generate NIM), GET /stats. DB session lewat Depends.
NIM = [Tahun:2][Kode Prodi:3][Running:3], contoh 24360006, harus thread-safe
dan idempotent. Sertakan pytest (fixtures, test duplikat, idempotent,
format telepon). Kode lengkap tanpa placeholder.
```
**Mengapa efektif:** peran jelas, stack & versi spesifik, kode status HTTP eksplisit,
format NIM disertai contoh, ada kriteria non-fungsional (thread-safe, idempotent),
dan larangan placeholder.

## Pemahaman Konsep (wajib dipahami)
- **Race condition NIM:** dua approve bersamaan bisa sama-sama membaca "nomor terakhir = 5"
  dan membuat NIM ke-6 yang sama. Pencegahan berlapis: `RLock` (antar-thread),
  `SELECT ... FOR UPDATE` pada baris prodi (antar-proses di MySQL), dan UNIQUE pada `nim`.
- **Idempotent:** approve kedua pada pendaftar yang sama mengembalikan NIM lama
  dan tidak memakai nomor urut baru.

## Penandaan Commit
```bash
git commit -m "feat(pmb): implementasi modul PMB [AI-assisted: Claude]" \
           -m "Co-authored-by: Claude <noreply@anthropic.com>"
```
