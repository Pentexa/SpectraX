# Planet X and SPHEREx Target Validation

15 November 2026. We obtained reference astrometry for the targets from SIMBAD and downloaded FITS cutouts from NASA/IPAC IRSA centered on the predicted ICRS position at each observation midpoint. These examples document observation selection and quality checks. A reliable measurement of change across epochs requires more than a single valid pixel. [IRSA data access](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

| Target | Example observations | Result |
| --- | --- | --- |
| Barnard's Star | 13 D6 cutouts from DR1 and QR3 | Every cutout covered the star. The best cutout had 4 of 9 valid core pixels. This sample did not yield a proper-motion measurement. |
| Epsilon Indi B | DR1 `2025W40_1A_0444_3/D6`, `2026W18_1A_0502_1/D6` | The blended source shifted 3.98″ east and 1.38″ south over 210.43 days. Five common reference sources verified registration. |
| WISE 0855−0714 | DR1 `2025W46_1A_0238_1/D6`, `2026W17_1B_0227_4/D6` | We measured a relative displacement of 5.13″ west and 1.71″ north over 161.22 days. Six common reference sources verified registration. |
| RW Aurigae | DR1 `2025W36_1A_0095_1/D1`, `2026W10_1A_0445_1/D1`, `2026W11_1A_0285_4/D1` | The initial single-source fit had large residuals. In later observations, core masking or missing variance prevented a measurement. This sample did not yield a reliable flux difference. |
| R Draconis | DR1 `2025W23_2B_0130_1/D6`, `2026W01_1A_0534_3/D6` | Both FITS files were readable. Quality flags or missing variance prevented a source fit. |

The published angular separation of Epsilon Indi Ba and Bb is about 0.73″. SPHEREx spectral images have a pixel scale of about 6″, so the pair appears blended in this sample. [Epsilon Indi observation](https://arxiv.org/abs/astro-ph/0309256) · [SPHEREx data products](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-products/)

We tested ten more D2 visits across two DR1 time windows for RW Aurigae using a 1.31 µm archive filter. The four cutouts we retrieved failed the pixel-quality criteria for source fitting. The archive request failed for the other six cutouts.

To reproduce the results, use `GET /api/targets/{target_id}/observations` to retrieve records and predicted positions. For each archive ID, send the predicted position for that observation and `fov: 0.05` to `POST /api/archive/import`. Send the returned epoch IDs and `target_id` to `POST /api/source-series`. The `predicted_catalog_offset_arcsec` field reports the catalog prediction. The API computes `light_curves[].change` only from compatible flux measurements that pass the quality checks. [Barnard pixel audit](BARNARDS_STAR.md)

## Target pairs available in the app

`planet-x-data --include-benchmarks` prepares FITS files for all five targets and verifies their SHA-256 checksums. Each prepared timeline contains three real observations. `GET /api/targets/{target_id}/benchmark` returns the comparison pair. `POST /api/timeline` returns observations in chronological order on a common WCS.

| Target | IRSA observations shown in the app | SPHEREx measurement |
| --- | --- | --- |
| Barnard's Star | DR1 `2025W35_1A_0484_2/D6`, `2026W19_1A_0403_1/D6` | About 0.75″ east and 7.13″ north over 250.6 days. The measurement uses unmasked wings and 17 common reference stars. |
| RW Aurigae | DR1 `2026W11_1A_0285_1/D1`, QR3 `2026W37_1A_0234_3/D1` | Aperture flux rose from 131.0 to 200.5 mJy at about 0.77 µm over 181.84 days. |
| R Draconis | DR1 `2025W29_1A_0141_4/D1`, QR3 `2026W28_2A_0364_4/D1` | The unmasked outer rings dimmed at about 0.78 µm over 361.65 days. The core was saturated in both exposures. |

For RW Aurigae, we subtracted the local background using apertures of 2 and 2.5 pixels in radius and applied an ePSF aperture correction. The two radii yielded flux differences of +69.5 and +68.9 mJy, respectively. The approximately 12.0 mJy uncertainty on the first result includes FITS variance, background noise, and an assumed independent 5% systematic allowance per observation. The measurement represents the combined light of the star system.

For R Draconis, we aligned the two images on a common WCS and subtracted the background from pixels that passed the wavelength and quality checks. Median surface brightness fell from 2.69 to 1.11 MJy/sr in the 25–37″ ring and from 0.99 to 0.45 MJy/sr in the 37–49″ ring. All four sectors in both rings changed in the same direction. The pair `2025W29_1A_0141_3/D1` and `2026W28_2A_0364_3/D1` showed the same trend at approximately 0.762 µm. The measurement describes the surface brightness of the wings outside the saturated core. [IRSA data products and flags](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf)

We identified candidate exposures in published SIA result lists, downloaded the FITS files from IRSA, and recalculated the measurements from those files. [Archived SIA results](https://github.com/FearmessOp/blackhole-spherex/tree/main/data/sia)

## WISE 0855 hareket testi

15 November 2026. We used 0.20° FITS cutouts and a 0.18° registration field. The uncertainties along the two axes are approximately 1.23″ and 1.29″. The two-dimensional Mahalanobis distance is 4.51. Comparing the same first observation with a different second visit, `2026W17_1B_0507_3/D6`, yielded a shift of 5.30″ west and 1.52″ north using eight reference sources. The local wavelengths differ between the two observations, so this result supports the astrometry. We did not compute a brightness change from these observations.

If the cutout service is unavailable, the download tool uses full FITS files from the IRSA AWS mirror. The full images yielded one additional common reference source. We measured 5.34″ west and 1.62″ north from these images. [IRSA archive access](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

Run the test again with the two FITS files pinned by SHA-256.

```powershell
$env:PLANET_X_MANIFEST = 'data/manifests/spherex-wise-0855.json'
$env:PLANET_X_DATA_DIR = 'data/samples/wise-0855'
.\.venv\Scripts\planet-x-data.exe
.\.venv\Scripts\planet-x-api.exe
```

With the API running, run `python scripts/smoke_backend.py --wise-0855` in another terminal. To load the same observations in the frontend, submit the DR1 IDs and cutout centers below to `/api/archive/import`. Send the two returned epoch IDs to `POST /api/astrometry` with `target_id=wise-0855` and `fov=0.18`.

| Archive record | RA | Dec | Cutout width |
| --- | ---: | ---: | ---: |
| `ivo://irsa.ipac/spherex_dr1?2025W46_1A_0238_1/D6` | 133.76019838679107° | −7.242244305443577° | 0.20° |
| `ivo://irsa.ipac/spherex_dr1?2026W17_1B_0227_4/D6` | 133.7589615748621° | −7.2421046267988975° | 0.20° |

## Epsilon Indi B motion test

15 November 2026. With `target_id=epsilon-indi-b` and a 0.20° registration field, the uncertainty was approximately 1.10″ per axis. The two-dimensional Mahalanobis distance was 3.81. The position fit gives the photocenter of the blended source. The table lists the verified DR1 D6 cutouts and their SHA-256 checksums.

| Archive record | RA | Dec | SHA-256 |
| --- | ---: | ---: | --- |
| `ivo://irsa.ipac/spherex_dr1?2025W40_1A_0444_3/D6` | 331.0960799055985° | −56.800529751506424° | `f0282210706193bf9e4e0c2b902d1ed846bd2d52d4ad2424652030996de18583` |
| `ivo://irsa.ipac/spherex_dr1?2026W18_1A_0502_1/D6` | 331.09744651228624° | −56.800835052161254° | `464ce879ef80db459bab4a94ee246bb7c57de0a9f470e597f3813e4bd78c770f` |

## Saturation and optical reference

The 3 × 3 core around Barnard's Star remained masked in additional DR1 cutouts. Fits to the unmasked PSF wings in the earlier 13 cutouts yielded reduced χ² values of 149–652. Additional DR1 and QR3 D1/D2 cutouts of R Draconis had 0 of 9 usable core pixels. Some RW Aurigae cutouts had a pixel near saturation. A D1 cutout with a valid core yielded large model residuals. These tests did not yield a SPHEREx motion or flux difference. [IRSA pixel flags](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html#notes-on-spherex-photometry-flags)

In the AAVSO visual observations of R Draconis, 20 valid measurements over MJD 61180–61208 had a median magnitude of 12.65, and 11 measurements over MJD 61292–61306 had a median magnitude of 7.50. The difference of about 5.15 magnitudes is visible in the optical reference curve. `GET /api/targets/r-draconis/reference-light-curve?start_mjd=61180&end_mjd=61308&limit=129` returns the observations with observer codes and provenance. The photometry was contributed by AAVSO observers. [AAVSO data archive](https://aavso.org/search-and-download-data/)
