import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import get_db, make_engine
from app.exceptions import NimExhaustedError
from app.main import app
from app.models import Base, CalonMahasiswa
from app.seed import seed_reference_data
from app.services.nim import format_nim, generate_nim
from app.services.pmb import approve_pendaftar

YY = f"{datetime.now(timezone.utc).year % 100:02d}"  # 2 digit tahun berjalan


# ----------------------------------------------------------------- fixtures
@pytest.fixture()
def session_factory(tmp_path):
    """Database SQLite berbasis file sementara (aman untuk uji multi-thread)."""
    engine = make_engine(f"sqlite:///{tmp_path / 'test_pmb.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        seed_reference_data(session)
    yield factory
    engine.dispose()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def payload(**overrides):
    data = {
        "nama_lengkap": "Nabila Latifatul Hamdah",
        "email": "nabila.latifatul@example.com",
        "phone": "081234567890",
        "tanggal_lahir": "2006-05-17",
        "alamat": "Jl. Merdeka No. 10, Bogor",
        "program_studi_id": 1,
        "jalur_masuk": "SNBP",
    }
    data.update(overrides)
    return data


def register(client, **overrides):
    resp = client.post("/api/pmb/register", json=payload(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_calon(session, email, nama="Test User", prodi_id=1, nim=None):
    calon = CalonMahasiswa(
        nama_lengkap=nama,
        email=email,
        phone="081234567890",
        tanggal_lahir=date(2006, 1, 1),
        alamat="Jl. Test No. 1",
        program_studi_id=prodi_id,
        jalur_masuk_id=1,
        nim=nim,
    )
    session.add(calon)
    session.commit()
    return calon


# ------------------------------------------------------------ register tests
def test_register_success(client):
    resp = client.post("/api/pmb/register", json=payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["nama_lengkap"] == "Nabila Latifatul Hamdah"
    assert body["status"] == "pending"
    assert body["nim"] is None
    assert body["email"] == "nabila.latifatul@example.com"
    assert body["program_studi"]["kode"] == "360"
    assert body["jalur_masuk"] == "SNBP"


def test_register_normalizes_phone_and_jalur(client):
    body = register(client, phone="+62 812-3456-7890", jalur_masuk="mandiri")
    assert body["phone"] == "081234567890"
    assert body["jalur_masuk"] == "MANDIRI"


def test_register_duplicate_email(client):
    register(client)
    resp = client.post(
        "/api/pmb/register", json=payload(email="NABILA.Latifatul@Example.com")
    )
    assert resp.status_code == 409


@pytest.mark.parametrize("bad_phone", ["12345", "0212345678", "08abc12345678", "+1234567890123"])
def test_invalid_phone_format(client, bad_phone):
    resp = client.post("/api/pmb/register", json=payload(phone=bad_phone))
    assert resp.status_code == 400
    assert any(e["field"] == "phone" for e in resp.json()["errors"])


def test_register_invalid_program_studi(client):
    resp = client.post("/api/pmb/register", json=payload(program_studi_id=999))
    assert resp.status_code == 400


def test_register_invalid_email_and_future_birthdate(client):
    assert client.post("/api/pmb/register", json=payload(email="bukan-email")).status_code == 400
    assert client.post(
        "/api/pmb/register", json=payload(tanggal_lahir="2999-01-01")
    ).status_code == 400


# --------------------------------------------------------------- status tests
def test_get_status(client):
    created = register(client)
    resp = client.get(f"/api/pmb/status/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_get_status_not_found(client):
    assert client.get("/api/pmb/status/9999").status_code == 404


# -------------------------------------------------------------- approve tests
def test_approve_generate_nim(client):
    a = register(client, email="nabila.latifatul@example.com")
    b = register(client, email="b@example.com", nama_lengkap="Budi Santoso")
    c = register(client, email="c@example.com", nama_lengkap="Citra Dewi", program_studi_id=2)

    ra = client.put(f"/api/pmb/approve/{a['id']}")
    assert ra.status_code == 200
    assert ra.json()["status"] == "approved"
    assert ra.json()["nim"] == f"{YY}360001"
    assert re.fullmatch(r"\d{8}", ra.json()["nim"])

    # sequential pada prodi yang sama
    assert client.put(f"/api/pmb/approve/{b['id']}").json()["nim"] == f"{YY}360002"
    # prodi lain memiliki counter sendiri
    assert client.put(f"/api/pmb/approve/{c['id']}").json()["nim"] == f"{YY}361001"


def test_approve_idempotent(client):
    a = register(client, email="nabila.latifatul@example.com")
    b = register(client, email="b@example.com", nama_lengkap="Budi Santoso")

    first = client.put(f"/api/pmb/approve/{a['id']}").json()
    second = client.put(f"/api/pmb/approve/{a['id']}").json()

    assert first["nim"] == second["nim"] == f"{YY}360001"
    assert first["already_approved"] is False
    assert second["already_approved"] is True
    assert first["approved_at"] == second["approved_at"]

    # tidak ada nomor urut yang "terbuang" oleh approve kedua
    assert client.put(f"/api/pmb/approve/{b['id']}").json()["nim"] == f"{YY}360002"


def test_approve_invalid_data(client, session_factory):
    assert client.put("/api/pmb/approve/9999").status_code == 404
    assert client.put("/api/pmb/approve/0").status_code == 400
    assert client.put("/api/pmb/approve/abc").status_code == 400

    created = register(client)
    with session_factory() as s:
        s.get(CalonMahasiswa, created["id"]).status = "rejected"
        s.commit()
    assert client.put(f"/api/pmb/approve/{created['id']}").status_code == 409


# ------------------------------------------------------------------ stats test
def test_stats(client):
    a = register(client, email="a@example.com")
    register(client, email="b@example.com", program_studi_id=2, jalur_masuk="SNBT")
    client.put(f"/api/pmb/approve/{a['id']}")

    body = client.get("/api/pmb/stats").json()
    assert body["total_pendaftar"] == 2
    assert body["per_status"] == {"pending": 1, "approved": 1, "rejected": 0}
    per_prodi = {p["kode"]: p["jumlah"] for p in body["per_program_studi"]}
    assert per_prodi["360"] == 1 and per_prodi["361"] == 1 and per_prodi["362"] == 0
    per_jalur = {j["kode"]: j["jumlah"] for j in body["per_jalur_masuk"]}
    assert per_jalur == {"MANDIRI": 0, "SNBP": 1, "SNBT": 1}


# ------------------------------------------------------- NIM generator (unit)
def test_format_nim():
    assert format_nim(2024, "360", 6) == "24360006"
    assert format_nim(2025, "361", 123) == "25361123"


def test_generate_nim_contoh_nabila_24360006(session_factory):
    """Nabila adalah pendaftar ke-6 Teknik Informatika angkatan 2024 -> 24360006."""
    with session_factory() as s:
        for i in range(1, 6):  # 5 mahasiswa sebelumnya: 24360001..24360005
            make_calon(s, f"mhs{i}@example.com", nim=f"2436000{i}")
        nabila = make_calon(
            s, "nabila.latifatul@example.com", nama="Nabila Latifatul Hamdah"
        )
        assert generate_nim(s, nabila, tahun=2024) == "24360006"


def test_generate_nim_is_idempotent(session_factory):
    with session_factory() as s:
        calon = make_calon(s, "x@example.com", nama="Nabila Latifatul Hamdah")
        nim1 = generate_nim(s, calon, tahun=2024)
        s.commit()
        nim2 = generate_nim(s, calon, tahun=2024)
        assert nim1 == nim2 == "24360001"


def test_generate_nim_exhausted(session_factory):
    with session_factory() as s:
        make_calon(s, "full@example.com", nim="24360999")
        other = make_calon(s, "other@example.com")
        with pytest.raises(NimExhaustedError):
            generate_nim(s, other, tahun=2024)


def test_generate_nim_thread_safe(session_factory):
    """20 approval paralel -> 20 NIM unik dan berurutan 001..020 tanpa duplikat."""
    with session_factory() as s:
        ids = [make_calon(s, f"user{i}@example.com").id for i in range(20)]

    def worker(pendaftar_id):
        with session_factory() as session:
            calon, _ = approve_pendaftar(session, pendaftar_id)
            return calon.nim

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(worker, ids))

    assert len(set(results)) == 20
    assert sorted(int(n[5:]) for n in results) == list(range(1, 21))


# ------------------------------------------------------ database constraints
@pytest.mark.parametrize(
    "field,value",
    [("phone", "12345"), ("phone", "0212345678901"), ("status", "bogus"), ("program_studi_id", 999)],
)
def test_db_constraints_reject_invalid_rows(session_factory, field, value):
    with session_factory() as s:
        calon = CalonMahasiswa(
            nama_lengkap="Nabila Latifatul Hamdah",
            email="c@example.com",
            phone="081234567890",
            tanggal_lahir=date(2006, 1, 1),
            alamat="Jl. Test No. 1",
            program_studi_id=1,
            jalur_masuk_id=1,
        )
        setattr(calon, field, value)
        s.add(calon)
        with pytest.raises(IntegrityError):
            s.commit()
