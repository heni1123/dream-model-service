import pytest
from src.service import analyze

def test_analyze_raises_without_text():
    with pytest.raises(Exception):
        analyze(text="", lang="fr")
