from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatusPendaftaran(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Base(DeclarativeBase):
    pass


class ProgramStudi(Base):
    __tablename__ = "program_studi"
    __table_args__ = (
        UniqueConstraint("kode", name="uq_program_studi_kode"),
        CheckConstraint("LENGTH(kode) = 3", name="ck_program_studi_kode_len"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kode: Mapped[str] = mapped_column(String(3))
    nama: Mapped[str] = mapped_column(String(100))
    fakultas: Mapped[str] = mapped_column(String(100))

    pendaftar: Mapped[list["CalonMahasiswa"]] = relationship(back_populates="program_studi")


class JalurMasuk(Base):
    __tablename__ = "jalur_masuk"
    __table_args__ = (UniqueConstraint("kode", name="uq_jalur_masuk_kode"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kode: Mapped[str] = mapped_column(String(10))  # SNBP / SNBT / MANDIRI
    nama: Mapped[str] = mapped_column(String(100))

    pendaftar: Mapped[list["CalonMahasiswa"]] = relationship(back_populates="jalur_masuk")


class CalonMahasiswa(Base):
    __tablename__ = "calon_mahasiswa"
    __table_args__ = (
        UniqueConstraint("email", name="uq_calon_mahasiswa_email"),
        UniqueConstraint("nim", name="uq_calon_mahasiswa_nim"),
        # Format telepon Indonesia ternormalisasi: 08xxxxxxxxx (10-13 digit).
        # Validasi regex penuh dilakukan di schema Pydantic (portable lintas DB).
        CheckConstraint(
            "SUBSTR(phone, 1, 2) = '08' AND LENGTH(phone) BETWEEN 10 AND 13",
            name="ck_calon_mahasiswa_phone_format",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_calon_mahasiswa_status",
        ),
        Index("ix_calon_mahasiswa_status", "status"),
        Index("ix_calon_mahasiswa_program_studi_id", "program_studi_id"),
        Index("ix_calon_mahasiswa_jalur_masuk_id", "jalur_masuk_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nama_lengkap: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(254))
    phone: Mapped[str] = mapped_column(String(15))
    tanggal_lahir: Mapped[date] = mapped_column(Date)
    alamat: Mapped[str] = mapped_column(String(500))
    program_studi_id: Mapped[int] = mapped_column(
        ForeignKey("program_studi.id", name="fk_calon_program_studi", ondelete="RESTRICT")
    )
    jalur_masuk_id: Mapped[int] = mapped_column(
        ForeignKey("jalur_masuk.id", name="fk_calon_jalur_masuk", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(
        String(10), default=StatusPendaftaran.PENDING.value, server_default="pending"
    )
    nim: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    program_studi: Mapped[ProgramStudi] = relationship(back_populates="pendaftar")
    jalur_masuk: Mapped[JalurMasuk] = relationship(back_populates="pendaftar")
