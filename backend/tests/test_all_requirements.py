import pytest
from fastapi.testclient import TestClient
import uuid
import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from server import app, db, ensure_user, OWNER_EMAIL, OWNER_PASSWORD, OWNER_NAME, SEED_CUSTOMER_EMAIL, SEED_CUSTOMER_PASSWORD, SEED_CUSTOMER_NAME

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Use TestClient with context manager to trigger startup events
    with TestClient(app) as client:
        yield client

def get_auth_token(client):
    response = client.post("/api/auth/login", json={"email": "taromaya@gmail.com", "password": "123456789"})
    return response.json()["token"]

def get_owner_token(client):
    response = client.post("/api/auth/login", json={"email": "riaahuja2000@gmail.com", "password": "rioelixir"})
    return response.json()["token"]

@pytest.fixture
def customer_headers(setup_db):
    token = get_auth_token(setup_db)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def owner_headers(setup_db):
    token = get_owner_token(setup_db)
    return {"Authorization": f"Bearer {token}"}

def test_login(setup_db):
    response = setup_db.post("/api/auth/login", json={"email": "taromaya@gmail.com", "password": "123456789"})
    assert response.status_code == 200
    assert "token" in response.json()

def test_consult_marriage_knowledge(setup_db, customer_headers):
    response = setup_db.post("/api/oracle/consult", json={"question": "meri shaadi kab hogi?", "lang": "en"}, headers=customer_headers)
    assert response.status_code == 200
    d = response.json()
    assert "answer" in d
    assert "7th Partners, contracts" not in d["answer"]
    assert "marriage" in [t.lower() for t in d.get("topics", [])] or "relationships" in [t.lower() for t in d.get("topics", [])]

def test_consult_daily_reading(setup_db, customer_headers):
    response = setup_db.post("/api/oracle/consult", json={"question": "aaj ka mera din kaisa jaega?", "lang": "hi"}, headers=customer_headers)
    assert response.status_code == 200
    d = response.json()
    assert "answer" in d
    assert "Personal Year, Personal Month" not in d["answer"]
    assert d["primary"] == "daily"

def test_consult_career_opportunity(setup_db, customer_headers):
    response = setup_db.post("/api/oracle/consult", json={"question": "career me next opportunity kab milegi?", "lang": "hi"}, headers=customer_headers)
    assert response.status_code == 200
    d = response.json()
    assert "answer" in d
    assert "career" in [t.lower() for t in d.get("topics", [])]

def test_consult_finance_improvement(setup_db, customer_headers):
    response = setup_db.post("/api/oracle/consult", json={"question": "meri financial situation kaise improve hogi?", "lang": "en"}, headers=customer_headers)
    assert response.status_code == 200
    d = response.json()
    assert "answer" in d
    assert "money" in [t.lower() for t in d.get("topics", [])]

def test_consult_unknown_safe_fallback(setup_db, customer_headers):
    response = setup_db.post("/api/oracle/consult", json={"question": "what is the speed of light in vacuum according to occult physics?", "lang": "en"}, headers=customer_headers)
    assert response.status_code == 200
    d = response.json()
    assert "answer" in d
    assert isinstance(d["answer"], str)
    assert len(d["answer"]) > 5

def test_owner_upload_knowledge(setup_db, owner_headers):
    data = b'{"Tarot": {"en": ["New esoteric meaning"]}}'
    files = {"file": ("test.json", data, "application/json")}
    response = setup_db.post("/api/owner/knowledge/upload", files=files, headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["ingested"] >= 1

def test_owner_upload_logo(setup_db, owner_headers):
    png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
           b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7v\x9d\xf2\x00\x00\x00\x00IEND\xaeB`\x82")
    files = {"file": ("logo.png", png, "image/png")}
    response = setup_db.post("/api/owner/upload", data={"kind": "logo"}, files=files, headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["ok"] is True
