from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_record_visit_route_includes_request_id_on_validation_error():
    response = client.post(
        "/api/stats/visit",
        json={"client_id": ""},
        headers={"x-request-id": "req-visit-400"},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_visit"
    assert response.json()["request_id"] == "req-visit-400"