# Validation of the real export

Status on 2026-11-15: all five variables are downloaded (297 months, 2001-01 to 2025-09). The real
export `web_data/` (schema 1.3.0, `meta.synthetic: false`) contains `precip`, `evap`, `runoff_surface`
and `soil_moisture_0_10cm`, each region result with a quality status from the owner-approved gate
(section 7). `t2m` stays held (`hold:` in `data/catalog/variables.yaml`). Every number below was
produced by the command named next to it. Nothing was typed from memory.

Sections 1 to 3 were written on 2026-11-14 for `t2m`. Sections 4 to 7 were added on 2026-11-15.

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

## 4. Pipeline checks for `precip` (GPM IMERG Final, monthly, V07)

| Check | Result | PASS / FAIL |
|---|---|---|
| Units | Source `precipitation` units `mm/hr` (in `manifest.json`, read from the source file); exported `mm day-1` (x 24) | PASS |
| Series | 2001-01 to 2025-09, 297 consecutive months | PASS |
| NaN pattern | `nan_fraction` 0.0 in the processed file. Native IMERG cells are missing only at abs(lat) >= 89.25; the 2-degree rows at +-89 keep a value | PASS |
| Cells per region | All 21 regions: every box cell in the fixed mask, 297 valid months; lowest monthly weight share 0.9962 (Antarctica), all others >= 0.9997 | PASS |
| Regridded vs raw global mean | 2001-01 2.5985 -> 2.5983 mm/day (−1.53e-04), 2013-07 −8.59e-05, 2025-09 −1.37e-04; valid-area-weighted difference at most 4.4e-16 (method is exact); processed file 2.5983, 2.8757, 2.8174 | PASS |
| `validate --source real` | 0 schema errors, 0 consistency errors, 0 mismatches | PASS |
| Reference | GPCP v3.3 monthly (`GPCPMON`, DOI 10.5067/MEASURES/GPCP/DATA306, variable `sat_gauge_precip`). **Not independent:** the IMERG V07 collection abstract says the Final run is adjusted with GPCP. The GPCP abstract says the product is paused at 2024-09, but CMR listed 297 granules and every month 2024-10..2025-09 has 16,200 valid cells (global means 2.43 to 2.69 mm/day) | related product only |

Commands: regridding check `.venv/bin/python -I ../EcoDelta/ecodelta-engine/scripts/quality/check_regrid.py IMERG precip`
(from `nasa-data/`); reference fetch `nasa-data/scripts/fetch_reference.py`; comparison
`scripts/quality/vs_reference.py precip <nasa-data>/data/interim/GPCP precip data/quality/precip_vs_gpcp.json`.

## 5. Pipeline checks for `evap`, `runoff_surface`, `soil_moisture_0_10cm` (GLDAS Noah 2.1 monthly)

| Check | Result | PASS / FAIL |
|---|---|---|
| Units | From the source files (in `manifest.json`): `Evap_tavg` kg m-2 s-1 -> mm day-1 (x 86400); `Qs_acc` kg m-2 per 3 h (file attribute "past 3-hour accumulation") -> mm day-1 (x 8); `SoilMoi0_10cm_inst` kg m-2 kept | PASS |
| Series | 2001-01 to 2025-09, 297 consecutive months, all three | PASS |
| NaN pattern | Land only, 60S to 90N (native grid lat −59.875 to 89.875). 3,799 valid 2-degree cells in every month (`nan_fraction` 0.7655, the ocean, Antarctica and cells with < 50% land). The valid set never changes: every region's fixed-mask weight share is 1.0 in every month | PASS |
| Cells per region | 20 regions have cells (for example Sahel 139 of 145, Amazon 179 of 198, Southeast Asia 120 of 500, Arctic 551 of 2160). **Antarctica: 0 cells** (outside GLDAS coverage) | PASS (Antarctica: no data) |
| Regridded vs raw global mean | Valid-area-weighted difference 0 (largest −2.2e-16), so the averaging is exact. With the 50% land rule, coastal cells drop out and the global land mean moves by up to 1.7% (evap 2001-01: 1.1062 -> 1.0879 mm/day; soil moisture 2025-09: 22.3374 -> 22.2981 kg m-2). The processed files give the same values (evap 1.0879, 2.2330, 1.6335) | PASS (coastline effect documented) |
| `validate --source real` | 0 errors (see section 7) | PASS |
| Reference | CMR search (`evapotranspiration / soil moisture / runoff monthly global`, 2001-01..2025-09) found no observational product covering the whole period on the same NASA service: AMSR-E soil moisture covers 2002-10..2011-09, GRACE gives total water storage, and MODIS MOD16 is 8-day 500 m. Used instead: MERRA-2 land `M2TMNXLND` v5.12.4 (`EVLAND`, `RUNOFF` = "overland_runoff_including_throughflow", `SFMC` = "water_surface_layer" in m-3 m-3). **Another model with other forcing, not independent** | other model only |

Command: `.venv/bin/python -I ../EcoDelta/ecodelta-engine/scripts/quality/check_regrid.py GLDAS evap runoff_surface soil_moisture_0_10cm` (from `nasa-data/`).

## 6. `t2m` investigation (hypotheses, not conclusions)

**6a. MERRA-2 production streams.** From CMR granule names (`scripts/quality/merra_streams.py`, run with
the nasa-data venv; output `data/quality/merra_granules.json`): stream 300 covers 2001-01..2010-12;
stream 400 covers 2011-01..2025-09 except 2020-09 and 2021-06..2021-09, which are stream 401
(reprocessed; DMR attribute "Re-processed file generated: Wed Nov 4 2020"). Segment trends
(`scripts/quality/t2m_segments.py data/quality/t2m_segments.json`), °C/decade with 95% CI; the step
is an OLS coefficient on [1, t, t >= 2011-01], descriptive only (no p-value, since OLS ignores
autocorrelation):

