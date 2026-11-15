# trendkit

The statistical core of our NASA Space Apps Challenge 2026 project,
"Be an Earth System Trend Detective". Given a monthly time series or a gridded field,
it answers: **what is changing, where, how much, and is the change statistically significant?**

- Removes the seasonal cycle, then measures the rate of change with Sen's slope (per decade, with a 95% CI).
- Tests significance with the Mann-Kendall test, corrected for autocorrelation (method chosen by Monte Carlo).
- Controls false alarms across a map with the Benjamini-Hochberg false discovery rate.
- Returns JSON-ready results for a web app, with plain-language verdicts and warnings.

How each method works, its assumptions, and the numbers we measured: [docs/METHODS.md](docs/METHODS.md).

## Install

Requires Python 3.12 or newer (the test suite passes on Python 3.12.16 and 3.14.4).

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Runtime dependencies: numpy, scipy, pandas, xarray. The `dev` extra adds pytest,
statsmodels and pymannkendall, used only as references in tests.

## Run the tests

```bash
.venv/bin/python -m pytest
```

The full suite takes about 2 minutes (most of it Monte Carlo simulations).
Add `-s` to print the measured coverage, false-alarm rates and the comparison table.

Other scripts:

| Command | What it does |
|---|---|
| `.venv/bin/python examples/demo_synthetic.py` | End-to-end demo on synthetic data: one series, a grid, a regional mean (about 6 s) |
| `.venv/bin/python scripts/benchmark_grid.py` | Times `grid_trends` on a 90 x 180 x 300 grid (52.6 s on a Ryzen 5 3600) |
| `.venv/bin/python scripts/smoke_power.py` | Fetches real monthly temperature from the NASA POWER API and prints its trend report (needs internet) |

## Example

```python
import numpy as np, pandas as pd
from trendkit import trend_report

dates = pd.date_range("2000-01-01", periods=300, freq="MS")  # 25 years, monthly
years = np.arange(300) / 12
rng = np.random.default_rng(0)
temps = 15 + 8 * np.sin(2 * np.pi * years) + 0.03 * years + rng.normal(0, 0.5, 300)

r = trend_report(temps, dates, units="K")
print(r["verdict"], r["slope_per_decade"], r["ci_low_per_decade"], r["ci_high_per_decade"], r["pvalue"])
```

Output (true trend: +0.30 K per decade):

```
increasing 0.22421211988355602 0.1439727438170946 0.3033834479123648 8.134651680819466e-08
```

`r` also holds Kendall's tau, an OLS cross-check, and plain-language `warnings`;
see the docstring of `trend_report` for every key.

For a grid, pass an `xarray.DataArray` with dims `(time, lat, lon)`:
`grid_trends(da)` returns a Dataset with `slope` (per decade), `ci_low`, `ci_high`,
`pvalue`, `qvalue`, `significant` and `n_valid` per cell, and
`area_weighted_mean(da, (lat_min, lat_max, lon_min, lon_max))` reduces a region to one series.
`fixed_mask_mean(da, box)` does the same over a fixed set of cells (valid in at least 95% of the
months), which avoids spurious trends from cells entering or leaving the record; see
docs/METHODS.md section 7.
