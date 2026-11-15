# Validation of the real export

Status on 2026-11-14: only **air temperature (`t2m`, MERRA-2)** has complete real data (297 months,
2001-01 to 2025-09). After the checks below, the owner decided to **hold `t2m` back**: it is not in the
real export (`hold:` in `data/catalog/variables.yaml`), so there is no real `web_data/` yet. Precipitation (IMERG) and the three GLDAS variables are still
downloading and are **not** in the real export (see `PROBLEMS.md`). Every number below was produced
in this session by the commands named next to it. Nothing was typed from memory.

## 1. Sanity checks for `t2m`

| Check | Result | PASS / FAIL |
|---|---|---|
| Units | Source file `T2M` units `K` (read from the 2001-01 source file into `manifest.json`); exported `degC` (K - 273.15); displayed `°C` | PASS |
| Series start, end, length | `2001-01` to `2025-09`, 297 consecutive months (`load.open_variable` checks this; `meta.period`) | PASS |
| NaN pattern | 0 NaN in the processed file and in the export: all 16,200 cells have 297 valid months. Expected, since a reanalysis has values everywhere, including ocean and both poles. | PASS |
| Cells per region | All 21 regions: valid cells = cells in the box, `covered_fraction` 1.000 (for example global 16,200, Arctic 2,160, Antarctica 2,700, Sahel 145, Western Europe 117) | PASS |
| Regridded vs raw global mean | Re-confirmed against the processed file: 2001-01 raw 12.38798 °C vs file 12.38798 °C (diff +4e-9); 2013-07 16.14889 vs 16.14889 (-5e-9); 2025-09 16.10173 vs 16.10173 (-9e-9). The differences are float32 storage only. | PASS |
| Schema, consistency, golden | `validate --source real`: 46 files, 0 schema errors, 0 consistency errors, 44 numbers recomputed with trendkit, 0 mismatches | PASS |
| Sign of the global trend | +0.163 °C/decade (95% CI +0.057 to +0.271, p = 0.0034). Warming, the same sign as GISTEMP v4. | PASS |
| Size of the global trend | **About one third lower than an independent observational record.** GISTEMP v4 over the same 297 months, same trendkit method: +0.245 °C/decade (CI +0.190 to +0.303). The two CIs overlap, but the MERRA-2 point estimate is low. See 1.1. | **FLAG (not a pipeline error; a known MERRA-2 limitation)** |
| Regional plausibility | Sahel −0.204 °C/decade (significant), Central Africa −0.149 (not significant), East Africa −0.004. A literature search found CRU-based work describing warming across the whole Sahel strip, but no number for our period, so this is **unverified**. | **FLAG (needs an independent check, see section 3)** |

### 1.1 Why the global MERRA-2 trend is low

Zonal comparison with GISTEMP v4 (`ZonAnn.Ts+dSST.csv`), OLS on annual means 2001 to 2024 (complete
years only), °C/decade:

| Band | GISTEMP v4 | MERRA-2 (this export) |
|---|---|---|
| Global | +0.252 | +0.169 |
| 64N-90N | +0.673 | +0.371 |
| 44N-64N | +0.360 | +0.238 |
| 24N-44N | +0.390 | +0.337 |
| EQU-24N | +0.233 | +0.156 |
| 24S-EQU | +0.175 | +0.188 |
| 44S-24S | +0.161 | +0.137 |
| 64S-44S | +0.124 | +0.082 |
| 90S-64S | +0.084 | **−0.405** |

