# Barnard Yıldızı özdevinim kontrolü

**Sonuç `not_testable`.** Hazır demo kesitleri yıldızın iki gözlem tarihindeki konumunun güneyinde kalıyor. Orijinal DR1 görüntüleri hedefi kapsıyor. Her iki görüntüde de beklenen hedef konumu etrafındaki 3 × 3 pikselin tamamı kalite maskesine giriyor. Ölçülen özdevinim ve ölçüm belirsizliği bu veri çifti için boş.

| Gözlem ortası (UTC) | Beklenen RA | Beklenen Dec | Tam görüntüde geçerli çekirdek pikseli |
| --- | ---: | ---: | ---: |
| 2025-10-01 03:08:33.664 | 269.446164° | +4.767589° | 0 / 9 |
| 2026-03-11 15:16:28.426 | 269.446366° | +4.768864° | 0 / 9 |

Her iki tam görüntüde çekirdek bayraklarının bit düzeyinde birleşimi `69206023`. Bu değer `TRANSIENT`, `OVERFLOW`, `SUR_ERROR`, `SOURCE` ve `BLOOM` bitlerini içeriyor. Yıldızın 161,51 gün için katalogdan beklenen görünür yer değiştirmesi 0,72″ doğu ve 4,59″ kuzey yönünde. Tahmin Gaia astrometrisi, SIMBAD radyal hızı ve Astropy Dünya efemerisiyle hesaplandı. Dünya merkezli paralaks yaklaşımı kullanıldı. [SIMBAD astrometrisi](https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=barnard+star&submit=SIMBAD+search) · [Gaia EDR3 astrometrik çözümü](https://arxiv.org/abs/2012.03380) · [IRSA piksel bayrakları](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html#notes-on-spherex-photometry-flags)

Tam görüntüleri ayrı bir dizine indirmek ve sonucu JSON olarak üretmek için şu komutları çalıştır.

```powershell
.\.venv\Scripts\planet-x-data.exe --full-images --data-dir data/samples/full
.\.venv\Scripts\python.exe -m pipeline.benchmark_barnard --data-dir data/samples/full
```

Kullanılan gözlemler `2025W40_1A_0471_1` ve `2026W11_1A_0556_2`. Arşiv bağlantıları ve atıflar [veri envanterinde](../DATA_SOURCES.md).
