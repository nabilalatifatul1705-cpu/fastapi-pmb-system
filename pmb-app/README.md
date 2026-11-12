# PMB App - Penerimaan Mahasiswa Baru

FastAPI + SQLAlchemy 2.0 + Alembic + SQLite (bisa MySQL) + pytest.
Format NIM: `[Tahun:2][Kode Prodi:3][Running:3]`, contoh `24360006`.

## Menjalankan

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux
pip install -r requirements.txt

alembic upgrade head            # buat tabel + seed prodi & jalur
alembic downgrade base          # uji rollback
alembic upgrade head

pytest                          # test + coverage (min 80%)
uvicorn app.main:app --reload   # Swagger: http://localhost:8000/docs
```

## Endpoint
| Method | Path | Keterangan |
|---|---|---|
| POST | /api/pmb/register | Daftar (201; 409 email ganda; 400 input invalid) |
| GET | /api/pmb/status/{id} | Cek status (404 jika tidak ada) |
| PUT | /api/pmb/approve/{id} | Approve + generate NIM (idempotent) |
| GET | /api/pmb/stats | Statistik pendaftar |

MySQL: `set DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/pmb` dan `pip install pymysql`.
