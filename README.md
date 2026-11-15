# EcoDelta

NASA Space Apps Challenge 2026, "Be an Earth System Trend Detective".

| Folder | What it is |
|---|---|
| [trendkit/](trendkit/) | Statistics package: deseasonalizing, Sen's slope, Mann-Kendall with autocorrelation correction, FDR, regional means |
| [ecodelta-engine/](ecodelta-engine/) | Engine: screens and ranks variables per region with trendkit and exports JSON for the web app (`web_data/`) |
| nasa-data/ | Not here yet: download and regridding of the NASA data (MERRA-2, GPM IMERG, GLDAS) |

## What is real, and what EcoDelta held back

The real export (built 2026-11-15) has four water variables: rain and snow (GPM IMERG), evaporation,
surface runoff and soil moisture (GLDAS). They have passed pipeline checks only, not an independent
check. Air temperature (MERRA-2) is **held back**: our pipeline reproduces NASA POWER to about 1%, but
POWER is built on MERRA-2, and against the independent GISTEMP v4 record the MERRA-2 global trend is
about one third lower, while the Sahel showed a cooling we could not confirm. EcoDelta checks its own
output and does not publish what it cannot defend. Details and numbers:
[ecodelta-engine/docs/VALIDATION.md](ecodelta-engine/docs/VALIDATION.md) and
[docs/DESCRIPTION.md](docs/DESCRIPTION.md).

Regions are approximate boxes, not country borders. When two compared boxes overlap, their averages
share data and the result compares two overlapping areas; read it with caution.

Submission documents: [docs/](docs/) (description, pitch, demo, TODO list).

## Running it

Until `nasa-data/` is in this repository, point the engine at the data folder with
`ECODELTA_DATA_DIR=/path/to/nasa-data`. See each folder's README for install and run commands.
