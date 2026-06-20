from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_knows_marios_job():
    response = client.post("/chat", json={"message": "What is Mario do?"})
    assert response.status_code == 200
    assert "music producer" in response.json()["reply"].lower()


def test_chat_admits_unknown():
    response = client.post("/chat", json={"message": "What is Mario's favorite color?"})
    assert response.status_code == 200
    assert "don't know" in response.json()["reply"].lower()
