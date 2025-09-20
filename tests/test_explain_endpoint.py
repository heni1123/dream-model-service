from fastapi.testclient import TestClient
from src.app import app


def test_explain_endpoint_minimal():
    client = TestClient(app)
    r = client.post('/explain', json={'text': 'Je cours dans un rêve, je suis poursuivi par une ombre.', 'lang': 'fr'})
    assert r.status_code == 200
    j = r.json()
    assert 'narrative' in j
    assert 'keywords' in j
    assert 'sentiment' in j