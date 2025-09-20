import sys
import pathlib
# ensure repository root is on sys.path so `src` package is importable
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from src.app import app
import json

client = TestClient(app)

cases = [
    "Je cours dans un rêve, je suis poursuivi par une ombre.",
    "Je me vois voler au-dessus d'une ville, je me sens libre.",
    "Je perds mes dents et je panique.",
]

for t in cases:
    r = client.post('/explain', json={'text': t, 'lang': 'fr'})
    print('---')
    print('TEXT:', t)
    if r.status_code != 200:
        print('ERROR:', r.status_code, r.text)
        continue
    j = r.json()
    print('NARRATIVE:', j.get('narrative'))
    print('KEYWORDS:', ', '.join(j.get('keywords', [])))
    print('SENTIMENT:', j.get('sentiment'))
    print('ESTIMATED TOKENS:', j.get('estimated_tokens'))
    print('\n')
