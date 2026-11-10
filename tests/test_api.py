import os
from fastapi.testclient import TestClient
from app import main

def setup_module():
    main.DB_PATH = main.BASE_DIR / "data" / "test_neurosales.db"
    main.DB_PATH.parent.mkdir(exist_ok=True)
    if main.DB_PATH.exists():
        main.DB_PATH.unlink()
    main.init_db()
    main.APP_PASSWORD = "test-password-123"
    main.TOKEN_SECRET = "test-secret-for-tests"

client = TestClient(main.app)

def auth():
    token = client.post("/api/login", json={"password":"test-password-123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_login_rejects_wrong_password():
    assert client.post("/api/login", json={"password":"wrong-password"}).status_code == 401

def test_lead_crud_and_ai_reply():
    headers = auth()
    created = client.post("/api/leads", headers=headers, json={
        "name":"Тестовый клиент","phone":"+7 900 000-00-00",
        "product":"Доска тарная","volume":"5 м³","source":"Сайт"
    })
    assert created.status_code == 201
    lead_id = created.json()["id"]
    assert client.get("/api/leads", headers=headers).status_code == 200
    assert client.post("/api/ai/reply", headers=headers,
                       json={"lead_id":lead_id,"tone":"Деловой"}).json()["reply"]
    assert client.patch(f"/api/leads/{lead_id}", headers=headers,
                        json={"status":"В работе"}).json()["status"] == "В работе"
    assert client.delete(f"/api/leads/{lead_id}", headers=headers).json()["deleted"] is True

def test_api_requires_auth():
    assert client.get("/api/leads").status_code == 401
