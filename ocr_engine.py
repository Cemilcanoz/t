"""Windows 10/11 gömülü OCR motoru (winocr üzerinden).

Not: Windows OCR dilleri alfabe bazlı çalışır — Latin alfabesi kullanan diller
(tr, en, de, fr, es, it…) birbirinin metnini büyük ölçüde okuyabilir. Bu yüzden
istenen dil kurulu değilse aynı alfabeden kurulu bir dile otomatik düşeriz.
"""
import winocr
from PIL import Image, ImageOps
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
LANGUAGE_ALIASES = {"zh-CN": "zh-Hans", "zh-TW": "zh-Hant"}


def _is_supported(tag: str) -> bool:
    try:
        return bool(OcrEngine.is_language_supported(Language(tag)))
    except Exception:
        return False


def available_languages() -> list:
    """Bu bilgisayarda kurulu OCR dilleri."""
    try:
        return [item.language_tag for item in OcrEngine.available_recognizer_languages]
    except Exception:
        return [t for t in _ALL_LANGS if _is_supported(t)]


def resolve_language(lang: str):
    """İstenen dili, kurulu değilse aynı alfabeden kurulu bir dile çevirir."""
    lang = LANGUAGE_ALIASES.get(lang, lang).replace("_", "-")
    if _is_supported(lang):
        resolved = lang
    elif lang in _cache and _is_supported(_cache[lang]):
        return _cache[lang]
    else:
        # Sadece AYNI alfabe grubundan kurulu bir dile düşülebilir.
        # Farklı alfabeye düşmek (ör. Japonca metni Türkçe motoruyla okumak)
        # anlamsız çıktı üretir, o yüzden None döner ve kullanıcı uyarılır.
        resolved = None
        base = lang.split("-")[0]
        for group in SCRIPT_GROUPS:
            if lang in group or base in group:
                candidates = group + [tag for tag in available_languages()
                                      if tag in group or tag.split("-")[0] in group]
                resolved = next((t for t in candidates if _is_supported(t)), None)
                break

    # Başarısız seçimleri önbelleğe alma: Windows'a yeni dil eklenince
    # uygulamayı kapatıp açmak zorunda kalınmasın.
    if resolved is not None:
        _cache[lang] = resolved
    else:
        _cache.pop(lang, None)
    return resolved


def _prepare_image(pil_image):
    if pil_image.width < 1 or pil_image.height < 1:
        raise RuntimeError("OCR için seçilen görüntü boş.")
    image = pil_image.convert("RGB")
    limit = OcrEngine.max_image_dimension
    if max(image.size) > limit:
        scale = limit / max(image.size)
        image = image.resize((max(1, round(image.width * scale)),
                              max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
    return image


def _read_lines(result):
    lines = []
    for line in result.get("lines") or []:
        text = (line.get("text") or "").strip()
        if text:
            lines.append(text)
    # Bazı winocr sürümleri yalnızca birleştirilmiş text döndürebilir.
    if not lines and (result.get("text") or "").strip():
        lines = [result["text"].strip()]
    return lines


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
        image = _prepare_image(pil_image)
        result = winocr.recognize_pil_sync(image, actual)
        lines = _read_lines(result)
        if not lines:
            # Küçük veya düşük kontrastlı tarayıcı yazısı için bir ikinci
            # okuma; çeviri ağına görüntü gönderilmez.
            retry = ImageOps.autocontrast(ImageOps.grayscale(image))
            if max(image.size) * 2 <= OcrEngine.max_image_dimension and image.width * image.height <= 4_000_000:
                retry = retry.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
            lines = _read_lines(winocr.recognize_pil_sync(retry, actual))
    except Exception as e:
        raise RuntimeError("Windows metin tanıma işlemi başarısız oldu. Alanı yeniden seçip deneyin; sorun sürerse OCR dil paketini kontrol edin.") from e

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
