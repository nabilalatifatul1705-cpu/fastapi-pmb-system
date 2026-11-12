from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions import PMBError
from app.routers import pmb

app = FastAPI(
    title="API PMB - Penerimaan Mahasiswa Baru",
    version="1.0.0",
    description="Pendaftaran calon mahasiswa dengan generator NIM otomatis.",
)


@app.exception_handler(PMBError)
async def pmb_error_handler(_: Request, exc: PMBError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    """Spesifikasi tugas: input tidak valid -> 400 (bukan 422 bawaan FastAPI)."""
    errors = [
        {"field": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=400, content={"detail": "Validasi input gagal.", "errors": errors})


app.include_router(pmb.router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}
