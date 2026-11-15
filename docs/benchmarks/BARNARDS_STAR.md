# Barnard's Star Proper Motion Check

## D6 wing measurement

DR1 images `2025W35_1A_0484_2/D6` and `2026W19_1A_0403_1/D6` yielded a relative displacement of **0.75 ± 1.27″ east** and **7.13 ± 0.83″ north** over 250.6 days. The catalog predicts 7.20″ of apparent northward motion for those dates.

We masked the saturated core and fitted the centroid to unflagged wing pixels over two separate radial ranges, 1.8–6.5 and 2.8–8.5 pixels. The centroids from the two windows differed by less than 0.9″ in each observation. The uncertainties include sensitivity to the choice of window and registration scatter across 17 common reference stars.

## First two DR1 images

The October 2025 and March 2026 pair returned `not_testable`. The prepared example cutouts lie south of the star's positions at both observation dates. The original DR1 images cover the target. In both images, the quality mask excludes all 3 × 3 pixels around the expected target position.

| Observation midpoint (UTC) | Expected RA | Expected Dec | Valid core pixels in the full image |
| --- | ---: | ---: | ---: |
| 2025-10-01 03:08:33.664 | 269.446164° | +4.767589° | 0 / 9 |
| 2026-03-11 15:16:28.426 | 269.446366° | +4.768864° | 0 / 9 |

The bitwise OR of the core flags is `69206023` in both full images. It includes `TRANSIENT`, `OVERFLOW`, `SUR_ERROR`, `SOURCE`, and `BLOOM`. The catalog predicts an apparent displacement of 0.72″ east and 4.59″ north over 161.51 days. We calculated this estimate from Gaia astrometry, SIMBAD radial velocity, and the Astropy Earth ephemeris using a geocentric parallax approximation. [SIMBAD astrometry](https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=barnard+star&submit=SIMBAD+search) · [Gaia EDR3 astrometric solution](https://arxiv.org/abs/2012.03380) · [IRSA pixel flags](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html#notes-on-spherex-photometry-flags)

Run these commands to download the full images to a separate directory and report the result as JSON.

```powershell
.\.venv\Scripts\planet-x-data.exe --full-images --data-dir data/samples/full
.\.venv\Scripts\python.exe -m pipeline.benchmark_barnard --data-dir data/samples/full
```

The observations are `2025W40_1A_0471_1` and `2026W11_1A_0556_2`. The [data inventory](../DATA_SOURCES.md) lists archive links and citations.

## Live IRSA archive search

The `--archive` option queries IRSA SIA2 for DR1 and QR3 records near the predicted ICRS position. The 4.65 µm catalog filter samples distinct visits from three time windows. Each 0.05° FITS cutout is centered on the position predicted for the observation midpoint. The JSON report records the archive ID, FITS access URL, SHA-256 checksum, and number of valid core pixels. [IRSA data access](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

```powershell
.\.venv\Scripts\python.exe -m pipeline.benchmark_barnard --archive --per-window 3
.\.venv\Scripts\python.exe -m pipeline.benchmark_barnard --archive --per-window 4
```

Two searches on 15 November 2026 identified the 13 distinct D6 cutouts below that cover the target. The table lists repeated observations once. The core check covers a 3 × 3 pixel region around the target in each cutout.

| Release | Observation ID | Observation date (UTC) | Valid core pixels | Combined flags |
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

`2097154` includes the `SOURCE` and `OVERFLOW` bits. Two other QR3 IDs did not match the archive query at the cutout center, so we excluded them from the quality assessment. The sample contained no observation with a fully valid core. The measured displacement and its uncertainty remained empty. [IRSA pixel flags](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html#notes-on-spherex-photometry-flags)
