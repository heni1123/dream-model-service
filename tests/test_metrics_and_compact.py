from fastapi.testclient import TestClient
from src.app import app


def test_metrics_and_compact_endpoints():
    client = TestClient(app)
    # call compact explain
    r = client.post('/explain/compact', json={'text': 'Je cours dans un rêve', 'lang': 'fr'})
    assert r.status_code == 200
    j = r.json()
    assert 'narrative' in j
    assert 'estimated_tokens' in j

    # metrics
    m = client.get('/metrics')
    assert m.status_code == 200
    assert 'explain_requests_total' in m.text
