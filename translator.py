"""Selectable free translation transports with bounded retries and cancellation."""
import re
import time

import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator as _GoogleTranslator
from deep_translator.exceptions import TooManyRequests, RequestError

MAX_CHARS = 4500  # Google'ın istek başına ~5000 karakter sınırı var
RETRY_DELAYS = (1.0, 2.0)
REQUEST_TIMEOUT = (3.0, 8.0)  # bağlantı ve yanıtta hareketsizlik sınırı


class TranslationCancelled(RuntimeError):
    """İstek kullanıcının yeni işlemi nedeniyle iptal edildi."""


def _check_cancelled(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise TranslationCancelled("Çeviri iptal edildi.")


class _InvalidResponse(Exception):
    """Servis çeviri yerine boş yanıt veya engelleme sayfası döndürdü."""


class GoogleTranslator(_GoogleTranslator):
    """deep-translator dil doğrulaması; süre sınırlı Google aktarımı.

    Mobil HTML servisindeki geçici engelde aynı sağlayıcının JSON servisini
    dener. Her çağrı yalnızca tek HTTP isteği yapar; tekrar sayısı aşağıdadır.
    Bu ücretsiz uçların kullanılabilirliği Google tarafından garanti edilmez.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._use_json = False

    def translate(self, text: str, **kwargs) -> str:
        use_json = self._use_json
        params = {"sl": self._source, "tl": self._target, "q": text}
        url = "https://translate.google.com/m"
        if use_json:
            url = "https://translate.googleapis.com/translate_a/single"
            params.update(client="gtx", dt="t")
        response = None
        try:
            response = requests.get(url, params=params, proxies=self.proxies,
                                    timeout=REQUEST_TIMEOUT)
            if response.status_code == 429:
                raise TooManyRequests()
            if response.status_code != 200:
                raise RequestError()
            if use_json:
                try:
                    rows = response.json()[0]
                    if not isinstance(rows, list) or not rows:
                        raise _InvalidResponse()
                    parts = []
                    for row in rows:
                        if not isinstance(row, list) or not row or not isinstance(row[0], str) or not row[0].strip():
                            raise _InvalidResponse()
                        parts.append(row[0])
                    result = "".join(parts).strip()
                except (ValueError, TypeError, IndexError, KeyError) as exc:
                    raise _InvalidResponse() from exc
            else:
                soup = BeautifulSoup(response.text, "html.parser")
                element = soup.find("div", class_="t0") or soup.find("div", class_="result-container")
                result = element.get_text(" ", strip=True) if element else ""
            if not result:
                raise _InvalidResponse()
            return result
        except (requests.RequestException, TooManyRequests, RequestError, _InvalidResponse):
            self._use_json = not use_json
            raise
        finally:
            if response is not None:
                response.close()


def _split_text(text: str, limit: int | None = None) -> list[str]:
    """Metnin hiçbir bölümünü kesip atmadan çeviri isteklerine böl.

    Boşluk sınırlarını tercih eder; boşluksuz uzun bir bölüm varsa karakter
    sınırından böler. Bölüm içinde kalan satır sonları korunur.
    """
    return [chunk for chunk, _ in _split_segments(text, limit)]


def _split_segments(text: str, limit: int | None = None) -> list[tuple[str, str]]:
    """Bölümleri ve sonraki bölümün ayıracını sakla; satırları silme."""
    limit = MAX_CHARS if limit is None else limit
    if limit < 1:
        raise ValueError("limit en az 1 olmalı")

    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [(text, "")]

    chunks = []
    while len(text) > limit:
        boundaries = list(re.finditer(r"\s+", text[:limit + 1]))
        boundary = boundaries[-1] if boundaries else None
        cut = boundary.start() if boundary and boundary.start() > 0 else limit
        end = cut
        while end < len(text) and text[end].isspace():
            end += 1
        chunks.append((text[:cut], text[cut:end]))
        text = text[end:]
    if text:
        chunks.append((text, ""))
    return chunks


def _translate_chunk(engine: GoogleTranslator, chunk: str, cancel_event=None) -> str:
    """Ağ ve servis hatalarını sınırlı sayıda yeniden dene; boş çıktı yutma."""
    for attempt in range(len(RETRY_DELAYS) + 1):
        _check_cancelled(cancel_event)
        try:
            result = engine.translate(chunk)
            _check_cancelled(cancel_event)
            if not isinstance(result, str) or not result.strip():
                raise _InvalidResponse()
            return result.strip()
        except (TooManyRequests, RequestError, requests.RequestException, _InvalidResponse) as exc:
            _check_cancelled(cancel_event)
            if attempt == len(RETRY_DELAYS):
                if isinstance(exc, TooManyRequests):
                    message = "Google çeviri servisi şu anda çok yoğun veya bağlantınızı geçici olarak sınırladı. Biraz sonra yeniden deneyin."
                elif isinstance(exc, requests.RequestException):
                    message = "Çeviri servisine bağlanılamadı. İnternet bağlantınızı kontrol edip yeniden deneyin."
                else:
                    message = "Çeviri servisi geçerli bir çeviri döndürmedi. Biraz sonra yeniden deneyin."
                raise RuntimeError(message) from exc
            if cancel_event is None:
                time.sleep(RETRY_DELAYS[attempt])
            else:
                cancel_event.wait(RETRY_DELAYS[attempt])
                _check_cancelled(cancel_event)


class MyMemoryTranslator:
    """Documented anonymous API: 500 UTF-8 bytes/request, 5000 chars/day.

    Only /get is used; no translation-memory contributions are submitted.
    """
    def __init__(self, source, target):
        self.source = {"zh-Hans": "zh-CN"}.get(source, source)
        self.target = target

    def translate(self, text):
        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"{self.source}|{self.target}"},
            timeout=REQUEST_TIMEOUT,
        )
        try:
            if response.status_code == 429:
                raise RuntimeError("MyMemory günlük çeviri kotası doldu. Daha sonra dene veya Ayarlar’dan Google’ı seç.")
            if response.status_code != 200:
                raise RequestError()
            try:
                data = response.json()
                if data.get("quotaFinished") or str(data.get("responseStatus")) == "429":
                    raise RuntimeError("MyMemory günlük çeviri kotası doldu (5.000 karakter). Daha sonra dene veya Ayarlar’dan Google’ı seç.")
                if str(data.get("responseStatus")) != "200":
                    raise RuntimeError("MyMemory bu dil çiftini çeviremedi. Ayarlar’dan ekrandaki metnin dilini kontrol et.")
                result = data["responseData"]["translatedText"]
                if not isinstance(result, str) or not result.strip():
                    raise _InvalidResponse()
                return result
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                raise _InvalidResponse() from exc
        finally:
            response.close()


def _byte_segments(text, limit=500):
    """Split Unicode without dropping bytes or paragraph separators."""
    while text:
        size = 0
        end = 0
        for char in text:
            size += len(char.encode("utf-8"))
            if size > limit:
                break
            end += 1
        if end == len(text):
            yield text, ""
            return
        if not end:
            raise ValueError("Byte limit cannot hold one character")
        boundaries = list(re.finditer(r"\s+", text[:end + 1]))
        cut = boundaries[-1].start() if boundaries and boundaries[-1].start() else end
        after = cut
        while after < len(text) and text[after].isspace():
            after += 1
        yield text[:cut], text[cut:after]
        text = text[after:]


def translate(text: str, target: str = "tr", cancel_event=None,
              provider: str = "google", source: str = "en") -> str:
    _check_cancelled(cancel_event)
    text = text.strip()
    if not text:
        return ""

    if provider == "mymemory":
        if source == target:
            return text
        engine = MyMemoryTranslator(source, target)
        segments = _byte_segments(text.replace("\r\n", "\n"))
    elif provider == "google":
        engine = GoogleTranslator(source="auto", target=target)
        segments = _split_segments(text.replace("\r\n", "\n"))
    else:
        raise ValueError("Bilinmeyen çeviri sağlayıcısı")
    # Kısa çok satırlı metin tek istekte çevrilir. Büyük metin bölünürken
    # sınırdaki paragraf ayraçlarını koru. Herhangi bir bölüm başarısız olursa
    # eksik sonucu başarı gibi döndürme.
    return "".join(_translate_chunk(engine, chunk, cancel_event) + separator
                   for chunk, separator in segments)