| Region | 2001-01..2025-09 | 2001-2010 (stream 300) | 2011-2025 (streams 400/401) | OLS step at 2011-01 |
|---|---|---|---|---|
| global | +0.163 [+0.057, +0.271] | -0.118 [-0.250, +0.015] | +0.428 [+0.255, +0.605] | -0.215 |
| mexico | +0.422 [+0.320, +0.523] | -0.165 [-0.504, +0.171] | +0.494 [+0.269, +0.730] | +0.177 |
| central_america_caribbean | +0.293 [+0.158, +0.440] | +0.182 [-0.195, +0.557] | +0.591 [+0.297, +0.897] | -0.339 |
| amazon_basin | +0.406 [+0.139, +0.690] | +0.174 [-0.422, +0.812] | +0.702 [-0.032, +1.476] | -0.308 |
| southern_south_america | +0.231 [+0.113, +0.345] | -0.159 [-0.513, +0.222] | +0.389 [+0.124, +0.643] | -0.035 |
| western_us | +0.336 [+0.142, +0.531] | -0.902 [-1.482, -0.323] | +0.535 [+0.103, +0.960] | +0.304 |
| eastern_us | +0.429 [+0.241, +0.619] | -0.195 [-0.811, +0.435] | +0.638 [+0.210, +1.025] | +0.043 |
| western_europe | +0.528 [+0.313, +0.734] | -0.567 [-1.414, +0.348] | +0.923 [+0.537, +1.298] | -0.132 |
| mediterranean | +0.571 [+0.422, +0.718] | +0.268 [-0.276, +0.778] | +0.976 [+0.695, +1.273] | -0.399 |
| sahel | -0.204 [-0.377, -0.036] | -0.198 [-0.901, +0.479] | +0.131 [-0.207, +0.462] | -0.463 |
| central_africa | -0.149 [-0.410, +0.118] | -0.456 [-1.282, +0.560] | +0.513 [+0.109, +0.922] | -0.778 |
| east_africa | -0.004 [-0.120, +0.110] | -0.076 [-0.376, +0.221] | +0.163 [-0.138, +0.456] | -0.164 |
| southern_africa | +0.156 [+0.014, +0.306] | -0.197 [-0.671, +0.287] | +0.501 [+0.209, +0.799] | -0.276 |
| middle_east | +0.265 [+0.137, +0.389] | +0.246 [-0.182, +0.678] | +0.541 [+0.270, +0.825] | -0.482 |
| indian_subcontinent | +0.066 [-0.047, +0.181] | -0.022 [-0.328, +0.305] | +0.285 [+0.000, +0.576] | -0.249 |
| southeast_asia | +0.224 [+0.149, +0.302] | +0.155 [-0.071, +0.355] | +0.447 [+0.273, +0.622] | -0.256 |
| east_china | +0.417 [+0.287, +0.548] | -0.126 [-0.611, +0.336] | +0.886 [+0.624, +1.153] | -0.440 |
| siberia | +0.285 [+0.051, +0.533] | -0.238 [-1.258, +0.764] | +0.381 [-0.117, +0.917] | +0.205 |
| arctic | +0.349 [+0.178, +0.524] | +0.073 [-0.464, +0.676] | +0.315 [-0.090, +0.721] | +0.116 |
| australia | +0.271 [+0.134, +0.413] | -0.113 [-0.545, +0.320] | +0.556 [+0.218, +0.874] | -0.206 |
| antarctica | -0.273 [-0.502, -0.053] | -1.638 [-2.370, -0.979] | +0.536 [+0.179, +0.881] | -0.543 |

The step at 2011-01 is negative in 16 of 21 regions. 2010 to 2011 was also a real El Niño to La Niña
change, so this is a hypothesis: a stream change could explain part of it, but it is not shown.

**6b. GLDAS air temperature.** The GLDAS 2.1 granule attribute `source` says "Noah_v3.6 forced with
GDAS-AGRMET-GPCPv13rA1"; `Tair_f_inst` is the forcing air temperature (K, NOAA GDAS). MERRA-2 vs
GLDAS `Tair_f_inst` on the same cells (`scripts/quality/vs_reference.py t2m <nasa-data>/data/interim/GLDAS_TAIR tair data/quality/t2m_vs_gldas.json`):

| Region | MERRA-2, same cells | GLDAS Tair | D | p(D) | r |
|---|---|---|---|---|---|
| global | +0.214 [+0.099, +0.338] | +0.617 [+0.484, +0.748] | -0.361 [-0.744, -0.043] | 3.1e-02 | 0.74 |
| mexico | +0.474 [+0.306, +0.645] | +0.690 [+0.544, +0.839] | -0.213 [-0.478, +0.020] | 7.1e-02 | 0.90 |
| central_america_caribbean | +0.345 [+0.105, +0.596] | +0.406 [+0.218, +0.593] | -0.048 [-0.402, +0.269] | 7.5e-01 | 0.69 |
| amazon_basin | +0.426 [+0.144, +0.725] | +0.373 [+0.149, +0.613] | +0.133 [-0.141, +0.396] | 3.2e-01 | 0.79 |
| southern_south_america | +0.301 [+0.150, +0.456] | +0.747 [+0.573, +0.915] | -0.384 [-0.663, -0.171] | 1.8e-03 | 0.86 |
| western_us | +0.336 [+0.118, +0.556] | +0.666 [+0.439, +0.889] | -0.280 [-0.492, -0.074] | 7.9e-03 | 0.94 |
| eastern_us | +0.390 [+0.120, +0.663] | +0.311 [+0.061, +0.580] | +0.044 [-0.070, +0.150] | 4.3e-01 | 0.98 |
| western_europe | +0.645 [+0.395, +0.886] | +0.641 [+0.385, +0.893] | +0.004 [-0.073, +0.081] | 9.1e-01 | 0.99 |
| mediterranean | +0.601 [+0.427, +0.776] | +1.019 [+0.862, +1.179] | -0.455 [-0.792, -0.136] | 8.8e-03 | 0.91 |
| sahel | -0.214 [-0.393, -0.039] | +0.885 [+0.623, +1.159] | -1.108 [-1.653, -0.592] | 9.8e-04 | 0.36 |
| central_africa | -0.195 [-0.479, +0.096] | +0.456 [+0.238, +0.690] | -0.653 [-1.460, +0.096] | 8.1e-02 | 0.09 |
| east_africa | -0.127 [-0.265, +0.011] | +0.927 [+0.719, +1.148] | -1.051 [-1.433, -0.676] | 2.7e-05 | 0.06 |
| southern_africa | +0.189 [-0.024, +0.409] | +0.860 [+0.667, +1.058] | -0.603 [-1.117, -0.137] | 1.5e-02 | 0.62 |
| middle_east | +0.271 [+0.124, +0.412] | +1.101 [+0.887, +1.332] | -0.879 [-1.468, -0.333] | 7.5e-03 | 0.74 |
| indian_subcontinent | -0.032 [-0.194, +0.127] | +0.981 [+0.734, +1.226] | -0.923 [-1.290, -0.556] | 1.1e-05 | 0.55 |
| southeast_asia | +0.133 [+0.038, +0.228] | +0.376 [+0.260, +0.499] | -0.253 [-0.518, -0.005] | 4.6e-02 | 0.75 |
| east_china | +0.424 [+0.277, +0.574] | +0.765 [+0.609, +0.913] | -0.345 [-0.488, -0.213] | 1.4e-06 | 0.94 |
| siberia | +0.295 [-0.003, +0.601] | +0.303 [-0.020, +0.628] | +0.084 [-0.173, +0.363] | 5.3e-01 | 0.94 |
| arctic | +0.258 [+0.071, +0.441] | +0.133 [-0.096, +0.354] | +0.108 [-0.178, +0.421] | 4.5e-01 | 0.84 |
| australia | +0.339 [+0.101, +0.586] | +0.785 [+0.552, +1.018] | -0.434 [-0.768, -0.129] | 8.1e-03 | 0.86 |
| antarctica | n/a | n/a | n/a |  |  |

