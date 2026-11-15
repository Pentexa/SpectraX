# Validation on Real SPHEREx Fields

The DR1 spectrum test selects two HEALPix tiles published by IRSA using ICRS coordinates. Both FITS cubes contain 102 channels, with valid samples in 100 channels at the test coordinates. The flux column gives pixel surface brightness. The cube provides no per-channel uncertainty field. [IRSA cube product](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/#science-data-product-all-sky-cube-dr1-only)

| ICRS RA, Dec | DR1 tile | Surface brightness at 4.6 µm | NHITS |
| --- | ---: | ---: | ---: |
| 269.4500000°, +4.7000000° | 7945 | 0.06335347 MJy/sr | 9 |
| 60.8109955°, +51.3404038° | 445 | 3.54918933 MJy/sr | 10 |

The test reads tile 7945 from the sample pinned in the manifest. It selects tile 445 by coordinate and downloads it from the IRSA AWS mirror. The downloaded FITS for tile 445 has SHA-256 `f098a04d2fed64a051eaf56444c2f18fad84bd9bd1e15b1f964337a9a4139f31`. [IRSA tile 445 example](https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/)

We checked point-source photometry with real observations that produced both high and low SNR using the same ePSF method. The statistical uncertainties come from pixel variance. The last two rows are below the detection threshold and correspond to different wavelengths.

| ICRS RA, Dec | DR1 observation | Wavelength | Flux ± statistical uncertainty | SNR |
| --- | --- | ---: | ---: | ---: |
| 269.448214°, +4.695946° | 2025W40_1A_0471_1/D1 | ≈1.02 µm | 1428.92 ± 53.18 µJy | ≈26.9 |
| 305.598750°, +41.14888889° | 2025W18_1B_0023_2/D1 | 0.7441 µm | 19.37 ± 42.57 µJy | 0.45 |
| 305.598750°, +41.14888889° | 2025W18_1B_0064_1/D1 | 0.7978 µm | −6.36 ± 40.72 µJy | −0.16 |

Quality masks in the first DR1 observation pair prevented a proper-motion measurement for Barnard's Star itself. The pixel in the Barnard field and the high-SNR source are separate validation samples. [Barnard's Star check](BARNARDS_STAR.md)

With the manifest samples installed and an empty import directory, run `python scripts/smoke_backend.py --wide-sky` to verify both spectral fields, the detector layer, and photometry for the low-SNR reference source.
