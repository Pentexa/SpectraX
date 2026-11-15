# Planet X and SPHEREx hedef doğrulaması

15 Kasım 2026. Hedeflerin referans astrometrisi SIMBAD’dan alındı. FITS kesitleri, her gözlemin ortasındaki tahmini ICRS konumuna göre NASA/IPAC IRSA’dan indirildi. Sonuçlar gözlem seçimi ve kalite kontrolünü belgeleyen örneklerdir. Geçerli bir piksel, güvenilir dönemler arası değişim için tek başına yeterli değildir. [IRSA veri erişimi](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

| Hedef | Örnek gerçek gözlemler | Sonuç |
| --- | --- | --- |
| Barnard Yıldızı | DR1 ve QR3, 13 D6 kesiti | Yıldız her kesitte kapsandı. En iyi kesitte 4/9 çekirdek pikseli geçerliydi. Özdevinim değeri boş. |
| Epsilon Indi B | DR1 `2025W41_2B_0200_1/D4`, `2026W17_1B_0337_3/D4` | 3,497 ve 3,300 µm'de sırasıyla yaklaşık 13.792 ± 112 ve 10.872 ± 102 µJy. İki uyum da yüksek artık verdi. Ölçümler farklı dalga boylarında ve bileşenleri birlikte içeriyor. |
| WISE 0855−0714 | DR1 `2026W17_1B_0227_2/D6`, `2026W17_2A_0609_1/D6` | Sırasıyla 4,424 µm'de 563 ± 107 µJy ve 4,753 µm'de 638 ± 125 µJy. SNR 5,28 ve 5,08. 2025 kesitinde SNR 1,22. Bu örnekten konum kayması veya aynı bantta parlaklık değişimi çıkarılmadı. |
| RW Aurigae | DR1 `2025W36_1A_0095_1/D1`, `2026W10_1A_0445_1/D1`, `2026W11_1A_0285_4/D1` | İlk tek kaynak uyumu yüksek artık verdi. Sonraki gözlemlerde çekirdek maskesi veya eksik varyans ölçümü engelledi. Güvenilir akı farkı döndürülmedi. |
| R Draconis | DR1 `2025W23_2B_0130_1/D6`, `2026W01_1A_0534_3/D6` | Her iki FITS okundu. Kalite bayrakları veya eksik varyans kaynak uyumuna engel oldu. |

Epsilon Indi Ba ve Bb’nin yayımlanmış açısal ayrımı yaklaşık 0,73″. SPHEREx tayfsal görüntülerinin yaklaşık 6″ piksel ölçeğinde bu örneğin iki ayrı bileşen olarak yorumlanması desteklenmiyor. [Epsilon Indi gözlemi](https://arxiv.org/abs/astro-ph/0309256) · [SPHEREx veri ürünü](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-products/)

Sonuçları tekrar üretmek için `GET /api/targets/{target_id}/observations` ile kayıtları ve tahmini konumları al. Her arşiv kimliği için `POST /api/archive/import` çağrısında ilgili gözlemin tahmini konumunu ve `fov: 0.05` değerini kullan. Dönen epoch değerlerini ve `target_id` alanını `POST /api/source-series` çağrısına gönder. `predicted_catalog_offset_arcsec` katalog tahminidir. `light_curves[].change` yalnızca uyumlu ve yeterli kalitedeki akı ölçümleri için hesaplanır. [Barnard piksel denetimi](BARNARDS_STAR.md)