Low correlations in Africa (Central Africa r 0.09) and large steps make GLDAS `Tair` a weak trend
reference; it is not used by the gate.

**6c. GISTEMP v4 gridded** (`gistemp250_GHCNv4.nc` land only, and `gistemp1200_GHCNv4_ERSSTv5.nc`,
both on the same 2-degree grid; retrieval time in `nasa-data/data/reference/gistemp/retrieved_utc.txt`).
Command: `scripts/quality/t2m_vs_gistemp.py data/quality/t2m_vs_gistemp.json`. The 250 km land-only
comparison is the `t2m` table in section 7. GISTEMP 1200 mixes sea surface temperature into ocean
cells, so only land-dominated boxes compare like with like; its results are in the same JSON file.
In the Sahel, on the same cells, MERRA-2 shows no clear trend while GISTEMP 250 land warms
(D −0.379 °C/decade, p 6.9e-07). GISTEMP 250 covers only 57% of the Sahel box, 32% of Central Africa
and 38% of East Africa.

## 7. Quality gate v1 (owner-approved 2026-11-15, G4 on)

The rule was written before the GLDAS vs MERRA-2 land comparison was run, but **after** the `t2m` and
`precip` comparison tables had been seen. The full rule text is in `data/catalog/quality_gate.json`
and in `meta.quality_gate.rule`. In short: per (variable, region), compare with a fixed primary
reference on the same cells (trendkit on each, D test at alpha 0.05). The verdicts differ and D is
significant: **held**. The verdicts differ but D is not significant, or the verdicts agree and D is
significant: **limited**. They agree and D is not significant: **published**. A pair is at most
limited when the reference covers < 50% of the region, or (G4) when the reference is not independent.
A region comparison gets the worse status of its two regions. Held pairs are not exported as results:
they are listed in `meta.quality_gate.held`, `regions/<id>.json` `held`, and
`compare/<variable>.json` `held_pairs`.

Commands (from `ecodelta-engine/`, `ECODELTA_DATA_DIR` set): the comparison scripts above write
`data/quality/*.json`; `.venv/bin/python -I scripts/quality/gate.py --write` writes
`data/catalog/quality_gate.json`; then `build --source real --allow-missing` and `validate --source real`.

Result of `validate --source real` on 2026-11-15: 53 files, 0 schema errors, 0 consistency errors,
292 difference series rebuilt with 0 mismatches, 161 golden numbers with 0 mismatches.

Status counts (published / limited / held): `precip` 0 / 17 / 4, `evap` 0 / 14 / 7, `runoff_surface`
0 / 11 / 10, `soil_moisture_0_10cm` 0 / 5 / 16, and `t2m` (not exported, held by owner decision)
7 / 10 / 4. **Nothing is "published"** among the exported variables, because none has an independent
reference.

Limits of the gate:
- There are 105 D tests at alpha 0.05, so about 5% flag a difference by chance. This pushes towards
  holding.
- Soil moisture is compared by verdict only: GLDAS 0-10 cm kg m-2 against the MERRA-2 surface layer in m-3 m-3.
- MERRA-2 land `RUNOFF` includes throughflow and GLDAS `Qs` does not.
- The gate covers regional results only; the trend maps (`grids/`) are still exported for every
  cell.
- MERRA-2 land shares the MERRA-2 stream changes of section 6a.

#### `evap` vs MERRA-2 land EVLAND (not independent)

