from src import openai_client
from src.service import analyze
import json

class DummyResp:
    class Choice:
        class Message:
            def __init__(self, args):
                class ToolCall:
                    def __init__(self, arguments):
                        self.function = type('f', (), {'arguments': arguments})
                self.tool_calls = [ToolCall(args)]
        def __init__(self, args):
            self.message = DummyResp.Choice.Message(args)
    def __init__(self, args):
        self.choices = [DummyResp.Choice(args)]

class StubChat:
    class Completions:
        def create(self, **kwargs):
            payload = {
                "summary": "Rêve de vol suivi d'une chute. Sentiment de liberté et d'anxiété.",
                "themes": ["vol", "mer", "chute"],
                "symbols": [{"token":"vol","meaning":"liberté","confidence":0.8}],
                "emotions": [{"label":"liberté","score":0.7}],
                "possible_causes": ["stress récent"],
                "advice": ["tenir un journal", "diminuer les stimulants avant le coucher"],
                "lucid_hint": None,
                "keywords": ["vol","mer","chute"],
                "safety_flags": {"self_harm": False, "medical": False},
                "language": "fr",
                "confidence": 0.75
            }
            return DummyResp(json.dumps(payload, ensure_ascii=False))
    def __init__(self):
        self.chat = type('c', (), {'completions': StubChat.Completions()})

openai_client.client = StubChat()
res = analyze('Je volais au-dessus d\'une mer agitée, puis je tombais.', lang='fr', seed=42, use_rag=False)
print(json.dumps(res, ensure_ascii=False, indent=2))
