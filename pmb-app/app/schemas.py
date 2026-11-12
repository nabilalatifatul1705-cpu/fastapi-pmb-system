import re
from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import CalonMahasiswa

# Format ternormalisasi: 08 + [1-9] + 7-10 digit  => total 10-13 digit
PHONE_RE = re.compile(r"08[1-9][0-9]{7,10}")


class JalurMasukEnum(str, Enum):
    SNBP = "SNBP"
    SNBT = "SNBT"
    MANDIRI = "MANDIRI"


class CalonMahasiswaCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nama_lengkap: str = Field(min_length=3, max_length=150)
    email: EmailStr
    phone: str = Field(max_length=25, description="Contoh: 081234567890 / +6281234567890")
    tanggal_lahir: date
    alamat: str = Field(min_length=5, max_length=500)
    program_studi_id: int = Field(gt=0)
    jalur_masuk: JalurMasukEnum

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-().]", "", v)
        if cleaned.startswith("+62"):
            cleaned = "0" + cleaned[3:]
        elif cleaned.startswith("62"):
            cleaned = "0" + cleaned[2:]
        if not PHONE_RE.fullmatch(cleaned):
            raise ValueError(
                "Format nomor telepon Indonesia tidak valid "
                "(contoh: 081234567890 atau +6281234567890)."
            )
        return cleaned

    @field_validator("tanggal_lahir")
    @classmethod
    def validate_birthdate(cls, v: date) -> date:
        if v >= date.today():
            raise ValueError("Tanggal lahir harus di masa lalu.")
        if v.year < 1920:
            raise ValueError("Tanggal lahir tidak masuk akal.")
        return v

    @field_validator("jalur_masuk", mode="before")
    @classmethod
    def upper_jalur(cls, v):
        return v.strip().upper() if isinstance(v, str) else v


def _as_utc(v: datetime | None) -> datetime | None:
    """SQLite tidak menyimpan zona waktu; anggap nilai naive sebagai UTC."""
    if v is not None and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


class ProgramStudiOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kode: str
    nama: str
    fakultas: str


class PendaftarOut(BaseModel):
    id: int
    nama_lengkap: str
    email: str
    phone: str
    tanggal_lahir: date
    alamat: str
    program_studi: ProgramStudiOut
    jalur_masuk: str
    status: str
    nim: str | None
    created_at: datetime
    approved_at: datetime | None

    @field_validator("created_at", "approved_at")
    @classmethod
    def _utc(cls, v):
        return _as_utc(v)

    @classmethod
    def from_model(cls, c: CalonMahasiswa) -> "PendaftarOut":
        return cls(
            id=c.id,
            nama_lengkap=c.nama_lengkap,
            email=c.email,
            phone=c.phone,
            tanggal_lahir=c.tanggal_lahir,
            alamat=c.alamat,
            program_studi=ProgramStudiOut.model_validate(c.program_studi),
            jalur_masuk=c.jalur_masuk.kode,
            status=c.status,
            nim=c.nim,
            created_at=c.created_at,
            approved_at=c.approved_at,
        )


class ApproveOut(BaseModel):
    id: int
    nama_lengkap: str
    status: str
    nim: str
    approved_at: datetime | None
    already_approved: bool
    message: str

    @field_validator("approved_at")
    @classmethod
    def _utc(cls, v):
        return _as_utc(v)


class StatusCount(BaseModel):
    pending: int = 0
    approved: int = 0
    rejected: int = 0


class ProdiCount(BaseModel):
    kode: str
    nama: str
    jumlah: int


class JalurCount(BaseModel):
    kode: str
    jumlah: int


class StatsOut(BaseModel):
    total_pendaftar: int
    per_status: StatusCount
    per_program_studi: list[ProdiCount]
    per_jalur_masuk: list[JalurCount]
