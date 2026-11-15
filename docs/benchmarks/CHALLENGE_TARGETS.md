# Planet X and SPHEREx hedef doğrulaması

15 Kasım 2026. Hedeflerin referans astrometrisi SIMBAD’dan alındı. FITS kesitleri, her gözlemin ortasındaki tahmini ICRS konumuna göre NASA/IPAC IRSA’dan indirildi. Sonuçlar gözlem seçimi ve kalite kontrolünü belgeleyen örneklerdir. Geçerli bir piksel, güvenilir dönemler arası değişim için tek başına yeterli değildir. [IRSA veri erişimi](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

| Hedef | Örnek gerçek gözlemler | Sonuç |
| --- | --- | --- |
| Barnard Yıldızı | DR1 ve QR3, 13 D6 kesiti | Yıldız her kesitte kapsandı. En iyi kesitte 4/9 çekirdek pikseli geçerliydi. Özdevinim değeri boş. |
| Epsilon Indi B | DR1 `2025W40_1A_0444_3/D6`, `2026W18_1A_0502_1/D6` | Birleşik kaynağın 210,43 günde 3,98″ doğu ve 1,38″ güney yönünde göreli kayması ölçüldü. Beş ortak referans kaynağı hizalamayı doğruladı. |
| WISE 0855−0714 | DR1 `2025W46_1A_0238_1/D6`, `2026W17_1B_0227_4/D6` | 161,22 günde 5,13″ batı ve 1,71″ kuzey yönünde göreli kayma ölçüldü. Altı ortak referans kaynağı hizalamayı doğruladı. |
| RW Aurigae | DR1 `2025W36_1A_0095_1/D1`, `2026W10_1A_0445_1/D1`, `2026W11_1A_0285_4/D1` | İlk tek kaynak uyumu yüksek artık verdi. Sonraki gözlemlerde çekirdek maskesi veya eksik varyans ölçümü engelledi. Güvenilir akı farkı döndürülmedi. |
| R Draconis | DR1 `2025W23_2B_0130_1/D6`, `2026W01_1A_0534_3/D6` | Her iki FITS okundu. Kalite bayrakları veya eksik varyans kaynak uyumuna engel oldu. |

Epsilon Indi Ba ve Bb’nin yayımlanmış açısal ayrımı yaklaşık 0,73″. SPHEREx tayfsal görüntülerinin yaklaşık 6″ piksel ölçeğinde bu örneğin iki ayrı bileşen olarak yorumlanması desteklenmiyor. [Epsilon Indi gözlemi](https://arxiv.org/abs/astro-ph/0309256) · [SPHEREx veri ürünü](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-products/)

RW Aurigae için 1,31 µm arşiv filtresiyle iki DR1 zaman penceresinde on D2 ziyaretini daha denedik. İndirilebilen dört kesit kaynak uyumu için gereken piksel kalite koşullarını karşılamadı. Diğer altı kesit için arşiv isteği tamamlanamadı.

Sonuçları tekrar üretmek için `GET /api/targets/{target_id}/observations` ile kayıtları ve tahmini konumları al. Her arşiv kimliği için `POST /api/archive/import` çağrısında ilgili gözlemin tahmini konumunu ve `fov: 0.05` değerini kullan. Dönen epoch değerlerini ve `target_id` alanını `POST /api/source-series` çağrısına gönder. `predicted_catalog_offset_arcsec` katalog tahminidir. `light_curves[].change` yalnızca uyumlu ve yeterli kalitedeki akı ölçümleri için hesaplanır. [Barnard piksel denetimi](BARNARDS_STAR.md)

## Uygulamada açılan hedef çiftleri

`planet-x-data --include-benchmarks` beş hedefin FITS dosyalarını SHA-256 doğrulamasıyla hazırlar. Her hazır zaman çizelgesi üç gerçek gözlem içerir. `GET /api/targets/{target_id}/benchmark` ölçüm çiftini, `POST /api/timeline` tarih sıralı görüntü dizisini ortak WCS ile döndürür.

| Hedef | Uygulamada açılan IRSA gözlemleri | SPHEREx ölçüm durumu |
| --- | --- | --- |
| Barnard Yıldızı | DR1 `2025W35_1A_0484_2/D6`, `2026W19_1A_0403_1/D6` | 250,6 günde yaklaşık 0,75″ doğu ve 7,13″ kuzey. Ölçüm maskesiz kanatlara ve 17 ortak referans yıldızına dayanıyor. |
| RW Aurigae | DR1 `2026W11_1A_0285_1/D1`, QR3 `2026W37_1A_0234_3/D1` | 181,84 günde yaklaşık 0,77 µm'de açıklık akısı 131,0 mJy'den 200,5 mJy'ye çıktı. |
| R Draconis | DR1 `2025W29_1A_0141_4/D1`, QR3 `2026W28_2A_0364_4/D1` | 361,65 günde yaklaşık 0,78 µm'de maskesiz dış halkalar sönükleşti. Çekirdek iki pozda da doyumlu. |

RW Aurigae için 2 ve 2,5 piksellik açıklıklarla yerel arka plan çıkarıldı ve ePSF ile açıklık düzeltmesi uygulandı. İki yarıçap sırasıyla +69,5 ve +68,9 mJy fark verdi. İlk sonucun yaklaşık 12,0 mJy belirsizliği FITS varyansını, arka plan gürültüsünü ve her gözlem için varsayılan %5 bağımsız sistematik payı içeriyor. Yıldız sisteminin birleşik ışığı ölçüldü.

R Draconis için iki görüntü ortak WCS'ye taşındı. Eşleşen dalga boyu ve kalite maskesini geçen piksellerde arka plan çıkarıldı. 25–37″ halkasının medyan yüzey parlaklığı 2,69'dan 1,11 MJy/sr'ye, 37–49″ halkasınınki 0,99'dan 0,45 MJy/sr'ye indi. İki halkanın dört sektöründe de değişim aynı yöndeydi. `2025W29_1A_0141_3/D1` ve `2026W28_2A_0364_3/D1` çiftinde yaklaşık 0,762 µm'de de aynı yönde değişim görüldü. Bu ölçüm doyum dışındaki kanatların yüzey parlaklığını veriyor. [IRSA veri ürünleri ve bayraklar](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf)

Aday pozların kimlikleri yayımlanmış SIA listelerinden tarandı. FITS dosyaları IRSA'dan indirildi ve buradaki ölçümler bu dosyalardan yeniden hesaplandı. [SIA sonuçlarının kaydı](https://github.com/FearmessOp/blackhole-spherex/tree/main/data/sia)

## WISE 0855 hareket testi

15 Kasım 2026. 0,20° FITS kesitleri ve 0,18° hizalama alanı kullanıldı. Ölçümde eksen başına belirsizlik yaklaşık 1,23″ ve 1,29″. İki boyutlu Mahalanobis uzaklığı 4,51. Aynı ilk gözlem, farklı bir ikinci ziyaret olan `2026W17_1B_0507_3/D6` ile karşılaştırıldığında sekiz referans kaynağıyla 5,30″ batı ve 1,52″ kuzey yönünde kayma ölçüldü. İlk ve ikinci gözlemlerin yerel dalga boyları farklı olduğundan bu sonuç astrometriyi doğrular. Parlaklık değişimi bu gözlemlerden hesaplanmadı.

Kesit servisi erişilemezse indirme aracı IRSA’nın AWS aynasındaki tam FITS dosyalarını kullanır. İki tam görüntüde ek bir ortak referans bulundu. Bu görüntülerden ölçülen kayma 5,34″ batı ve 1,62″ kuzey yönünde. [IRSA arşiv erişimi](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

SHA-256 değerleri sabitlenmiş iki FITS dosyasıyla testi yeniden çalıştır.

```powershell
$env:PLANET_X_MANIFEST = 'data/manifests/spherex-wise-0855.json'
$env:PLANET_X_DATA_DIR = 'data/samples/wise-0855'
.\.venv\Scripts\planet-x-data.exe
.\.venv\Scripts\planet-x-api.exe
```

API çalışırken ayrı bir terminalden `python scripts/smoke_backend.py --wise-0855` komutunu çalıştır. Frontend için aşağıdaki DR1 kimliklerini ve kesit merkezlerini `/api/archive/import` çağrısında kullan. Dönen iki epoch kimliğini `target_id=wise-0855` ve `fov=0.18` ile `POST /api/astrometry` çağrısına gönder.

| Arşiv kaydı | RA | Dec | Kesit genişliği |
| --- | ---: | ---: | ---: |
| `ivo://irsa.ipac/spherex_dr1?2025W46_1A_0238_1/D6` | 133.76019838679107° | −7.242244305443577° | 0.20° |
| `ivo://irsa.ipac/spherex_dr1?2026W17_1B_0227_4/D6` | 133.7589615748621° | −7.2421046267988975° | 0.20° |

## Epsilon Indi B hareket testi

15 Kasım 2026. `target_id=epsilon-indi-b` ve 0,20° hizalama alanıyla eksen başına yaklaşık 1,10″ belirsizlik hesaplandı. İki boyutlu Mahalanobis uzaklığı 3,81. Konum uyumu birleşik kaynağın ışık merkezini verir. Doğrulanan DR1 D6 kesitleri ve SHA-256 değerleri aşağıda.

| Arşiv kaydı | RA | Dec | SHA-256 |
| --- | ---: | ---: | --- |
| `ivo://irsa.ipac/spherex_dr1?2025W40_1A_0444_3/D6` | 331.0960799055985° | −56.800529751506424° | `f0282210706193bf9e4e0c2b902d1ed846bd2d52d4ad2424652030996de18583` |
| `ivo://irsa.ipac/spherex_dr1?2026W18_1A_0502_1/D6` | 331.09744651228624° | −56.800835052161254° | `464ce879ef80db459bab4a94ee246bb7c57de0a9f470e597f3813e4bd78c770f` |

## Doyum ve optik referans

Barnard Yıldızı için ek DR1 kesitlerinde de 3 × 3 çekirdek bölgesi maskeli kaldı. Önceki 13 kesitte maskesiz PSF kanatlarının model uyumu indirgenmiş χ² 149–652 aralığında kaldı. R Draconis'in ek DR1 ve QR3 D1/D2 kesitlerinde kullanılabilir çekirdek pikseli 0/9 idi. RW Aurigae'nin bazı kesitlerinde doyuma yaklaşan piksel, çekirdeği geçerli bir D1 kesitinde ise yüksek model artığı görüldü. Bu sınamalar SPHEREx hareketi veya akı farkı üretmedi. [IRSA piksel bayrakları](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html#notes-on-spherex-photometry-flags)

R Draconis için AAVSO'nun görsel gözlemlerinde MJD 61180–61208 arasında 20 geçerli ölçümün medyanı 12,65 kadir, MJD 61292–61306 arasında 11 ölçümün medyanı 7,50 kadir. Yaklaşık 5,15 kadirlik fark optik referans eğrisinde görülebilir. `GET /api/targets/r-draconis/reference-light-curve?start_mjd=61180&end_mjd=61308&limit=129` çağrısı gözlemci kodları ve kaynak bilgileriyle gerçek gözlemleri döndürür. Fotometriyi AAVSO gözlemcileri sağladı. [AAVSO veri arşivi](https://aavso.org/search-and-download-data/)
