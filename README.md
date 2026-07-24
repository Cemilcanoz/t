# T — Ekran Çeviri Aracı

Ekranın herhangi bir bölgesini seçip içindeki metni anında çeviren, sistem
tepsisinde çalışan hafif bir masaüstü uygulaması.

## Kurulum

**Hazır .exe ile** — [Releases](../../releases) bölümünden `T.exe` dosyasını
indir ve çift tıkla. Python kurulumuna gerek yok.

**Kaynak koddan:**

```
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\pythonw.exe main.py
```

`pythonw.exe` kullanıldığı için siyah konsol penceresi açılmaz. Uygulama ilk
açılışta masaüstüne kısayol oluşturmayı teklif eder.

## Kendin derlemek istersen

```
venv\Scripts\pip install pyinstaller
venv\Scripts\pyinstaller T.spec --noconfirm --clean
```

Sonuç `dist\T.exe` olarak çıkar. `T.spec` dosyasındaki `excludes` listesi
kullanılmayan Qt modüllerini (tarayıcı motoru, 3B, multimedya…) dışarıda
bırakarak dosya boyutunu küçük tutar.

## Kullanım

| Ne yapmak istiyorsun | Nasıl |
|---|---|
| Çeviri başlat | `Alt+T` · yüzen logoya tıkla · tepsi ikonuna sol tıkla |
| Alan seç | Fareyle sürükle |
| Seçimi iptal et | `Esc` veya sağ tık |
| Çeviriyi kopyala | Karttaki kopyala ikonu (kopyalanınca yeşil tike döner) |
| Orijinal metni gör | Karttaki göz ikonu (aç/kapa) |
| Kartı taşı | Ortasından veya başlık çubuğundan sürükle |
| Kartı boyutlandır | Herhangi bir kenardan veya köşeden çek |
| Ayarlar, çıkış | Tepsi ikonuna sağ tık |
| Sorun giderme | Tepsi menüsü → **Tanılama** (rapor Not Defteri'nde açılır) |

Ayarlar `%APPDATA%\TTranslator\config.json` dosyasında saklanır.

## OCR dil paketleri

Uygulama Windows'un gömülü OCR motorunu kullanır; her dil için o dilin paketi
kurulu olmalıdır. Kurulu diller Ayarlar panelinde listelenir, kurulu olmayanlar
⚠ ile işaretlenir.

Latin alfabesi kullanan diller (İngilizce, Türkçe, Almanca, Fransızca…)
birbirinin metnini okuyabildiği için, istenen dil kurulu değilse aynı alfabeden
kurulu bir dile otomatik geçilir. Farklı alfabeler (Japonca, Rusça, Korece…)
için ilgili paket zorunludur.

Yeni dil eklemek için: **Ayarlar > Zaman ve Dil > Dil ve bölge > Dil ekle**
(kurulum ekranında *Metin tanıma / OCR* kutusunu işaretle).

## Oyunlarda kullanım

- Oyunu **Borderless / Penceresiz Tam Ekran** modunda çalıştır. Exclusive
  Fullscreen modunda hiçbir overlay (Discord dahil) görünmez.
- Uygulamanın hiçbir penceresi odak almaz (`WindowDoesNotAcceptFocus` +
  `WA_ShowWithoutActivating`). Bu sayede seçim ekranı veya çeviri kartı
  açıldığında oyun aktif pencere olmaktan çıkmaz, masaüstüne düşmez.
- Oyun yönetici olarak çalışıyorsa kısayol tuşunun algılanması için bu
  uygulamayı da yönetici olarak başlat.
- Boştayken CPU kullanımı %0'dır; ekran yalnızca kısayola bastığında bir kez
  yakalanır, sürekli tarama yapılmaz.

## Ölçülen kaynak kullanımı

Windows 11, tek 1536×864 ekran, 16 çekirdek üzerinde `T.exe` ile ölçüldü:

| | |
|---|---|
| Boşta CPU | **%0** (12 sn boyunca 0 ms) |
| RAM | 78 MB, sabit |
| Açılış süresi | ~3.5 sn (tek dosya .exe kendini geçici klasöre açar) |
| OCR süresi | ~0.05 sn |
| Çeviri süresi | ~1.5–3 sn (internet hızına bağlı) |
| `T.exe` boyutu | 58 MB |

Boşta CPU'nun sıfır olması tasarım gereği: ekran sürekli taranmaz, yalnızca
kısayola basıldığında tek bir kare yakalanır.

## Modüller

| Dosya | Görevi |
|---|---|
| `main.py` | Giriş noktası, sistem tepsisi, modüllerin bağlanması |
| `config.py` | Ayarların JSON olarak kaydı/yüklenmesi |
| `ocr_engine.py` | Windows OCR + alfabe bazlı dil yedeklemesi |
| `translator.py` | Google Translate (deep-translator, ücretsiz) |
| `hotkey.py` | Global kısayol tuşu |
| `floating_logo.py` | Sürüklenebilir yüzen "T" logosu |
| `snip_overlay.py` | Snipping Tool tarzı alan seçimi |
| `result_card.py` | Çeviri sonucu kartı |
| `settings_dialog.py` | Ayarlar penceresi |
| `icons.py` | SVG ikonlar (kopyala, göz, kapat) |
| `shortcut.py` | Masaüstü kısayolu (.lnk) oluşturma |
| `T.spec` | PyInstaller derleme yapılandırması |

## Sorun giderme

Bir şey çalışmıyorsa tepsi menüsündeki **Tanılama**'yı çalıştır. OCR dil
paketlerini, OCR okumasını ve çeviri bağlantısını uçtan uca test edip raporu
Not Defteri'nde açar. Komut satırından da çalışır:

```
T.exe --selftest
```
