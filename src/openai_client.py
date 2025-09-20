from openai import OpenAI
from .config import OPENAI_API_KEY, USE_STUB_OPENAI, APP_NAME, PROMPT_VERSION

class _StubClient:
    class Responses:
        def create(self, **kwargs):
            # renvoie un objet minimal avec output_text + usage simulée
            class Dummy:
                output_text = (
                    '{"summary":"(stub) Analyse indisponible en local","themes":[],"symbols":[],"emotions":[],'
                    '"advice":[],"safety_flags":{"self_harm":false,"medical":false},"language":"fr","confidence":0.0}'
                )
                usage = type("U", (), {
                    "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                    "prompt_tokens_details": type("D", (), {"cached_tokens": 0})()
                })()
            return Dummy()
    def __init__(self):
        self.responses = _StubClient.Responses()

if USE_STUB_OPENAI:
    client = _StubClient()
else:
    client = OpenAI(api_key=OPENAI_API_KEY)

def make_cache_key(locale: str, mode: str = "base", shard: int = 0) -> str:
    # app|version|locale|mode|sX — courte et stable
    return f"{APP_NAME}|{PROMPT_VERSION}|{locale}|{mode}|s{shard}"