| Region | Product, same cells | Reference | D = product - reference | p(D) | r | Status | Reason |
|---|---|---|---|---|---|---|---|
| amazon_basin | +0.108 [+0.011, +0.215] | -0.210 [-0.301, -0.119] | +0.369 [+0.187, +0.528] | 3.4e-04 | -0.07 | held | disagrees with MERRA-2 land EVLAND: product increasing, reference decreasing; MERRA-2 land EVLAND is not independent of the product |
| antarctica | n/a | n/a | n/a |  |  | held | no data in this region |
| arctic | +0.026 [+0.007, +0.046] | +0.002 [-0.001, +0.006] | +0.022 [+0.007, +0.039] | 6.1e-03 | 0.23 | held | disagrees with MERRA-2 land EVLAND: product increasing, reference no clear trend; MERRA-2 land EVLAND is not independent of the product |
| australia | +0.025 [-0.041, +0.094] | -0.108 [-0.234, +0.018] | +0.121 [+0.078, +0.166] | 6.1e-07 | 0.76 | limited | direction agrees with MERRA-2 land EVLAND (no clear trend); size differs by +0.121/decade; MERRA-2 land EVLAND is not independent of the product |
| central_africa | +0.138 [+0.065, +0.212] | +0.089 [-0.024, +0.203] | +0.039 [-0.086, +0.163] | 5.4e-01 | 0.32 | limited | verdict differs from MERRA-2 land EVLAND (increasing vs no clear trend), difference not significant; MERRA-2 land EVLAND is not independent of the product |
| central_america_caribbean | +0.111 [+0.008, +0.218] | +0.098 [-0.014, +0.208] | -0.000 [-0.096, +0.095] | 9.9e-01 | 0.55 | limited | verdict differs from MERRA-2 land EVLAND (increasing vs no clear trend), difference not significant; MERRA-2 land EVLAND is not independent of the product |
| east_africa | +0.055 [+0.001, +0.112] | +0.282 [+0.179, +0.392] | -0.222 [-0.297, -0.152] | 4.3e-08 | 0.69 | limited | direction agrees with MERRA-2 land EVLAND (increasing); size differs by -0.222/decade; MERRA-2 land EVLAND is not independent of the product |
| east_china | +0.098 [+0.069, +0.127] | +0.133 [+0.093, +0.175] | -0.021 [-0.060, +0.018] | 2.8e-01 | 0.65 | limited | agrees with MERRA-2 land EVLAND (increasing); MERRA-2 land EVLAND is not independent of the product |
| eastern_us | +0.073 [+0.024, +0.122] | +0.014 [-0.033, +0.060] | +0.060 [+0.019, +0.100] | 5.8e-03 | 0.63 | held | disagrees with MERRA-2 land EVLAND: product increasing, reference no clear trend; MERRA-2 land EVLAND is not independent of the product |
| global | +0.058 [+0.034, +0.083] | +0.038 [+0.022, +0.054] | +0.024 [-0.007, +0.055] | 1.2e-01 | 0.52 | limited | agrees with MERRA-2 land EVLAND (increasing); MERRA-2 land EVLAND is not independent of the product |
| indian_subcontinent | +0.123 [+0.068, +0.184] | +0.180 [+0.115, +0.247] | -0.053 [-0.099, -0.003] | 3.7e-02 | 0.79 | limited | direction agrees with MERRA-2 land EVLAND (increasing); size differs by -0.053/decade; MERRA-2 land EVLAND is not independent of the product |
| mediterranean | -0.006 [-0.033, +0.021] | -0.001 [-0.045, +0.040] | -0.009 [-0.032, +0.013] | 4.2e-01 | 0.76 | limited | agrees with MERRA-2 land EVLAND (no clear trend); MERRA-2 land EVLAND is not independent of the product |
| mexico | -0.010 [-0.078, +0.061] | +0.010 [-0.077, +0.094] | -0.017 [-0.055, +0.021] | 3.8e-01 | 0.84 | limited | agrees with MERRA-2 land EVLAND (no clear trend); MERRA-2 land EVLAND is not independent of the product |
| middle_east | +0.019 [-0.001, +0.039] | +0.079 [+0.045, +0.115] | -0.070 [-0.085, -0.054] | 2.4e-13 | 0.67 | held | disagrees with MERRA-2 land EVLAND: product no clear trend, reference increasing; MERRA-2 land EVLAND is not independent of the product |
| sahel | +0.045 [+0.015, +0.086] | +0.190 [+0.119, +0.270] | -0.116 [-0.179, -0.061] | 4.7e-05 | 0.53 | limited | direction agrees with MERRA-2 land EVLAND (increasing); size differs by -0.116/decade; MERRA-2 land EVLAND is not independent of the product |
| siberia | +0.065 [+0.038, +0.093] | +0.016 [+0.007, +0.027] | +0.039 [+0.014, +0.063] | 2.6e-03 | 0.47 | limited | direction agrees with MERRA-2 land EVLAND (increasing); size differs by +0.039/decade; MERRA-2 land EVLAND is not independent of the product |
| southeast_asia | +0.172 [+0.104, +0.242] | +0.187 [+0.135, +0.241] | -0.011 [-0.090, +0.068] | 7.7e-01 | 0.60 | limited | agrees with MERRA-2 land EVLAND (increasing); MERRA-2 land EVLAND is not independent of the product |
| southern_africa | -0.076 [-0.148, -0.005] | +0.031 [-0.082, +0.141] | -0.095 [-0.168, -0.014] | 2.4e-02 | 0.59 | held | disagrees with MERRA-2 land EVLAND: product decreasing, reference no clear trend; MERRA-2 land EVLAND is not independent of the product |
| southern_south_america | -0.031 [-0.094, +0.030] | -0.100 [-0.171, -0.035] | +0.076 [+0.042, +0.111] | 2.2e-05 | 0.78 | held | disagrees with MERRA-2 land EVLAND: product no clear trend, reference decreasing; MERRA-2 land EVLAND is not independent of the product |
| western_europe | +0.048 [+0.016, +0.079] | +0.037 [+0.003, +0.071] | +0.019 [-0.014, +0.049] | 2.5e-01 | 0.72 | limited | agrees with MERRA-2 land EVLAND (increasing); MERRA-2 land EVLAND is not independent of the product |
| western_us | +0.036 [+0.001, +0.069] | +0.006 [-0.046, +0.060] | +0.021 [-0.005, +0.047] | 1.1e-01 | 0.78 | limited | verdict differs from MERRA-2 land EVLAND (increasing vs no clear trend), difference not significant; MERRA-2 land EVLAND is not independent of the product |

#### `precip` vs GPCP v3.3 (not independent)

