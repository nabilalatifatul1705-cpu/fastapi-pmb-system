from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ApproveOut, CalonMahasiswaCreate, PendaftarOut, StatsOut
from app.services import pmb as service

router = APIRouter(prefix="/api/pmb", tags=["PMB"])


@router.post(
    "/register",
    response_model=PendaftarOut,
    status_code=201,
    summary="Daftar calon mahasiswa",
    responses={
        400: {"description": "Input tidak valid (mis. format telepon salah)"},
        409: {"description": "Email sudah terdaftar"},
    },
)
def register(payload: CalonMahasiswaCreate, db: Session = Depends(get_db)):
    return PendaftarOut.from_model(service.register_calon(db, payload))


@router.get(
    "/stats",
    response_model=StatsOut,
    summary="Dashboard jumlah pendaftar",
)
def stats(db: Session = Depends(get_db)):
    return service.get_stats(db)


@router.get(
    "/status/{id}",
    response_model=PendaftarOut,
    summary="Cek status pendaftaran",
    responses={404: {"description": "Pendaftar tidak ditemukan"}},
)
def status(id: int = Path(gt=0), db: Session = Depends(get_db)):
    return PendaftarOut.from_model(service.get_pendaftar(db, id))


@router.put(
    "/approve/{id}",
    response_model=ApproveOut,
    summary="Admin approve -> generate NIM",
    responses={
        404: {"description": "Pendaftar tidak ditemukan"},
        409: {"description": "Status pendaftar tidak dapat di-approve (rejected)"},
    },
)
def approve(id: int = Path(gt=0), db: Session = Depends(get_db)):
    calon, created = service.approve_pendaftar(db, id)
    return ApproveOut(
        id=calon.id,
        nama_lengkap=calon.nama_lengkap,
        status=calon.status,
        nim=calon.nim,
        approved_at=calon.approved_at,
        already_approved=not created,
        message="Pendaftar berhasil di-approve." if created else "Pendaftar sudah di-approve sebelumnya.",
    )
