# SpectraX Development Journey

We built SpectraX for the **Planet X and SPHEREx** challenge at the 2026 NASA Space Apps Challenge. We wanted anyone to be able to pick a patch of sky, compare real observations taken at different times, and explore what changes across SPHEREx’s 102 infrared bands.

## 21 hours of development

The hackathon was scheduled for 48 hours. Our assigned table on level −2 had no working internet connection. We spent a substantial part of the early schedule waiting for access before starting development. When we heard that internet access was available on the third floor, we moved upstairs. We still couldn’t get online there, and the modem that later arrived didn’t provide a working connection either.

We switched to our own mobile data and used it for all **21 hours** we spent developing the project during the event. Once we were connected, our first goal was to get one sky field working end to end. That gave us something we could test and improve while building out the rest of the tool.

## From archive data to an interactive sky

We built a Python and FastAPI pipeline around the public NASA/IPAC IRSA archive. We fetched calibrated DR1 and QR3 FITS exposures, aligned observations on a common sky grid, and carried the FITS quality flags into the comparison. The first working flow grew into side-by-side views, blinking, subtraction, stacking, and a time-ordered sequence of observations. We kept checksum-verified FITS cutouts available for known fields when a live archive request failed. [Data inventory and citations](docs/DATA_SOURCES.md)

In the Next.js frontend, we used Aladin Lite for navigation and added Gaia DR3 and AllWISE reference overlays. We built a separate Spectral Explorer around the DR1 All-Sky Cube so visitors could inspect available wavelength channels and combine the 17 channels of a detector into one image. We also made sky coordinates shareable as links. A visitor can reopen the same field from a link and compare the observations for themselves. [API and processing details](docs/API.md)

## What the five targets taught us

We tested Barnard’s Star, Epsilon Indi B, WISE 0855, RW Aurigae, and R Draconis. The targets required different checks. For WISE 0855 and Barnard’s Star, we measured motion relative to common reference sources. For Epsilon Indi B, the measured position represents the blended source. For RW Aurigae, we checked the brightness change using two aperture sizes. The core of R Draconis was saturated in both exposures, so we measured surface brightness changes in the unmasked outer rings. These cases shaped how we present quality flags, coverage, and measurements in the app. [Target verification report](docs/benchmarks/CHALLENGE_TARGETS.md)

## Taking the project online

We brought the frontend and backend into one repository and added GitHub Actions checks for both. The backend checks cover the archive download and comparison paths, including tests with verified SPHEREx FITS files. We deployed the web app to Vercel and the API to Render, then opened WISE 0855 in the public atlas to verify that both archived images reached the browser. [Open SpectraX](https://frontend-six-alpha-ypiwtpqppn.vercel.app/) · [Project setup](README.md)

## Project team

Ahmet Aras Akyasan, Mustafa Emir Yayla, Korhan Erol, and Nisanur Çakır.

GPT SOL 6.1 supported coding. GLM 5.3 supported code review.
