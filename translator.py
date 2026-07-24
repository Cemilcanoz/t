"""Ücretsiz Google Translate (deep-translator ile, API anahtarı gerekmez)."""
from deep_translator import GoogleTranslator

MAX_CHARS = 4500  # Google'ın istek başına ~5000 karakter sınırı var


def translate(text: str, target: str = "tr") -> str:
    text = text.strip()
    if not text:
        return ""
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
    return GoogleTranslator(source="auto", target=target).translate(text) or ""