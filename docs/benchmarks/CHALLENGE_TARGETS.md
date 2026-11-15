# Planet X and SPHEREx hedef doğrulaması

15 Kasım 2026. Hedeflerin referans astrometrisi SIMBAD’dan alındı. FITS kesitleri, her gözlemin ortasındaki tahmini ICRS konumuna göre NASA/IPAC IRSA’dan indirildi. Sonuçlar gözlem seçimi ve kalite kontrolünü belgeleyen örneklerdir. Geçerli bir piksel, güvenilir dönemler arası değişim için tek başına yeterli değildir. [IRSA veri erişimi](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

| Hedef | Örnek gerçek gözlemler | Sonuç |
| --- | --- | --- |
| Barnard Yıldızı | DR1 ve QR3, 13 D6 kesiti | Yıldız her kesitte kapsandı. En iyi kesitte 4/9 çekirdek pikseli geçerliydi. Özdevinim değeri boş. |
| Epsilon Indi B | DR1 `2025W41_2B_0200_1/D4`, `2026W17_1B_0337_3/D4` | 3,497 ve 3,300 µm'de sırasıyla yaklaşık 13.792 ± 112 ve 10.872 ± 102 µJy. İki uyum da yüksek artık verdi. Ölçümler farklı dalga boylarında ve bileşenleri birlikte içeriyor. |
| WISE 0855−0714 | DR1 `2025W46_1A_0238_1/D6`, `2026W17_1B_0227_4/D6` | 161,22 günde 5,13″ batı ve 1,71″ kuzey yönünde göreli kayma ölçüldü. Altı ortak referans kaynağı hizalamayı doğruladı. |
| RW Aurigae | DR1 `2025W36_1A_0095_1/D1`, `2026W10_1A_0445_1/D1`, `2026W11_1A_0285_4/D1` | İlk tek kaynak uyumu yüksek artık verdi. Sonraki gözlemlerde çekirdek maskesi veya eksik varyans ölçümü engelledi. Güvenilir akı farkı döndürülmedi. |
| R Draconis | DR1 `2025W23_2B_0130_1/D6`, `2026W01_1A_0534_3/D6` | Her iki FITS okundu. Kalite bayrakları veya eksik varyans kaynak uyumuna engel oldu. |

Epsilon Indi Ba ve Bb’nin yayımlanmış açısal ayrımı yaklaşık 0,73″. SPHEREx tayfsal görüntülerinin yaklaşık 6″ piksel ölçeğinde bu örneğin iki ayrı bileşen olarak yorumlanması desteklenmiyor. [Epsilon Indi gözlemi](https://arxiv.org/abs/astro-ph/0309256) · [SPHEREx veri ürünü](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-products/)

RW Aurigae için 1,31 µm arşiv filtresiyle iki DR1 zaman penceresinde on D2 ziyaretini daha denedik. İndirilebilen dört kesit kaynak uyumu için gereken piksel kalite koşullarını karşılamadı. Diğer altı kesit için arşiv isteği tamamlanamadı.

Sonuçları tekrar üretmek için `GET /api/targets/{target_id}/observations` ile kayıtları ve tahmini konumları al. Her arşiv kimliği için `POST /api/archive/import` çağrısında ilgili gözlemin tahmini konumunu ve `fov: 0.05` değerini kullan. Dönen epoch değerlerini ve `target_id` alanını `POST /api/source-series` çağrısına gönder. `predicted_catalog_offset_arcsec` katalog tahminidir. `light_curves[].change` yalnızca uyumlu ve yeterli kalitedeki akı ölçümleri için hesaplanır. [Barnard piksel denetimi](BARNARDS_STAR.md)

## WISE 0855 hareket testi

15 Kasım 2026. 0,20° FITS kesitleri ve 0,18° hizalama alanı kullanıldı. Ölçümde eksen başına belirsizlik yaklaşık 1,23″ ve 1,29″. İki boyutlu Mahalanobis uzaklığı 4,51. Aynı ilk gözlem, farklı bir ikinci ziyaret olan `2026W17_1B_0507_3/D6` ile karşılaştırıldığında sekiz referans kaynağıyla 5,30″ batı ve 1,52″ kuzey yönünde kayma ölçüldü. İlk ve ikinci gözlemlerin yerel dalga boyları farklı olduğundan bu sonuç astrometriyi doğrular. Parlaklık değişimi bu gözlemlerden hesaplanmadı.

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
