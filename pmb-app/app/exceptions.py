class PMBError(Exception):
    """Basis error domain PMB; dipetakan ke HTTP response di main.py."""

    status_code = 500
    default_detail = "Terjadi kesalahan pada sistem PMB."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class PendaftarNotFoundError(PMBError):
    status_code = 404
    default_detail = "Pendaftar tidak ditemukan."


class ProgramStudiNotFoundError(PMBError):
    status_code = 400
    default_detail = "program_studi_id tidak valid."


class ReferenceDataError(PMBError):
    status_code = 400
    default_detail = "Data referensi (jalur masuk) tidak ditemukan."


class DuplicateEmailError(PMBError):
    status_code = 409
    default_detail = "Email sudah terdaftar."


class InvalidStatusError(PMBError):
    status_code = 409
    default_detail = "Status pendaftar tidak valid untuk operasi ini."


class NimExhaustedError(PMBError):
    status_code = 500
    default_detail = "Nomor urut NIM untuk prodi dan tahun ini sudah habis."
