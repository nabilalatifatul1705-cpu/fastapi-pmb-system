from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import (
    DuplicateEmailError,
    InvalidStatusError,
    PendaftarNotFoundError,
    ProgramStudiNotFoundError,
    ReferenceDataError,
)
from app.models import (
    CalonMahasiswa,
    JalurMasuk,
    ProgramStudi,
    StatusPendaftaran,
    utcnow,
)
from app.schemas import (
    CalonMahasiswaCreate,
    JalurCount,
    ProdiCount,
    StatsOut,
    StatusCount,
)
from app.services.nim import generate_nim, nim_lock

MAX_APPROVE_RETRY = 3


def register_calon(db: Session, data: CalonMahasiswaCreate) -> CalonMahasiswa:
    if db.get(ProgramStudi, data.program_studi_id) is None:
        raise ProgramStudiNotFoundError()

    jalur = db.scalar(select(JalurMasuk).where(JalurMasuk.kode == data.jalur_masuk.value))
    if jalur is None:
        raise ReferenceDataError()

    if db.scalar(select(CalonMahasiswa.id).where(CalonMahasiswa.email == data.email)):
        raise DuplicateEmailError()

    calon = CalonMahasiswa(
        nama_lengkap=data.nama_lengkap,
        email=data.email,
        phone=data.phone,
        tanggal_lahir=data.tanggal_lahir,
        alamat=data.alamat,
        program_studi_id=data.program_studi_id,
        jalur_masuk_id=jalur.id,
        status=StatusPendaftaran.PENDING.value,
    )
    db.add(calon)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Dua request bersamaan dengan email sama lolos pengecekan di atas,
        # tetapi UNIQUE constraint database tetap menolak yang kedua.
        if "email" in str(exc.orig).lower():
            raise DuplicateEmailError() from exc
        raise
    db.refresh(calon)
    return calon


def get_pendaftar(db: Session, pendaftar_id: int) -> CalonMahasiswa:
    calon = db.get(CalonMahasiswa, pendaftar_id)
    if calon is None:
        raise PendaftarNotFoundError()
    return calon


def approve_pendaftar(db: Session, pendaftar_id: int) -> tuple[CalonMahasiswa, bool]:
    """
    Approve pendaftar & generate NIM.

    Return (calon, created):
      created=False -> sudah pernah di-approve; NIM lama dikembalikan (idempotent).
    """
    with nim_lock:  # ditahan sampai commit agar thread lain melihat NIM terbaru
        for attempt in range(MAX_APPROVE_RETRY):
            calon = db.get(
                CalonMahasiswa, pendaftar_id, with_for_update=True, populate_existing=True
            )
            if calon is None:
                raise PendaftarNotFoundError()

            if calon.status == StatusPendaftaran.APPROVED.value and calon.nim:
                return calon, False

            if calon.status == StatusPendaftaran.REJECTED.value:
                raise InvalidStatusError("Pendaftar berstatus 'rejected' tidak dapat di-approve.")

            try:
                generate_nim(db, calon)
                calon.status = StatusPendaftaran.APPROVED.value
                calon.approved_at = utcnow()
                db.commit()
                return calon, True
            except IntegrityError:
                db.rollback()  # tabrakan NIM (sangat jarang) -> coba lagi
                if attempt == MAX_APPROVE_RETRY - 1:
                    raise
    raise RuntimeError("unreachable")  # pragma: no cover


def get_stats(db: Session) -> StatsOut:
    status_rows = db.execute(
        select(CalonMahasiswa.status, func.count()).group_by(CalonMahasiswa.status)
    ).all()
    per_status = StatusCount(**{status: n for status, n in status_rows})

    prodi_rows = db.execute(
        select(ProgramStudi.kode, ProgramStudi.nama, func.count(CalonMahasiswa.id))
        .outerjoin(CalonMahasiswa, CalonMahasiswa.program_studi_id == ProgramStudi.id)
        .group_by(ProgramStudi.id, ProgramStudi.kode, ProgramStudi.nama)
        .order_by(ProgramStudi.kode)
    ).all()

    jalur_rows = db.execute(
        select(JalurMasuk.kode, func.count(CalonMahasiswa.id))
        .outerjoin(CalonMahasiswa, CalonMahasiswa.jalur_masuk_id == JalurMasuk.id)
        .group_by(JalurMasuk.id, JalurMasuk.kode)
        .order_by(JalurMasuk.kode)
    ).all()

    return StatsOut(
        total_pendaftar=per_status.pending + per_status.approved + per_status.rejected,
        per_status=per_status,
        per_program_studi=[ProdiCount(kode=k, nama=n, jumlah=j) for k, n, j in prodi_rows],
        per_jalur_masuk=[JalurCount(kode=k, jumlah=j) for k, j in jalur_rows],
    )