The gap comes mostly from the polar bands, especially Antarctica. This matches a published evaluation:
Simmons et al. (2016, ECMWF ERA Report Series 25, "Estimates of variations and trends of global surface
temperature"). They found MERRA-2 to be an evident outlier: it is colder than all other datasets from
around 2005 onwards, for both the Arctic and the Antarctic. Its Antarctic cooling is linked to colder
values along the coast and over the sea that is ice-covered in winter. Together with land at 60N-60S,
this makes MERRA-2 underestimate recent warming substantially. They also note that MERRA-2 has shifts
tied to changes in its SST analysis.

Caveats on the comparison:
- GISTEMP blends sea surface temperature over the ocean with air temperature over land, and fills the
  polar regions by interpolating up to 1200 km. It is not the same quantity as MERRA-2 `T2M`.
- Simmons et al. analysed data only up to 2016.

Owner decision (2026-11-14): `t2m` is held back from the real export until this is resolved, for
example by the Giovanni comparison in section 3 or a different temperature product.

## 2. End-to-end check of one regional result (Western Europe) against NASA POWER

Command: `.venv/bin/python scripts/validate_power.py western_europe` (raw API responses are cached in
`build/power/`, which is not in git).

**Is NASA POWER independent of MERRA-2? No.** The POWER API response header names its own source as
`"sources": ["MERRA2"]` (API v2.10.0, read live by the script). This comparison therefore validates
our pipeline: OPeNDAP subsetting, unit conversion, conservative regridding, area averaging,
deseasonalizing and trend. It does **not** independently validate the temperature trend itself.

Method:
- **Box.** The engine region box is `[42, 60, -10, 15]`. On the POWER side we take the union of the
  2-degree cells whose centers lie in that box, which has edges `[42, 60, -10, 16]`. POWER native points
  strictly inside these edges are averaged with cos(latitude) weights: 1,435 points, 0 missing.
- **Fetching.** POWER limits regional requests to 10 x 10 degrees, so the box is fetched in tiles.
- **Statistics.** Both series then go through the engine's `regional_report`: monthly climatology
  removed, Mann-Kendall with Yue-Wang correction, Sen's slope, 95% CI.
- **Units.** POWER `T2M` comes in `C`; ours is `degC` converted from K.

| | EcoDelta export | NASA POWER | Difference |
|---|---|---|---|
| Slope (°C/decade) | +0.528 | +0.534 | −0.006 |
| 95% CI | +0.313 to +0.734 | +0.315 to +0.741 | |
| p-value | 4.6e-06 | 4.9e-06 | |
| Lag-1 autocorrelation | 0.306 | 0.304 | |
| Monthly anomalies | | | correlation 0.99995; RMS difference 0.017 °C; max 0.055 °C |

Plausible reasons for the small remaining difference:
- **Time standard.** POWER monthly values use local solar time (`time_standard: LST`), while MERRA-2
  monthly means use UTC.
- **Regridding.** We average 0.625 x 0.5 degree cells conservatively. On the POWER side, points that
  lie exactly on a cell edge are dropped and the rest are averaged as points.
- **Precision.** POWER rounds values to 0.01 °C.

Result: the pipeline reproduces the source data's regional trend to within 1%. **PASS for the pipeline;
no independent validation of the science from this test.**

## 3. Manual comparison in NASA Giovanni (to be filled in by the owner)

Giovanni (https://giovanni.gsfc.nasa.gov/) can produce an area-averaged monthly time series from the
same MERRA-2 collection. This checks our averaging and trend from a separate NASA tool. Like the POWER
check, it is not independent of MERRA-2. Repeat it with a non-MERRA-2 temperature product if Giovanni
offers one.

Checklist:
- [ ] Service: "Time Series, Area-Averaged".
- [ ] Variable: MERRA-2 `T2M` from M2TMNXSLV v5.12.4 (2-meter air temperature, monthly).
- [ ] Region box, exactly as exported (west, south, east, north):
  - Western Europe: `-10, 42, 15, 60`
  - Sahel: `-18, 10, 40, 20`
- [ ] Period: 2001-01 to 2025-09.
- [ ] Download the CSV. Giovanni's area average weights by cell area; note what the plot says.
- [ ] Remove the monthly climatology (mean of each calendar month over 2001-01 to 2025-09).
- [ ] Fit the trend: Sen's slope per decade (trendkit `trend_report(values, dates)` does this), and
  also an OLS slope.
- [ ] Note any difference in box edges: Giovanni clips at the box edge, while we use whole 2-degree cells
  whose centers are inside the box.

| Region | Box | Period | Giovanni slope (°C/decade) | Giovanni OLS | EcoDelta slope | EcoDelta 95% CI | Difference | Notes |
|---|---|---|---|---|---|---|---|---|
| Western Europe | -10, 42, 15, 60 | 2001-01 to 2025-09 | | | +0.528 | +0.313 to +0.734 | | |
| Sahel | -18, 10, 40, 20 | 2001-01 to 2025-09 | | | −0.204 | −0.377 to −0.036 | | |

## Sources

- GISTEMP Team, 2026: GISS Surface Temperature Analysis (GISTEMP), version 4. NASA Goddard Institute
  for Space Studies. Dataset accessed 2026-11-14 at https://data.giss.nasa.gov/gistemp/. Files
  `tabledata_v4/GLB.Ts+dSST.csv` and `tabledata_v4/ZonAnn.Ts+dSST.csv`, land GHCN v4 + ocean ERSST v5.
- Lenssen, N., G.A. Schmidt, M. Hendrickson, P. Jacobs, M. Menne, and R. Ruedy, 2024: A GISTEMPv4
  observational uncertainty ensemble. J. Geophys. Res. Atmos., 129, e2023JD040179,
  doi:10.1029/2023JD040179.
- Simmons, A., P. Berrisford, D. Dee, H. Hersbach, S. Hirahara and J.-N. Thépaut, 2016: Estimates of
  variations and trends of global surface temperature. ECMWF ERA Report Series 25.
  https://www.ecmwf.int/sites/default/files/elibrary/2016/16437-estimates-variations-and-trends-global-surface-temperature.pdf
- NASA POWER Monthly and Annual API v2.10.0, regional endpoint, accessed 2026-11-14,
  https://power.larc.nasa.gov/api/temporal/monthly/regional. The source is from its response header.
  The POWER documentation pages returned HTTP 404 on 2026-11-14.
- Guichard et al., chapter using CRU TS3.10, https://books.openedition.org/irdeditions/12319 (warming
  across the Sahel strip; no trend value for 2001-2025).
