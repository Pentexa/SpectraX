# Barnard Yıldızı özdevinim kontrolü

## D6 kanat ölçümü

DR1 `2025W35_1A_0484_2/D6` ve `2026W19_1A_0403_1/D6` görüntülerinden 250,6 günde **0,75 ± 1,27″ doğu** ve **7,13 ± 0,83″ kuzey** göreli kayma ölçüldü. Katalog bu tarihler için 7,20″ kuzey yönünde görünür hareket öngörüyor.

Çekirdekteki doyum maskesi uygulandı. Merkez, işaretlenmemiş kanat piksellerinde ayrı ayrı 1,8–6,5 ve 2,8–8,5 piksel yarıçap aralıklarıyla uyduruldu. İki pencerenin merkez farkı her gözlemde 0,9″ altında kaldı. Belirsizlikler pencere duyarlılığını ve 17 ortak referans yıldızının hizalama saçılımını içeriyor.

## İlk iki DR1 görüntüsü

2025 Ekim ve 2026 Mart çiftinin sonucu `not_testable`. Hazır demo kesitleri yıldızın iki gözlem tarihindeki konumunun güneyinde kalıyor. Orijinal DR1 görüntüleri hedefi kapsıyor. Her iki görüntüde de beklenen hedef konumu etrafındaki 3 × 3 pikselin tamamı kalite maskesine giriyor.

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

## Canlı IRSA arşiv taraması

`--archive` seçeneği tahmini ICRS konumu etrafındaki DR1 ve QR3 kayıtlarını IRSA SIA2 ile sorgular. 4,65 µm katalog filtresinde üç zaman penceresinden farklı ziyaretler örneklenir. Her 0,05° FITS kesiti gözlem ortasına göre hesaplanan konuma merkezlenir. JSON raporu arşiv kimliğini, FITS erişim adresini, SHA-256 değerini ve geçerli çekirdek pikseli sayısını kaydeder. [IRSA veri erişimi](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

```powershell
.\.venv\Scripts\python.exe -m pipeline.benchmark_barnard --archive --per-window 3
.\.venv\Scripts\python.exe -m pipeline.benchmark_barnard --archive --per-window 4
```

15 Kasım 2026 tarihli iki taramada aşağıdaki 13 farklı D6 kesiti hedefi kapsadı. Tekrar eden gözlemler tabloda bir kez yer alıyor. Çekirdek kontrolü her kesitte hedefin çevresindeki 3 × 3 piksele uygulandı.

| Sürüm | Gözlem kimliği | Gözlem tarihi (UTC) | Geçerli çekirdek pikseli | Birleşik bayrak |
| --- | --- | --- | ---: | ---: |
| DR1 | `2025W33_2C_0321_1/D6` | 2025-08-15 | 1 / 9 | 69206023 |
| DR1 | `2025W33_2C_0386_3/D6` | 2025-08-16 | 2 / 9 | 69206023 |
| DR1 | `2025W34_1B_0164_1/D6` | 2025-08-18 | 0 / 9 | 69206023 |
| DR1 | `2025W34_2B_0030_1/D6` | 2025-08-21 | 1 / 9 | 69206021 |
| DR1 | `2025W35_1A_0484_1/D6` | 2025-08-27 | 2 / 9 | 69206023 |
| DR1 | `2026W12_1A_0598_1/D6` | 2026-03-19 | 0 / 9 | 69206023 |
| DR1 | `2026W12_2A_0520_1/D6` | 2026-03-22 | 1 / 9 | 69206023 |
| DR1 | `2026W13_1A_0549_1/D6` | 2026-03-25 | 1 / 9 | 69206023 |
| DR1 | `2026W15_2A_0137_1/D6` | 2026-04-10 | 1 / 9 | 69206023 |
| DR1 | `2026W19_1A_0403_1/D6` | 2026-05-05 | 2 / 9 | 69206023 |
| QR3 | `2026W34_1A_0176_1/D6` | 2026-08-17 | 1 / 9 | 69206023 |
| QR3 | `2026W34_1A_0238_1/D6` | 2026-08-18 | 4 / 9 | 2097154 |
| QR3 | `2026W34_1A_0308_1/D6` | 2026-08-18 | 1 / 9 | 69206023 |

`2097154`, `SOURCE` ve `OVERFLOW` bitlerini içeriyor. İki ek QR3 kimliği, kesit merkeziyle yapılan arşiv sorgusunda eşleşmedi ve kalite değerlendirmesine katılmadı. İncelenen örnekte çekirdeği tamamen geçerli bir gözlem bulunamadı. Ölçülen kayma ve belirsizlik boş kaldı. [IRSA piksel bayrakları](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html#notes-on-spherex-photometry-flags)
