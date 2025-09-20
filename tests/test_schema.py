from jsonschema import validate
from src.schema import JSON_SCHEMA

def test_schema_minimal_valid():
    data = {
      "summary":"…",
      "themes":["peur"],
      "symbols":[{"token":"eau","meaning":"émotions","confidence":0.7}],
      "emotions":[{"label":"anxiété","score":0.6}],
      "advice":["respiration 4-7-8"],
      "safety_flags":{"self_harm":False,"medical":False},
      "language":"fr",
      "confidence":0.5
    }
    validate(data, JSON_SCHEMA)
