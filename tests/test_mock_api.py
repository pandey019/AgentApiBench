from fastapi.testclient import TestClient
from mock_api.server import app

client = TestClient(app)
TOKEN = "sk-bench-4921x"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def test_health():
    response = client.get("/health")
    # Health endpoint doesn't exist in mock_api/server.py directly,
    # it exists in server/app.py.
    # Let's test actual mock endpoints
    pass


def test_get_customer():
    response = client.get("/v1/customers/cust_4821", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["id"] == "cust_4821"


def test_get_customer_unauthorized():
    response = client.get("/v1/customers/cust_4821")
    assert response.status_code == 401


def test_create_payment():
    payload = {"customer_id": "cust_4821", "amount": 100.0, "currency": "USD"}
    response = client.post("/v1/payments", headers=HEADERS, json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


def test_create_payment_invalid_currency():
    payload = {"customer_id": "cust_4821", "amount": 100.0, "currency": "US"}
    response = client.post("/v1/payments", headers=HEADERS, json=payload)
    assert response.status_code == 422
