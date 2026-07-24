"""Windows 10/11 gömülü OCR motoru (winocr üzerinden).

Not: Windows OCR dilleri alfabe bazlı çalışır — Latin alfabesi kullanan diller
(tr, en, de, fr, es, it…) birbirinin metnini büyük ölçüde okuyabilir. Bu yüzden
istenen dil kurulu değilse aynı alfabeden kurulu bir dile otomatik düşeriz.
"""
import winocr
from winrt.windows.globalization import Language
from winrt.windows.media.ocr import OcrEngine

SENTENCE_END = (".", "!", "?", ":", ";", "…")

# Aynı gruptaki diller birbirinin yerine kullanılabilir (ortak alfabe)
SCRIPT_GROUPS = [
    ["en", "tr", "de", "fr", "es", "it", "pt", "nl", "pl", "sv", "da", "fi", "cs"],
    ["ru", "uk", "bg", "sr"],
    ["ja"],
    ["ko"],
    ["zh-Hans", "zh-Hant"],
    ["ar"],
    ["el"],
    ["he"],
]

_ALL_LANGS = [tag for group in SCRIPT_GROUPS for tag in group]
_cache: dict = {}


def _is_supported(tag: str) -> bool:
    try:
        return bool(OcrEngine.is_language_supported(Language(tag)))
    except Exception:
        return False


def available_languages() -> list:
    """Bu bilgisayarda kurulu OCR dilleri."""
    return [t for t in _ALL_LANGS if _is_supported(t)]


def resolve_language(lang: str):
    """İstenen dili, kurulu değilse aynı alfabeden kurulu bir dile çevirir."""
    if lang in _cache:
        return _cache[lang]

    if _is_supported(lang):
        resolved = lang
    else:
        # Sadece AYNI alfabe grubundan kurulu bir dile düşülebilir.
        # Farklı alfabeye düşmek (ör. Japonca metni Türkçe motoruyla okumak)
        # anlamsız çıktı üretir, o yüzden None döner ve kullanıcı uyarılır.
        resolved = None
        for group in SCRIPT_GROUPS:
            if lang in group:
                resolved = next((t for t in group if _is_supported(t)), None)
                break

    _cache[lang] = resolved
    return resolved


def recognize(pil_image, lang: str = "en") -> str:
    """Görüntüdeki metni okur, satırları akıllıca birleştirip döndürür."""
    actual = resolve_language(lang)
    if actual is None:
        installed = available_languages()
        raise RuntimeError(
            f"'{lang}' için OCR dil paketi kurulu değil.\n"
            + (f"Kurulu diller: {', '.join(installed)}\n" if installed else "")
            + "Yeni dil eklemek için: Ayarlar > Zaman ve Dil > Dil ve bölge > "
            "Dil ekle (kurulumda 'Metin tanıma / OCR' kutusunu işaretle)."
        )

    try:
        result = winocr.recognize_pil_sync(pil_image, actual)
    except Exception as e:
        raise RuntimeError(f"OCR başarısız: {e}")

    lines = [(ln.get("text") or "").strip() for ln in (result.get("lines") or [])]
    lines = [t for t in lines if t]

    # Satır sonu cümle bitişiyse yeni satır, değilse boşlukla birleştir
    # (oyun altyazıları gibi satırlara bölünmüş cümleler düzgün çevrilsin diye)
    text = ""
    for t in lines:
        if not text:
            text = t
        elif text.endswith(SENTENCE_END):
            text += "\n" + t
        else:
            text += " " + t
    return text.strip()
