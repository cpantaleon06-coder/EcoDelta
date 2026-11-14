# EcoDelta

NASA Space Apps Challenge 2026, "Be an Earth System Trend Detective".

| Folder | What it is |
|---|---|
| [trendkit/](trendkit/) | Statistics package: deseasonalizing, Sen's slope, Mann-Kendall with autocorrelation correction, FDR, regional means |
| [ecodelta-engine/](ecodelta-engine/) | Engine: screens and ranks variables per region with trendkit and exports JSON for the web app (`web_data/`) |
| nasa-data/ | Not here yet: download and regridding of the NASA data (MERRA-2, GPM IMERG, GLDAS) |

Until `nasa-data/` is in this repository, point the engine at the data folder with
`ECODELTA_DATA_DIR=/path/to/nasa-data`. See each folder's README for install and run commands.