| Region | Product, same cells | Reference | D = product - reference | p(D) | r | Status | Reason |
|---|---|---|---|---|---|---|---|
| amazon_basin | -0.172 [-0.313, -0.025] | -0.178 [-0.318, -0.032] | +0.001 [-0.010, +0.013] | 8.1e-01 | 1.00 | limited | agrees with GPCP v3.3 (decreasing); GPCP v3.3 is not independent of the product |
| antarctica | +0.163 [+0.134, +0.192] | -0.019 [-0.045, +0.006] | +0.182 [+0.139, +0.226] | 7.6e-12 | 0.01 | held | disagrees with GPCP v3.3: product increasing, reference no clear trend; GPCP v3.3 is not independent of the product |
| arctic | +0.028 [+0.006, +0.049] | +0.036 [+0.009, +0.063] | -0.012 [-0.037, +0.012] | 3.3e-01 | 0.56 | limited | agrees with GPCP v3.3 (increasing); GPCP v3.3 is not independent of the product |
| australia | +0.058 [-0.041, +0.158] | +0.059 [-0.037, +0.156] | +0.000 [-0.019, +0.020] | 9.9e-01 | 0.99 | limited | agrees with GPCP v3.3 (no clear trend); GPCP v3.3 is not independent of the product |
| central_africa | -0.053 [-0.119, +0.013] | -0.079 [-0.143, -0.016] | +0.031 [+0.015, +0.049] | 1.3e-04 | 0.97 | held | disagrees with GPCP v3.3: product no clear trend, reference decreasing; GPCP v3.3 is not independent of the product |
| central_america_caribbean | -0.043 [-0.205, +0.109] | +0.017 [-0.157, +0.184] | -0.074 [-0.122, -0.025] | 3.5e-03 | 0.96 | limited | direction agrees with GPCP v3.3 (no clear trend); size differs by -0.074/decade; GPCP v3.3 is not independent of the product |
| east_africa | +0.045 [-0.074, +0.173] | +0.094 [-0.034, +0.225] | -0.043 [-0.059, -0.028] | 2.9e-07 | 0.99 | limited | direction agrees with GPCP v3.3 (no clear trend); size differs by -0.043/decade; GPCP v3.3 is not independent of the product |
| east_china | +0.234 [+0.104, +0.363] | +0.186 [+0.064, +0.312] | +0.033 [+0.011, +0.056] | 3.7e-03 | 0.97 | limited | direction agrees with GPCP v3.3 (increasing); size differs by +0.033/decade; GPCP v3.3 is not independent of the product |
| eastern_us | +0.030 [-0.046, +0.109] | +0.015 [-0.059, +0.091] | +0.012 [-0.022, +0.046] | 4.9e-01 | 0.94 | limited | agrees with GPCP v3.3 (no clear trend); GPCP v3.3 is not independent of the product |
| global | +0.030 [+0.014, +0.046] | +0.014 [-0.007, +0.035] | +0.010 [-0.014, +0.033] | 4.1e-01 | 0.50 | limited | verdict differs from GPCP v3.3 (increasing vs no clear trend), difference not significant; GPCP v3.3 is not independent of the product |
| indian_subcontinent | +0.173 [+0.044, +0.299] | +0.201 [+0.076, +0.323] | -0.035 [-0.064, -0.006] | 1.8e-02 | 0.97 | limited | direction agrees with GPCP v3.3 (increasing); size differs by -0.035/decade; GPCP v3.3 is not independent of the product |
| mediterranean | -0.061 [-0.127, +0.003] | -0.080 [-0.145, -0.014] | +0.017 [+0.003, +0.031] | 1.5e-02 | 0.98 | held | disagrees with GPCP v3.3: product no clear trend, reference decreasing; GPCP v3.3 is not independent of the product |
| mexico | +0.020 [-0.092, +0.129] | +0.012 [-0.106, +0.121] | +0.011 [-0.016, +0.040] | 4.1e-01 | 0.96 | limited | agrees with GPCP v3.3 (no clear trend); GPCP v3.3 is not independent of the product |
| middle_east | +0.007 [-0.033, +0.047] | +0.015 [-0.029, +0.056] | -0.006 [-0.010, -0.001] | 9.8e-03 | 0.98 | limited | direction agrees with GPCP v3.3 (no clear trend); size differs by -0.006/decade; GPCP v3.3 is not independent of the product |
| sahel | +0.014 [-0.005, +0.040] | +0.014 [-0.006, +0.041] | +0.004 [+0.000, +0.008] | 3.8e-02 | 0.99 | limited | direction agrees with GPCP v3.3 (no clear trend); size differs by +0.004/decade; GPCP v3.3 is not independent of the product |
| siberia | +0.061 [+0.032, +0.090] | +0.056 [+0.028, +0.083] | +0.000 [-0.013, +0.013] | 9.9e-01 | 0.91 | limited | agrees with GPCP v3.3 (increasing); GPCP v3.3 is not independent of the product |
| southeast_asia | +0.361 [+0.077, +0.627] | +0.285 [+0.031, +0.552] | +0.041 [-0.003, +0.088] | 7.0e-02 | 0.98 | limited | agrees with GPCP v3.3 (increasing); GPCP v3.3 is not independent of the product |
| southern_africa | -0.091 [-0.166, -0.019] | -0.080 [-0.152, -0.006] | -0.012 [-0.030, +0.005] | 1.6e-01 | 0.97 | limited | agrees with GPCP v3.3 (decreasing); GPCP v3.3 is not independent of the product |
| southern_south_america | -0.038 [-0.124, +0.047] | -0.118 [-0.196, -0.037] | +0.076 [+0.056, +0.096] | 5.3e-12 | 0.96 | held | disagrees with GPCP v3.3: product no clear trend, reference decreasing; GPCP v3.3 is not independent of the product |
| western_europe | +0.026 [-0.113, +0.156] | +0.017 [-0.104, +0.136] | +0.001 [-0.031, +0.036] | 9.5e-01 | 0.97 | limited | agrees with GPCP v3.3 (no clear trend); GPCP v3.3 is not independent of the product |
| western_us | -0.013 [-0.071, +0.046] | -0.008 [-0.067, +0.051] | -0.007 [-0.014, +0.000] | 6.3e-02 | 0.99 | limited | agrees with GPCP v3.3 (no clear trend); GPCP v3.3 is not independent of the product |

#### `runoff_surface` vs MERRA-2 land RUNOFF (not independent)

