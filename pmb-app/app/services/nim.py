"""
Generator NIM.

Format : [Tahun:2][Kode Prodi:3][Running Number:3]  -> contoh: 24360006
         24 = angkatan 2024 | 360 = kode prodi | 006 = urutan ke-6

Strategi keamanan konkurensi (race condition), berlapis:
  1. `nim_lock` (threading.RLock)  : serialisasi antar-thread dalam satu proses.
  2. SELECT ... FOR UPDATE pada baris program_studi : serialisasi antar-proses
                                     pada MySQL/PostgreSQL (SQLite sudah
                                     write-lock level database).
  3. UNIQUE constraint pada kolom `nim` : jaring pengaman terakhir; bila tetap
                                     bentrok, IntegrityError di-retry oleh
                                     service approve.

Idempotent: jika `calon.nim` sudah terisi, nilai yang sama dikembalikan dan
tidak ada nomor urut baru yang terpakai.
"""
import threading
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import NimExhaustedError
from app.models import CalonMahasiswa, ProgramStudi

NIM_YEAR_DIGITS = 2
NIM_PRODI_DIGITS = 3
NIM_RUNNING_DIGITS = 3
NIM_MAX_RUNNING = 10**NIM_RUNNING_DIGITS - 1  # 999
NIM_LENGTH = NIM_YEAR_DIGITS + NIM_PRODI_DIGITS + NIM_RUNNING_DIGITS  # 8

# RLock agar approve_pendaftar() bisa menahan lock yang sama sampai COMMIT selesai.
nim_lock = threading.RLock()


def nim_prefix(tahun: int, kode_prodi: str) -> str:
    """Contoh: (2024, '360') -> '24360'."""
    return f"{tahun % 100:0{NIM_YEAR_DIGITS}d}{kode_prodi}"


def format_nim(tahun: int, kode_prodi: str, running: int) -> str:
    """Contoh: (2024, '360', 6) -> '24360006'."""
    return f"{nim_prefix(tahun, kode_prodi)}{running:0{NIM_RUNNING_DIGITS}d}"


def generate_nim(db: Session, calon: CalonMahasiswa, tahun: int | None = None) -> str:
    """
    Isi `calon.nim` (idempotent) dan kembalikan NIM-nya.

    Hanya melakukan flush; pemanggil yang commit. Untuk penggunaan konkuren,
    panggil lewat `services.pmb.approve_pendaftar` yang menahan `nim_lock`
    sampai commit selesai.
    """
    if calon.nim:
        return calon.nim

    tahun = tahun or datetime.now(timezone.utc).year

    with nim_lock:
        prodi = db.execute(
            select(ProgramStudi)
            .where(ProgramStudi.id == calon.program_studi_id)
            .with_for_update()
        ).scalar_one()

        prefix = nim_prefix(tahun, prodi.kode)
        # Semua NIM panjangnya sama (8) dan running di-zero-pad, sehingga MAX()
        # string sama dengan MAX() numerik.
        last_nim = db.scalar(
            select(func.max(CalonMahasiswa.nim)).where(CalonMahasiswa.nim.like(f"{prefix}%"))
        )
        running = int(last_nim[len(prefix):]) + 1 if last_nim else 1

        if running > NIM_MAX_RUNNING:
            raise NimExhaustedError()

        calon.nim = format_nim(tahun, prodi.kode, running)
        db.flush()
        return calon.nim
