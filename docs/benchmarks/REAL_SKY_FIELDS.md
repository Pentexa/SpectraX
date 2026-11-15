# Gerçek SPHEREx alanlarında doğrulama

DR1 spektrum testi, IRSA’nın yayımladığı iki farklı HEALPix karosunu ICRS koordinatlarıyla seçer. Her iki FITS küpünde 102 kanal var ve test koordinatlarında 100 kanalın geçerli örneği bulunuyor. Akı sütunu piksel yüzey parlaklığıdır. Küpün kanal başına belirsizlik alanı yoktur. [IRSA küp ürünü](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/#science-data-product-all-sky-cube-dr1-only)

| ICRS RA, Dec | DR1 karo | 4,6 µm yüzey parlaklığı | NHITS |
| --- | ---: | ---: | ---: |
| 269.4500000°, +4.7000000° | 7945 | 0,06335347 MJy/sr | 9 |
| 60.8109955°, +51.3404038° | 445 | 3,54918933 MJy/sr | 10 |

Karo 7945 manifestteki sabit örnekten okunur. Karo 445 koordinata göre seçilir ve IRSA’nın AWS aynasından indirilir. İndirilen 445 numaralı FITS dosyasının SHA-256 değeri `f098a04d2fed64a051eaf56444c2f18fad84bd9bd1e15b1f964337a9a4139f31`. [IRSA karo 445 örneği](https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/)

Nokta kaynak fotometrisi, aynı ePSF yönteminin yüksek ve düşük SNR verdiği gerçek gözlemlerle denetlendi. Belirsizlikler piksel varyansından hesaplanan istatistiksel hatalardır. Son iki satırdaki değerler tespit eşiğinin altında ve farklı dalga boylarına ait.

| ICRS RA, Dec | DR1 gözlemi | Dalga boyu | Akı ± istatistiksel hata | SNR |
| --- | --- | ---: | ---: | ---: |
| 269.448214°, +4.695946° | 2025W40_1A_0471_1/D1 | ≈1,02 µm | 1428,92 ± 53,18 µJy | ≈26,9 |
| 305.598750°, +41.14888889° | 2025W18_1B_0023_2/D1 | 0,7441 µm | 19,37 ± 42,57 µJy | 0,45 |
| 305.598750°, +41.14888889° | 2025W18_1B_0064_1/D1 | 0,7978 µm | −6,36 ± 40,72 µJy | −0,16 |

Barnard Yıldızı’nın kendisinde özdevinim ölçümü, ilk DR1 gözlem çiftindeki kalite maskeleri nedeniyle yapılamadı. İlk tablodaki Barnard alanı pikseli ve yüksek SNR’li kaynak, bu özdevinim ölçümünün yerine geçmez. [Barnard Yıldızı kontrolü](BARNARDS_STAR.md)

Manifest örnekleri yüklü ve içe aktarma dizini boşken `python scripts/smoke_backend.py --wide-sky` ile iki spektrum alanını, dedektör katmanını ve düşük SNR’li referansın fotometrisini tekrar doğrula.