| Region | Product, same cells | Reference | D = product - reference | p(D) | r | Status | Reason |
|---|---|---|---|---|---|---|---|
| amazon_basin | +0.005 [-0.035, +0.043] | -0.148 [-0.258, -0.039] | +0.149 [+0.046, +0.252] | 6.6e-03 | 0.48 | held | disagrees with MERRA-2 land RUNOFF: product no clear trend, reference decreasing; MERRA-2 land RUNOFF is not independent of the product |
| antarctica | n/a | n/a | n/a |  |  | held | no data in this region |
| arctic | +0.008 [-0.001, +0.019] | +0.012 [+0.001, +0.023] | -0.000 [-0.017, +0.015] | 9.5e-01 | 0.65 | limited | verdict differs from MERRA-2 land RUNOFF (no clear trend vs increasing), difference not significant; MERRA-2 land RUNOFF is not independent of the product |
| australia | +0.002 [-0.002, +0.005] | -0.019 [-0.041, -0.000] | +0.020 [+0.005, +0.038] | 9.7e-03 | 0.88 | held | disagrees with MERRA-2 land RUNOFF: product no clear trend, reference decreasing; MERRA-2 land RUNOFF is not independent of the product |
| central_africa | +0.019 [+0.010, +0.027] | +0.140 [+0.076, +0.206] | -0.120 [-0.179, -0.063] | 7.1e-05 | 0.42 | limited | direction agrees with MERRA-2 land RUNOFF (increasing); size differs by -0.120/decade; MERRA-2 land RUNOFF is not independent of the product |
| central_america_caribbean | +0.038 [+0.013, +0.064] | +0.290 [+0.189, +0.404] | -0.251 [-0.352, -0.158] | 2.3e-09 | 0.62 | limited | direction agrees with MERRA-2 land RUNOFF (increasing); size differs by -0.251/decade; MERRA-2 land RUNOFF is not independent of the product |
| east_africa | +0.006 [+0.000, +0.011] | +0.196 [+0.154, +0.243] | -0.187 [-0.231, -0.147] | 2.8e-17 | 0.44 | limited | direction agrees with MERRA-2 land RUNOFF (increasing); size differs by -0.187/decade; MERRA-2 land RUNOFF is not independent of the product |
| east_china | +0.035 [+0.021, +0.052] | +0.119 [+0.053, +0.196] | -0.077 [-0.142, -0.026] | 1.8e-03 | 0.80 | limited | direction agrees with MERRA-2 land RUNOFF (increasing); size differs by -0.077/decade; MERRA-2 land RUNOFF is not independent of the product |
| eastern_us | -0.000 [-0.008, +0.008] | +0.008 [-0.021, +0.038] | -0.009 [-0.037, +0.017] | 4.8e-01 | 0.53 | limited | agrees with MERRA-2 land RUNOFF (no clear trend); MERRA-2 land RUNOFF is not independent of the product |
| global | +0.003 [-0.001, +0.008] | +0.069 [+0.040, +0.098] | -0.066 [-0.098, -0.036] | 9.5e-05 | 0.24 | held | disagrees with MERRA-2 land RUNOFF: product no clear trend, reference increasing; MERRA-2 land RUNOFF is not independent of the product |
| indian_subcontinent | +0.005 [-0.003, +0.012] | +0.114 [+0.065, +0.176] | -0.120 [-0.178, -0.070] | 2.3e-08 | 0.66 | held | disagrees with MERRA-2 land RUNOFF: product no clear trend, reference increasing; MERRA-2 land RUNOFF is not independent of the product |
| mediterranean | -0.003 [-0.006, -0.000] | +0.006 [-0.011, +0.024] | -0.008 [-0.024, +0.006] | 2.4e-01 | 0.67 | limited | verdict differs from MERRA-2 land RUNOFF (decreasing vs no clear trend), difference not significant; MERRA-2 land RUNOFF is not independent of the product |
| mexico | -0.004 [-0.010, +0.002] | +0.050 [+0.015, +0.087] | -0.052 [-0.085, -0.020] | 1.9e-03 | 0.68 | held | disagrees with MERRA-2 land RUNOFF: product no clear trend, reference increasing; MERRA-2 land RUNOFF is not independent of the product |
| middle_east | +0.001 [-0.001, +0.002] | +0.024 [+0.017, +0.030] | -0.022 [-0.028, -0.017] | 1.4e-15 | 0.29 | held | disagrees with MERRA-2 land RUNOFF: product no clear trend, reference increasing; MERRA-2 land RUNOFF is not independent of the product |
| sahel | +0.001 [+0.000, +0.002] | +0.084 [+0.033, +0.159] | -0.081 [-0.155, -0.031] | 3.6e-06 | 0.43 | limited | direction agrees with MERRA-2 land RUNOFF (increasing); size differs by -0.081/decade; MERRA-2 land RUNOFF is not independent of the product |
| siberia | +0.000 [-0.007, +0.007] | +0.017 [+0.008, +0.030] | -0.016 [-0.030, -0.005] | 3.3e-03 | 0.68 | held | disagrees with MERRA-2 land RUNOFF: product no clear trend, reference increasing; MERRA-2 land RUNOFF is not independent of the product |
| southeast_asia | +0.059 [+0.036, +0.082] | +0.434 [+0.210, +0.654] | -0.372 [-0.569, -0.163] | 8.5e-04 | 0.74 | limited | direction agrees with MERRA-2 land RUNOFF (increasing); size differs by -0.372/decade; MERRA-2 land RUNOFF is not independent of the product |
| southern_africa | -0.001 [-0.002, -0.000] | +0.027 [+0.011, +0.053] | -0.030 [-0.057, -0.012] | 6.9e-05 | 0.17 | held | disagrees with MERRA-2 land RUNOFF: product decreasing, reference increasing; MERRA-2 land RUNOFF is not independent of the product |
| southern_south_america | -0.002 [-0.022, +0.019] | -0.056 [-0.095, -0.018] | +0.056 [+0.033, +0.080] | 5.1e-06 | 0.73 | held | disagrees with MERRA-2 land RUNOFF: product no clear trend, reference decreasing; MERRA-2 land RUNOFF is not independent of the product |
| western_europe | -0.005 [-0.011, +0.001] | +0.032 [-0.010, +0.075] | -0.038 [-0.078, +0.000] | 5.3e-02 | 0.60 | limited | agrees with MERRA-2 land RUNOFF (no clear trend); MERRA-2 land RUNOFF is not independent of the product |
| western_us | -0.000 [-0.003, +0.002] | +0.004 [-0.012, +0.020] | -0.003 [-0.017, +0.011] | 6.4e-01 | 0.72 | limited | agrees with MERRA-2 land RUNOFF (no clear trend); MERRA-2 land RUNOFF is not independent of the product |

