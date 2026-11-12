"""Seed data referensi (idempotent). Jalankan: python -m app.seed"""
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import JalurMasuk, ProgramStudi

PROGRAM_STUDI = [
    (1, "360", "Teknik Informatika", "Fakultas Teknik"),
    (2, "361", "Sistem Informasi", "Fakultas Teknik"),
    (3, "362", "Teknik Elektro", "Fakultas Teknik"),
    (4, "363", "Manajemen", "Fakultas Ekonomi dan Bisnis"),
]

JALUR_MASUK = [
    (1, "SNBP", "Seleksi Nasional Berdasarkan Prestasi"),
    (2, "SNBT", "Seleksi Nasional Berdasarkan Tes"),
    (3, "MANDIRI", "Seleksi Mandiri"),
]


def seed_reference_data(db: Session) -> None:
    for id_, kode, nama, fakultas in PROGRAM_STUDI:
        if db.get(ProgramStudi, id_) is None:
            db.add(ProgramStudi(id=id_, kode=kode, nama=nama, fakultas=fakultas))
    for id_, kode, nama in JALUR_MASUK:
        if db.get(JalurMasuk, id_) is None:
            db.add(JalurMasuk(id=id_, kode=kode, nama=nama))
    db.commit()


if __name__ == "__main__":  # pragma: no cover
    with SessionLocal() as session:
        seed_reference_data(session)
    print("Seed selesai.")
