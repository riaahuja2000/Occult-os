"""VELORA backend regression tests (pytest)"""
import io
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://mystique-voice-pro.preview.emergentagent.com").rstrip("/")
API = BASE_URL + "/api"

OWNER_EMAIL = "riaahuja2000@gmail.com"
OWNER_PW = "rioelixir"
CUSTOMER_EMAIL = "taromaya@gmail.com"
CUSTOMER_PW = "123456789"


@pytest.fixture(scope="session")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="session")
def owner_token(s):
    r = s.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PW})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["user"]["role"] == "owner"
    assert d["user"]["is_owner"] is True
    return d["token"]


@pytest.fixture(scope="session")
def customer_token(s):
    r = s.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PW})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["user"]["role"] == "customer"
    return d["token"]


def auth(t):
    return {"Authorization": f"Bearer {t}"}


# ---------------- Auth
class TestAuth:
    def test_health(self, s):
        r = s.get(f"{API}/")
        assert r.status_code == 200
        assert "VELORA" in r.json().get("message", "")

    def test_login_bad_password(self, s):
        r = s.post(f"{API}/auth/login", json={"email": CUSTOMER_EMAIL, "password": "wrongwrong"})
        assert r.status_code == 401

    def test_owner_email_reserved(self, s):
        r = s.post(f"{API}/auth/register", json={
            "name": "TEST_reserved", "email": OWNER_EMAIL, "password": "somepassword123"
        })
        assert r.status_code == 409

    def test_register_new_customer(self, s):
        email = f"test_{uuid.uuid4().hex[:10]}@example.com"
        r = s.post(f"{API}/auth/register", json={
            "name": "TEST_User", "email": email, "password": "password123"
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["role"] == "customer"
        assert d["user"]["is_owner"] is False
        assert "token" in d
        # duplicate email
        r2 = s.post(f"{API}/auth/register", json={
            "name": "TEST_User2", "email": email, "password": "password123"
        })
        assert r2.status_code == 409

    def test_register_password_too_short(self, s):
        email = f"test_{uuid.uuid4().hex[:10]}@example.com"
        r = s.post(f"{API}/auth/register", json={
            "name": "TEST", "email": email, "password": "short"
        })
        assert r.status_code == 422

    def test_me_requires_auth(self, s):
        assert s.get(f"{API}/auth/me").status_code == 401

    def test_me_customer(self, s, customer_token):
        r = s.get(f"{API}/auth/me", headers=auth(customer_token))
        assert r.status_code == 200
        assert r.json()["email"] == CUSTOMER_EMAIL

    def test_patch_me_language(self, s, customer_token):
        r = s.patch(f"{API}/me", json={"language": "hi"}, headers=auth(customer_token))
        assert r.status_code == 200
        assert r.json()["language"] == "hi"
        # revert
        s.patch(f"{API}/me", json={"language": "en"}, headers=auth(customer_token))

    def test_forgot_password_generic(self, s):
        r = s.post(f"{API}/auth/forgot-password", json={"email": "nobody_xyz@example.com"})
        assert r.status_code == 200
        assert r.json().get("ok") is True
        r2 = s.post(f"{API}/auth/forgot-password", json={"email": CUSTOMER_EMAIL})
        assert r2.status_code == 200
        assert r2.json().get("ok") is True


# ---------------- Oracle
class TestOracle:
    def test_consult_and_persist(self, s, customer_token):
        r = s.post(f"{API}/oracle/consult",
                   json={"question": "What guidance can you share about love and clarity?", "lang": "en"},
                   headers=auth(customer_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["answer"] and isinstance(d["answer"], str)
        assert isinstance(d["topics"], list) and len(d["topics"]) > 0
        assert "_id" not in d
        # Verify persistence
        r2 = s.get(f"{API}/readings", headers=auth(customer_token))
        assert r2.status_code == 200
        ids = [x["id"] for x in r2.json()]
        assert d["id"] in ids

    def test_consult_empty_question(self, s, customer_token):
        r = s.post(f"{API}/oracle/consult", json={"question": "   ", "lang": "en"},
                   headers=auth(customer_token))
        assert r.status_code == 400

    def test_readings_isolated_per_user(self, s, customer_token, owner_token):
        rc = s.get(f"{API}/readings", headers=auth(customer_token)).json()
        ro = s.get(f"{API}/readings", headers=auth(owner_token)).json()
        cust_ids = {r["id"] for r in rc}
        own_ids = {r["id"] for r in ro}
        assert cust_ids.isdisjoint(own_ids) or (not cust_ids and not own_ids)

    def test_speak_and_serve_mp3(self, s, customer_token):
        r = s.post(f"{API}/oracle/speak",
                   json={"text": "The stars whisper courage tonight.", "lang": "en"},
                   headers=auth(customer_token))
        assert r.status_code == 200, r.text
        url = r.json()["url"]
        assert url.startswith("/api/tts/") and url.endswith(".mp3")
        r2 = requests.get(BASE_URL + url)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("audio/mpeg")
        assert len(r2.content) > 1000

    def test_tts_missing_key(self, s):
        r = requests.get(f"{API}/tts/deadbeef.mp3")
        assert r.status_code == 404


# ---------------- Settings / Branding
class TestSettings:
    def test_public_settings(self, s):
        r = s.get(f"{API}/settings")
        assert r.status_code == 200
        d = r.json()
        for k in ("app_name", "tagline", "subtitle", "voice", "speed"):
            assert k in d

    def test_customer_cannot_put_settings(self, s, customer_token):
        r = s.put(f"{API}/owner/settings", json={"app_name": "HACK"},
                  headers=auth(customer_token))
        assert r.status_code == 403

    def test_owner_updates_settings(self, s, owner_token):
        payload = {"app_name": "VELORA", "tagline": "Ask · Receive · Apply · Move",
                   "subtitle": "Occult sciences. Real life. Real results.",
                   "voice": "shimmer", "speed": 0.95}
        r = s.put(f"{API}/owner/settings", json=payload, headers=auth(owner_token))
        assert r.status_code == 200
        d = r.json()
        assert d["voice"] == "shimmer"
        assert abs(d["speed"] - 0.95) < 0.01

    def test_owner_upload_rejects_bad_type(self, s, owner_token):
        files = {"file": ("test.txt", b"hello", "text/plain")}
        data = {"kind": "logo"}
        r = requests.post(f"{API}/owner/upload", files=files, data=data,
                          headers={"Authorization": f"Bearer {owner_token}"})
        assert r.status_code == 400

    def test_customer_upload_forbidden(self, s, customer_token):
        # Minimal valid PNG bytes
        png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
               b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7v\x9d\xf2\x00\x00\x00\x00IEND\xaeB`\x82")
        files = {"file": ("t.png", png, "image/png")}
        r = requests.post(f"{API}/owner/upload", files=files, data={"kind": "logo"},
                          headers={"Authorization": f"Bearer {customer_token}"})
        assert r.status_code == 403


# ---------------- Owner console + RBAC + member mgmt
class TestOwnerConsole:
    def test_customer_forbidden_overview(self, s, customer_token):
        r = s.get(f"{API}/owner/overview", headers=auth(customer_token))
        assert r.status_code == 403

    def test_owner_overview_shape(self, s, owner_token):
        r = s.get(f"{API}/owner/overview", headers=auth(owner_token))
        assert r.status_code == 200
        d = r.json()
        for k in ("total_sessions", "registered_users", "today", "topics_covered",
                  "most_asked", "last7", "members", "reset_requests"):
            assert k in d
        assert isinstance(d["last7"], list) and len(d["last7"]) == 7
        assert isinstance(d["members"], list) and len(d["members"]) >= 2

    def test_activate_deactivate_and_reset_flow(self, s, owner_token):
        # Create a fresh customer
        email = f"test_{uuid.uuid4().hex[:10]}@example.com"
        pw = "password123"
        reg = s.post(f"{API}/auth/register", json={"name": "TEST_M", "email": email, "password": pw})
        assert reg.status_code == 200
        old_token = reg.json()["token"]
        uid = reg.json()["user"]["id"]

        # /me works
        assert s.get(f"{API}/auth/me", headers=auth(old_token)).status_code == 200

        # Deactivate
        r = s.post(f"{API}/owner/customers/{uid}/active", json={"active": False},
                   headers=auth(owner_token))
        assert r.status_code == 200

        # Old token now invalid (token_version bumped)
        r2 = s.get(f"{API}/auth/me", headers=auth(old_token))
        assert r2.status_code in (401, 403)

        # Login with credentials should also fail while deactivated
        rlogin = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
        assert rlogin.status_code == 403

        # Reactivate
        r3 = s.post(f"{API}/owner/customers/{uid}/active", json={"active": True},
                    headers=auth(owner_token))
        assert r3.status_code == 200
        rlogin2 = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
        assert rlogin2.status_code == 200
        current_token = rlogin2.json()["token"]

        # Reset password
        new_pw = "newpassword456"
        r4 = s.post(f"{API}/owner/customers/{uid}/reset", json={"new_password": new_pw},
                    headers=auth(owner_token))
        assert r4.status_code == 200

        # Old token invalidated
        r5 = s.get(f"{API}/auth/me", headers=auth(current_token))
        assert r5.status_code == 401

        # New password works, old doesn't
        r6 = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
        assert r6.status_code == 401
        r7 = s.post(f"{API}/auth/login", json={"email": email, "password": new_pw})
        assert r7.status_code == 200

    def test_cannot_deactivate_owner(self, s, owner_token):
        me = s.get(f"{API}/auth/me", headers=auth(owner_token)).json()
        r = s.post(f"{API}/owner/customers/{me['id']}/active",
                   json={"active": False}, headers=auth(owner_token))
        assert r.status_code == 400

    def test_consult_marriage_knowledge(self, s, customer_token):
        r = s.post(f"{API}/oracle/consult",
                   json={"question": "meri shaadi kab hogi?", "lang": "en"},
                   headers=auth(customer_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "answer" in d
        # the new logic should return a safe answer from built-in oracle or natural language, not raw document chunks
        assert "7th Partners, contracts" not in d["answer"]
        assert "marriage" in [t.lower() for t in d.get("topics", [])] or "relationships" in [t.lower() for t in d.get("topics", [])]

    def test_consult_daily_reading(self, s, customer_token):
        r = s.post(f"{API}/oracle/consult",
                   json={"question": "aaj ka mera din kaisa jaega?", "lang": "hi"},
                   headers=auth(customer_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "answer" in d
        assert "Personal Year, Personal Month" not in d["answer"]
        assert d["primary"] == "daily"

    def test_consult_career_opportunity(self, s, customer_token):
        r = s.post(f"{API}/oracle/consult",
                   json={"question": "career me next opportunity kab milegi?", "lang": "hi"},
                   headers=auth(customer_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "answer" in d
        assert "career" in [t.lower() for t in d.get("topics", [])]

    def test_consult_finance_improvement(self, s, customer_token):
        r = s.post(f"{API}/oracle/consult",
                   json={"question": "meri financial situation kaise improve hogi?", "lang": "en"},
                   headers=auth(customer_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "answer" in d
        assert "money" in [t.lower() for t in d.get("topics", [])]

    def test_consult_unknown_safe_fallback(self, s, customer_token):
        r = s.post(f"{API}/oracle/consult",
                   json={"question": "what is the speed of light in vacuum according to occult physics?", "lang": "en"},
                   headers=auth(customer_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "answer" in d
        assert isinstance(d["answer"], str)
        assert len(d["answer"]) > 5