#### `soil_moisture_0_10cm` vs MERRA-2 land SFMC (not independent)

| Region | Product, same cells | Reference | D = product - reference | p(D) | r | Status | Reason |
|---|---|---|---|---|---|---|---|
| amazon_basin | -0.587 [-1.001, -0.194] | -0.010 [-0.019, +0.000] | not comparable (units) |  | 0.83 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference no clear trend; MERRA-2 land SFMC is not independent of the product |
| antarctica | n/a | n/a | not comparable (units) |  |  | held | no data in this region |
| arctic | -0.560 [-0.959, -0.119] | +0.004 [-0.001, +0.011] | not comparable (units) |  | 0.08 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference no clear trend; MERRA-2 land SFMC is not independent of the product |
| australia | -0.515 [-1.142, +0.096] | -0.006 [-0.016, +0.004] | not comparable (units) |  | 0.87 | limited | direction agrees with MERRA-2 land SFMC (no clear trend); size not checkable (other units); MERRA-2 land SFMC is not independent of the product |
| central_africa | -0.417 [-0.624, -0.214] | +0.011 [-0.003, +0.024] | not comparable (units) |  | 0.08 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference no clear trend; MERRA-2 land SFMC is not independent of the product |
| central_america_caribbean | -0.557 [-1.078, -0.037] | +0.005 [-0.004, +0.014] | not comparable (units) |  | 0.55 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference no clear trend; MERRA-2 land SFMC is not independent of the product |
| east_africa | -0.604 [-1.010, -0.182] | +0.017 [+0.010, +0.023] | not comparable (units) |  | 0.46 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference increasing; MERRA-2 land SFMC is not independent of the product |
| east_china | +0.373 [-0.011, +0.758] | +0.009 [+0.004, +0.014] | not comparable (units) |  | 0.70 | held | disagrees with MERRA-2 land SFMC: product no clear trend, reference increasing; MERRA-2 land SFMC is not independent of the product |
| eastern_us | -0.644 [-1.055, -0.240] | -0.002 [-0.009, +0.005] | not comparable (units) |  | 0.70 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference no clear trend; MERRA-2 land SFMC is not independent of the product |
| global | -0.453 [-0.591, -0.326] | +0.004 [+0.001, +0.006] | not comparable (units) |  | -0.14 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference increasing; MERRA-2 land SFMC is not independent of the product |
| indian_subcontinent | +0.197 [-0.186, +0.587] | +0.016 [+0.009, +0.023] | not comparable (units) |  | 0.78 | held | disagrees with MERRA-2 land SFMC: product no clear trend, reference increasing; MERRA-2 land SFMC is not independent of the product |
| mediterranean | -0.851 [-1.189, -0.507] | -0.004 [-0.009, +0.002] | not comparable (units) |  | 0.79 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference no clear trend; MERRA-2 land SFMC is not independent of the product |
| mexico | -0.658 [-1.216, -0.097] | -0.003 [-0.011, +0.005] | not comparable (units) |  | 0.90 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference no clear trend; MERRA-2 land SFMC is not independent of the product |
| middle_east | -0.104 [-0.379, +0.156] | +0.008 [+0.004, +0.011] | not comparable (units) |  | 0.71 | held | disagrees with MERRA-2 land SFMC: product no clear trend, reference increasing; MERRA-2 land SFMC is not independent of the product |
| sahel | -0.152 [-0.332, +0.043] | +0.014 [+0.008, +0.021] | not comparable (units) |  | 0.29 | held | disagrees with MERRA-2 land SFMC: product no clear trend, reference increasing; MERRA-2 land SFMC is not independent of the product |
| siberia | -0.281 [-0.682, +0.124] | +0.006 [-0.001, +0.013] | not comparable (units) |  | 0.08 | limited | direction agrees with MERRA-2 land SFMC (no clear trend); size not checkable (other units); MERRA-2 land SFMC is not independent of the product |
| southeast_asia | -0.131 [-0.469, +0.202] | +0.012 [-0.004, +0.027] | not comparable (units) |  | 0.57 | limited | direction agrees with MERRA-2 land SFMC (no clear trend); size not checkable (other units); MERRA-2 land SFMC is not independent of the product |
| southern_africa | -1.370 [-1.863, -0.926] | +0.002 [-0.005, +0.008] | not comparable (units) |  | 0.59 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference no clear trend; MERRA-2 land SFMC is not independent of the product |
| southern_south_america | -1.145 [-1.588, -0.703] | -0.009 [-0.014, -0.002] | not comparable (units) |  | 0.89 | limited | direction agrees with MERRA-2 land SFMC (decreasing); size not checkable (other units); MERRA-2 land SFMC is not independent of the product |
| western_europe | -0.701 [-1.182, -0.225] | -0.001 [-0.007, +0.006] | not comparable (units) |  | 0.73 | held | disagrees with MERRA-2 land SFMC: product decreasing, reference no clear trend; MERRA-2 land SFMC is not independent of the product |
| western_us | -0.406 [-0.893, +0.068] | +0.001 [-0.006, +0.008] | not comparable (units) |  | 0.69 | limited | direction agrees with MERRA-2 land SFMC (no clear trend); size not checkable (other units); MERRA-2 land SFMC is not independent of the product |

#### `t2m` vs GISTEMP v4 250 km land (independent)

