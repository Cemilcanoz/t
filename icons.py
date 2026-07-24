"""SVG tabanlı ikonlar.

Emoji yerine SVG kullanmamızın sebebi: emoji görünümü Windows sürümüne ve yazı
tipine göre değişir, renk kontrolü yoktur ve büyük boyutlarda bulanıklaşır.
SVG vektörel olduğu için her ölçekte net kalır ve rengini biz belirleriz.

Her ikon tek bir <svg> metni; `stroke="CUR"` yer tutucusu istenen renkle
değiştirilip QIcon'a dönüştürülür. Üretilen QIcon'lar önbelleğe alınır, böylece
her kart açılışında yeniden çizim yapılmaz.
"""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_PLACEHOLDER = "CUR"

# --- Kopyala: klasik "üst üste iki sayfa" ikonu -------------------------------
COPY = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="CUR" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
  <rect x="9" y="9" width="11" height="12" rx="2.2"/>
  <path d="M5 15H4.5A1.5 1.5 0 0 1 3 13.5v-9A1.5 1.5 0 0 1 4.5 3h9A1.5 1.5 0 0 1 15 4.5V5"/>
</svg>
"""

# --- Kopyalandı onayı: tik ----------------------------------------------------
CHECK = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="CUR" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 12.5 9.5 18 20 6.5"/>
</svg>
"""

# --- Orijinali göster / gizle: göz ve üstü çizili göz -------------------------
# Göz ikonu 15px'te bile net okunur ve iki durumu (görünür/gizli) tek bakışta
# ayırt edilir kılar. Çeviri gösterilirken EYE, orijinal gösterilirken EYE_OFF.
EYE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="CUR" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
  <path d="M2 12s3.7-6.6 10-6.6S22 12 22 12s-3.7 6.6-10 6.6S2 12 2 12Z"/>
  <circle cx="12" cy="12" r="2.9"/>
</svg>
"""

EYE_OFF = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="CUR" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
  <path d="M10.7 6.1A10.4 10.4 0 0 1 12 5.4c6.3 0 10 6.6 10 6.6a18.4 18.4 0 0 1-3.2 3.9"/>
  <path d="M6.4 7.8A18.2 18.2 0 0 0 2 12s3.7 6.6 10 6.6a10.3 10.3 0 0 0 4-.8"/>
  <path d="M9.9 9.9a2.9 2.9 0 0 0 4.1 4.1"/>
  <path d="M3.2 3.2 20.8 20.8"/>
</svg>
"""

# --- Kapat --------------------------------------------------------------------
CLOSE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="CUR" stroke-width="2" stroke-linecap="round">
  <path d="M6 6l12 12M18 6L6 18"/>
</svg>
"""

_cache: dict = {}


def icon(svg: str, color: str = "#d8d8e0", size: int = 40) -> QIcon:
    """SVG metnini istenen renkte QIcon'a çevirir (sonuç önbelleğe alınır)."""
    key = (id(svg), color, size)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    data = QByteArray(svg.replace(_PLACEHOLDER, color).encode("utf-8"))
    renderer = QSvgRenderer(data)

    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    result = QIcon(pm)
    _cache[key] = result
    return result
