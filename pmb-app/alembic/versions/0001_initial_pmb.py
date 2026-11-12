"""initial pmb schema: program_studi, jalur_masuk, calon_mahasiswa

Revision ID: 0001_initial_pmb
Revises:
Create Date: 2026-11-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_pmb"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- program_studi ----
    op.create_table(
        "program_studi",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kode", sa.String(3), nullable=False),
        sa.Column("nama", sa.String(100), nullable=False),
        sa.Column("fakultas", sa.String(100), nullable=False),
        sa.UniqueConstraint("kode", name="uq_program_studi_kode"),
        sa.CheckConstraint("LENGTH(kode) = 3", name="ck_program_studi_kode_len"),
    )

    # ---- jalur_masuk ----
    op.create_table(
        "jalur_masuk",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kode", sa.String(10), nullable=False),
        sa.Column("nama", sa.String(100), nullable=False),
        sa.UniqueConstraint("kode", name="uq_jalur_masuk_kode"),
    )

    # ---- calon_mahasiswa ----
    op.create_table(
        "calon_mahasiswa",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nama_lengkap", sa.String(150), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("phone", sa.String(15), nullable=False),
        sa.Column("tanggal_lahir", sa.Date(), nullable=False),
        sa.Column("alamat", sa.String(500), nullable=False),
        sa.Column("program_studi_id", sa.Integer(), nullable=False),
        sa.Column("jalur_masuk_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("nim", sa.String(8), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["program_studi_id"], ["program_studi.id"],
            name="fk_calon_program_studi", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["jalur_masuk_id"], ["jalur_masuk.id"],
            name="fk_calon_jalur_masuk", ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("email", name="uq_calon_mahasiswa_email"),
        sa.UniqueConstraint("nim", name="uq_calon_mahasiswa_nim"),
        sa.CheckConstraint(
            "SUBSTR(phone, 1, 2) = '08' AND LENGTH(phone) BETWEEN 10 AND 13",
            name="ck_calon_mahasiswa_phone_format",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_calon_mahasiswa_status",
        ),
    )
    op.create_index("ix_calon_mahasiswa_status", "calon_mahasiswa", ["status"])
    op.create_index("ix_calon_mahasiswa_program_studi_id", "calon_mahasiswa", ["program_studi_id"])
    op.create_index("ix_calon_mahasiswa_jalur_masuk_id", "calon_mahasiswa", ["jalur_masuk_id"])

    # ---- seed data referensi ----
    prodi_t = sa.table(
        "program_studi",
        sa.column("id", sa.Integer), sa.column("kode", sa.String),
        sa.column("nama", sa.String), sa.column("fakultas", sa.String),
    )
    op.bulk_insert(prodi_t, [
        {"id": 1, "kode": "360", "nama": "Teknik Informatika", "fakultas": "Fakultas Teknik"},
        {"id": 2, "kode": "361", "nama": "Sistem Informasi", "fakultas": "Fakultas Teknik"},
        {"id": 3, "kode": "362", "nama": "Teknik Elektro", "fakultas": "Fakultas Teknik"},
        {"id": 4, "kode": "363", "nama": "Manajemen", "fakultas": "Fakultas Ekonomi dan Bisnis"},
    ])
    jalur_t = sa.table(
        "jalur_masuk",
        sa.column("id", sa.Integer), sa.column("kode", sa.String), sa.column("nama", sa.String),
    )
    op.bulk_insert(jalur_t, [
        {"id": 1, "kode": "SNBP", "nama": "Seleksi Nasional Berdasarkan Prestasi"},
        {"id": 2, "kode": "SNBT", "nama": "Seleksi Nasional Berdasarkan Tes"},
        {"id": 3, "kode": "MANDIRI", "nama": "Seleksi Mandiri"},
    ])


def downgrade() -> None:
    """Rollback: hapus dalam urutan terbalik (tabel anak dulu)."""
    op.drop_index("ix_calon_mahasiswa_jalur_masuk_id", table_name="calon_mahasiswa")
    op.drop_index("ix_calon_mahasiswa_program_studi_id", table_name="calon_mahasiswa")
    op.drop_index("ix_calon_mahasiswa_status", table_name="calon_mahasiswa")
    op.drop_table("calon_mahasiswa")
    op.drop_table("jalur_masuk")
    op.drop_table("program_studi")
