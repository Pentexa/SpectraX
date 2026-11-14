# SPHEREx veri envanteri

14 Kasım 2026. IRSA, SPHEREx DR1 ile Survey 1–2 spektral görüntülerini ve 102 kanallı All-Sky Cube ürününü yayımladı. QR3, Survey 3–4 spektral görüntülerini kapsıyor. Her iki sürüm de IRSA SIA2 ile sorgulanabiliyor. Bu backend örneği yalnızca DR1 dosyaları kullanıyor. [IRSA sürüm notları](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-releases/) · [Erişim yöntemleri](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

| Source / release | Epoch ve arşiv kimliği | Bands | Coverage | Flags / uncertainty | Access ve boyut |
| --- | --- | --- | --- | --- | --- |
| NASA/IPAC IRSA SPHEREx DR1 L2B v27 | `dr1-2025-10-01-d1`, 1 Ekim 2025 03:07:36 UTC, `2025W40_1A_0471_1` | D1 LVF, merkez ≈ 1.0235 μm | RA 269.45°, Dec 4.7°, 0.05° kesit | `FLAGS`, `VARIANCE`, `ZODI`, `EPSF`, `WCS-WAVE` | [IRSA kesiti](https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W40_1A/l2b-v27-2026-239/1/level2_2025W40_1A_0471_1D1_spx_l2b-v27-2026-239.fits?center=269.45,4.7&size=0.05) 3 965 760 B · [Tam görüntü](https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/dr1/level2/2025W40_1A/l2b-v27-2026-239/1/level2_2025W40_1A_0471_1D1_spx_l2b-v27-2026-239.fits) 62 124 480 B |
| NASA/IPAC IRSA SPHEREx DR1 L2B v27 | `dr1-2026-03-11-d1`, 11 Mart 2026 15:15:30 UTC, `2026W11_1A_0556_2` | D1 LVF, merkez ≈ 1.0257 μm | Aynı 0.05° kesit | `FLAGS`, `VARIANCE`, `ZODI`, `EPSF`, `WCS-WAVE` | [IRSA kesiti](https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2026W11_1A/l2b-v27-2026-232/1/level2_2026W11_1A_0556_2D1_spx_l2b-v27-2026-232.fits?center=269.45,4.7&size=0.05) 3 965 760 B · [Tam görüntü](https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/dr1/level2/2026W11_1A/l2b-v27-2026-232/1/level2_2026W11_1A_0556_2D1_spx_l2b-v27-2026-232.fits) 63 092 160 B |
| NASA/IPAC IRSA SPHEREx DR1 All-Sky Cube | `dr1-coadd`, 12 Ağustos 2025–8 Mayıs 2026, `Npix7945_cube` | Her dedektörde 17 nominal kanal, toplam 102 | Norder5, HEALPix 7945, 512 × 512 piksel | `NHITS`, `FLAGS`, `SPECTRAL_CHANNELS`, `WCS-WAVE`. Akı belirsizliği sağlanmıyor. | [IRSA AWS aynası](https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/dr1/hips5_cube/hips_20261026/Norder5/Dir0/Npix7945_cube.fits) 320 909 760 B |

IRSA SIA2 `COLLECTION=spherex_dr1`, `POS=circle 269.45 4.7 0.002` sorgusu 240 görüntü kaydı döndürdü. Seçilen iki görüntü FITS başlığında ayrı gözlem zamanları taşıyor. Dalga boyu ve bant genişliği her pikselin LVF WCS kaydından hesaplanıyor. Her dedektör katmanı tek bir nominal kanal düzlemi sunuyor. [SPHEREx Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf)

### Doğrulanan senaryo

0.04° alanda iki görüntünün geometrik hizalama ve kalite maskesi sonrası ortak piksel oranı %94.0. Dalga boyu uyumluluğu da dahil edildiğinde %90.4. Beş ortak kaynağın medyan göreli konum farkı 0,17 yay saniyesi ve RMS saçılımı 1,27 yay saniyesi. Merkez piksel parlaklık farkı `+0.0249 ± 0.0320 MJy/sr`. Belirsizlik FITS varyansından gelir. Bu değer merkez pikseli temsil eder. Altı dedektörün birleşik küpünde aynı koordinatta 100 geçerli kanal var. İki kanalda `NHITS=0` olduğu için değerleri `null`. [Barnard Yıldızı hedef kontrolü](benchmarks/BARNARDS_STAR.md)

### Atıf ve kullanım

Bu kamuya açık veri kimlik bilgisi olmadan indirilebilir. SPHEREx, JPL ve Caltech'in ortak NASA görevidir. IRSA, görüntüler için [10.26131/IRSA678](https://doi.org/10.26131/IRSA678) ve küp için [10.26131/IRSA679](https://doi.org/10.26131/IRSA679) DOI'lerini ve yayımlanan çalışmalarda görev teşekkür metnini kullanmayı istiyor. [DR1 atıf yönergesi](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html) · [IRSA veri kullanım koşulları](https://irsa.ipac.caltech.edu/data_use_terms.html)