| Region | Product, same cells | Reference | D = product - reference | p(D) | r | Status | Reason |
|---|---|---|---|---|---|---|---|
| amazon_basin | +0.386 [+0.135, +0.653] | +0.306 [+0.167, +0.455] | +0.072 [-0.025, +0.172] | 1.4e-01 |  | published | agrees with GISTEMP v4 250 km land (increasing) |
| antarctica | -0.179 [-0.412, +0.060] | +0.103 [-0.175, +0.377] | -0.248 [-0.489, -0.014] | 3.8e-02 |  | limited | direction agrees with GISTEMP v4 250 km land (no clear trend); size differs by -0.248/decade; checked on 23% of the region |
| arctic | +0.287 [+0.125, +0.445] | +0.645 [+0.462, +0.831] | -0.327 [-0.502, -0.182] | 5.5e-06 |  | limited | direction agrees with GISTEMP v4 250 km land (increasing); size differs by -0.327/decade |
| australia | +0.296 [+0.139, +0.461] | +0.258 [+0.118, +0.400] | +0.041 [-0.026, +0.110] | 2.3e-01 |  | published | agrees with GISTEMP v4 250 km land (increasing) |
| central_africa | -0.018 [-0.241, +0.213] | +0.347 [+0.250, +0.445] | -0.401 [-0.553, -0.249] | 1.4e-05 |  | held | disagrees with GISTEMP v4 250 km land: product no clear trend, reference increasing; checked on 32% of the region |
| central_america_caribbean | +0.299 [+0.157, +0.456] | +0.346 [+0.239, +0.459] | -0.040 [-0.107, +0.022] | 2.1e-01 |  | published | agrees with GISTEMP v4 250 km land (increasing) |
| east_africa | -0.017 [-0.140, +0.103] | +0.278 [+0.189, +0.365] | -0.279 [-0.334, -0.226] | 3.2e-16 |  | held | disagrees with GISTEMP v4 250 km land: product no clear trend, reference increasing; checked on 38% of the region |
| east_china | +0.418 [+0.287, +0.549] | +0.491 [+0.358, +0.622] | -0.081 [-0.131, -0.031] | 2.1e-03 |  | limited | direction agrees with GISTEMP v4 250 km land (increasing); size differs by -0.081/decade |
| eastern_us | +0.414 [+0.177, +0.646] | +0.372 [+0.137, +0.606] | +0.022 [-0.016, +0.062] | 2.3e-01 |  | published | agrees with GISTEMP v4 250 km land (increasing) |
| global | +0.235 [+0.141, +0.338] | +0.360 [+0.291, +0.434] | -0.124 [-0.167, -0.080] | 2.4e-06 |  | limited | direction agrees with GISTEMP v4 250 km land (increasing); size differs by -0.124/decade; checked on 37% of the region |
| indian_subcontinent | +0.016 [-0.116, +0.147] | +0.172 [+0.067, +0.279] | -0.153 [-0.193, -0.114] | 3.2e-11 |  | held | disagrees with GISTEMP v4 250 km land: product no clear trend, reference increasing |
| mediterranean | +0.579 [+0.429, +0.728] | +0.572 [+0.420, +0.715] | +0.016 [-0.014, +0.046] | 2.8e-01 |  | published | agrees with GISTEMP v4 250 km land (increasing) |
| mexico | +0.437 [+0.314, +0.560] | +0.444 [+0.328, +0.557] | -0.004 [-0.040, +0.032] | 8.2e-01 |  | published | agrees with GISTEMP v4 250 km land (increasing) |
| middle_east | +0.319 [+0.162, +0.479] | +0.468 [+0.313, +0.624] | -0.163 [-0.205, -0.120] | 3.1e-11 |  | limited | direction agrees with GISTEMP v4 250 km land (increasing); size differs by -0.163/decade |
| sahel | -0.133 [-0.301, +0.036] | +0.228 [+0.107, +0.343] | -0.379 [-0.506, -0.245] | 6.9e-07 |  | held | disagrees with GISTEMP v4 250 km land: product no clear trend, reference increasing |
| siberia | +0.282 [+0.033, +0.545] | +0.547 [+0.303, +0.810] | -0.290 [-0.363, -0.223] | 4.5e-14 |  | limited | direction agrees with GISTEMP v4 250 km land (increasing); size differs by -0.290/decade |
| southeast_asia | +0.224 [+0.144, +0.305] | +0.392 [+0.308, +0.483] | -0.164 [-0.201, -0.128] | 6.2e-11 |  | limited | direction agrees with GISTEMP v4 250 km land (increasing); size differs by -0.164/decade |
| southern_africa | +0.156 [+0.010, +0.305] | +0.182 [+0.057, +0.305] | -0.028 [-0.076, +0.022] | 2.8e-01 |  | limited | agrees with GISTEMP v4 250 km land (increasing); checked on 44% of the region |
| southern_south_america | +0.254 [+0.117, +0.387] | +0.336 [+0.210, +0.459] | -0.080 [-0.129, -0.031] | 1.9e-03 |  | limited | direction agrees with GISTEMP v4 250 km land (increasing); size differs by -0.080/decade |
| western_europe | +0.528 [+0.313, +0.734] | +0.522 [+0.305, +0.738] | -0.004 [-0.035, +0.028] | 8.1e-01 |  | published | agrees with GISTEMP v4 250 km land (increasing) |
| western_us | +0.335 [+0.139, +0.535] | +0.239 [+0.056, +0.424] | +0.109 [+0.060, +0.157] | 1.6e-05 |  | limited | direction agrees with GISTEMP v4 250 km land (increasing); size differs by +0.109/decade |


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
- GPCP v3.3 monthly (GPCPMON), DOI 10.5067/MEASURES/GPCP/DATA306; MERRA-2 M2TMNXLND v5.12.4; GLDAS_NOAH025_M v2.1,
  DOI 10.5067/SXAVCZFAQLNO. Accessed 2026-11-15 through NASA CMR and GES DISC OPeNDAP.
- Guichard et al., chapter using CRU TS3.10, https://books.openedition.org/irdeditions/12319 (warming
  across the Sahel strip; no trend value for 2001-2025).
