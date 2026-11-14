# trendkit methods

This document explains what trendkit computes, why, and how far you can trust it.
It is written for students who know what a mean and a standard deviation are.
Every number below comes from a test or script in this repository that we ran on
the machine described under [Performance](#performance). Random tests use fixed
seeds, so you can reproduce them with `pytest -s`.

## The pipeline in one paragraph

For one time series (one grid cell, or a regional average) trendkit:
1. converts dates to decimal years,
2. removes the seasonal cycle if the data are monthly,
3. measures the **rate of change** with Sen's slope, reported per decade, with a 95% confidence interval,
4. tests whether the change is **statistically significant** with the Mann-Kendall test, corrected for autocorrelation,
5. on a map, controls the number of false alarms across all cells with the Benjamini-Hochberg false discovery rate,
6. reports an ordinary least squares (OLS) slope and t-test as a cross-check.

## What "significant" means

A trend is called significant when a series with **no** real trend, but the same
noise, would show a trend this strong less than 5% of the time (p < 0.05).
It does not mean the trend is large or important, and it does not prove what caused it.

## 1. Time in decimal years

`decimal_year` turns a date into a number of years:
`year + (days since Jan 1) / (days in that year)`. For example 2000-07-01 is
2000 + 182/366 = 2000.497. All slopes are computed per year and multiplied by 10
to report them per decade.

Assumption: the ordinary (Gregorian) calendar. Climate model output on
`noleap` or `360_day` calendars must be converted first.

## 2. Removing the seasonal cycle

Many Earth-system variables swing up and down every year (summer and winter).
That swing is much bigger than a slow trend, so it hides the trend.
`deseasonalize_monthly` computes the **climatology**, the average of each calendar month:

```
climatology[m] = mean of all values in calendar month m   (over the base period)
anomaly(t)     = value(t) - climatology[month of t]
```

The base period defaults to the whole record; you can choose, for example, 1991-2020.
Missing values (NaN) are skipped.

**Measured effect** (`tests/test_seasonal.py`): a 25-year monthly series with a
seasonal cycle of amplitude 10, a true trend of +0.02 units per year, and noise
of standard deviation 0.3.

| | slope (per year) | standard error | p-value |
|---|---|---|---|
| raw series | -0.0078 | 0.0567 | 0.891 (trend missed) |
| deseasonalized | +0.0221 | 0.0022 | 1.4e-20 (trend found) |

Removing the cycle shrinks the standard error about 25 times.

Assumptions and limits: the shape of the seasonal cycle does not change over
time. If it does (for example, an earlier spring), part of that change will show
up in the anomalies. An alternative we did not implement is the seasonal Kendall
test of Hirsch et al. (1982), which tests each calendar month separately and
combines the results.

## 3. Rate of change

### Sen's slope (main estimate)

Take every pair of points (i, j) with i earlier than j and compute the slope
between them. Sen's slope is the **median** of all these slopes (Sen 1968):

```
slope = median over i < j of (y_j - y_i) / (t_j - t_i)
```

With 300 monthly values there are 44,850 pairs. Because it uses the median,
a few wild values barely move it: in our test, adding +500 to 10% of the points
still gave the true slope 0.5 within 0.05.

**Confidence interval** (Sen 1968; Gilbert 1987). Sort the N pairwise slopes. With
`C = 1.96 * sqrt(Var(S))` (Var(S) from the Mann-Kendall test below),
the 95% interval runs from the slope ranked `(N - C)/2` to the slope ranked
`(N + C)/2 + 1`. We use the autocorrelation-corrected Var(S), so the interval
widens when neighbouring values are correlated. Measured on 1,000 AR(1) series
with phi = 0.6, n = 300 (`tests/test_mannkendall.py`): the 95% interval contained
the true slope **68.6%** of the time with the uncorrected Var(S) and **94.6%** with
the corrected one.

### Ordinary least squares (cross-check)

The familiar straight-line fit `y = a + b t`:

```
b     = sum((t - mean t)(y - mean y)) / sum((t - mean t)^2)
SE(b) = sqrt( sum(residual^2) / ((n_eff - 2) * sum((t - mean t)^2)) )
t     = b / SE(b),   p from Student's t with n_eff - 2 degrees of freedom
CI    = b +/- t_0.975 * SE(b)
```

With the AR(1) adjustment, the effective sample size is
`n_eff = n (1 - r1) / (1 + r1)` when the lag-1 autocorrelation r1 of the residuals
is positive (Santer et al. 2000 use this form), otherwise `n_eff = n`.

Measured on white noise (`tests/test_ols.py`): the 95% CI covered the true slope
in **95.4%** of 1,000 simulations (mean slope bias -1.2e-4 per year), and the false-alarm
rate at p < 0.05 was **4.92%** over 5,000 trend-free simulations.

Assumptions: a straight-line trend; residuals normal with constant variance;
independent residuals (or AR(1) with the adjustment). OLS is sensitive to outliers.

## 4. Significance: the Mann-Kendall test

The Mann-Kendall test (Mann 1945; Kendall 1975) asks: do later values tend to be
larger (or smaller) than earlier ones? It only looks at the **order** of values,
so it needs no assumption about their distribution.

```
S      = sum over i < j of sign(y_j - y_i)          (+1 if later is bigger, -1 if smaller, 0 if tied)
Var(S) = [n(n-1)(2n+5) - sum over groups of tied values of g(g-1)(2g+5)] / 18
Z      = (S - 1)/sqrt(Var(S)) if S > 0,  0 if S = 0,  (S + 1)/sqrt(Var(S)) if S < 0
p      = 2 * (1 - Phi(|Z|))                          (two-sided; Phi = standard normal CDF)
tau    = S / (n(n-1)/2)                              (Kendall's tau, between -1 and +1)
```

The `-1`/`+1` in Z is a continuity correction. The formula for Var(S) assumes the
values are **independent**. That assumption is the problem addressed next.

## 5. Autocorrelation: the main trap

Monthly anomalies are **autocorrelated**: a warm month tends to be followed by
another warm month. Such a series wanders, and the plain test mistakes the
wandering for a trend. We implemented three published fixes. Each first removes
the trend with Sen's slope, so the trend itself is not mistaken for autocorrelation.

* **Hamed and Rao (1998)**: multiply Var(S) by
  `1 + 2/(n(n-1)(n-2)) * sum_k (n-k)(n-k-1)(n-k-2) rho_k`, where rho_k is the
  autocorrelation at lag k of the **ranks** of the detrended series, keeping only lags
  with |rho_k| > 1.96/sqrt(n).
* **Yue and Wang (2004)**: multiply Var(S) by the variance inflation of an
  effective sample size, `1 + 2 sum_k (1 - k/n) rho_k`. We model the
  autocorrelation as AR(1), `rho_k = r1^k`, and never let the factor drop below 1.
  Both are our choices (see below).
* **Trend-free pre-whitening, TFPW** (Yue et al. 2002): remove the lag-1 dependence,
  `w_i = x_i - r1 x_{i-1}`, add the trend back, and run the plain test on w.

### Monte Carlo comparison

We simulated AR(1) noise `e_t = phi e_{t-1} + noise` with variance 1, for monthly-length
(n = 300) and annual-length (n = 25) series, 2,000 series per cell
(`tests/test_autocorr_montecarlo.py`, seed 2026). **False-alarm rate** = share of
trend-free series flagged at p < 0.05 (ideal: 0.05). **Power** = share of series with a
real trend flagged (total change over the record: 0.5 noise SD for n = 300,
1.5 SD for n = 25). Each cell shows false-alarm rate / power.

| Method | n=300, phi=0 | n=300, phi=0.3 | n=300, phi=0.6 | n=25, phi=0 | n=25, phi=0.3 | n=25, phi=0.6 |
|---|---|---|---|---|---|---|
| MK original | 0.047 / 0.682 | 0.140 / 0.637 | 0.328 / 0.623 | 0.058 / 0.531 | 0.117 / 0.542 | 0.280 / 0.576 |
| MK Hamed-Rao | 0.097 / 0.722 | 0.119 / 0.555 | 0.169 / 0.417 | 0.087 / 0.579 | 0.143 / 0.562 | 0.254 / 0.514 |
| **MK Yue-Wang (AR1), default** | **0.043 / 0.662** | **0.056 / 0.443** | **0.054 / 0.240** | **0.045 / 0.489** | **0.077 / 0.404** | **0.128 / 0.339** |
| MK TFPW | 0.046 / 0.675 | 0.168 / 0.659 | 0.421 / 0.701 | 0.043 / 0.481 | 0.124 / 0.516 | 0.342 / 0.615 |
| OLS | 0.048 / 0.701 | 0.149 / 0.658 | 0.336 / 0.629 | 0.057 / 0.570 | 0.139 / 0.583 | 0.299 / 0.618 |
| OLS AR1-adjusted | 0.044 / 0.684 | 0.047 / 0.452 | 0.057 / 0.246 | 0.048 / 0.529 | 0.083 / 0.429 | 0.127 / 0.334 |

What the table shows:
* Ignoring autocorrelation is costly: with phi = 0.6 the plain test raises a false alarm
  for a third of trend-free monthly series (0.328 instead of 0.05).
* TFPW is worse than doing nothing at phi = 0.6 (0.421).
* Hamed-Rao gives 0.097 false alarms even for white noise. Our implementation matches
  pymannkendall exactly, so this is the method as published with all lags screened, not a
  coding error. We did not investigate the cause; a plausible one is that about 5% of
  ~300 lags pass the significance screen by chance and their terms shrink Var(S).
  Hamed and Rao also suggested using only the first few lags, which we did not test.
* Yue-Wang (AR1) holds the false-alarm rate near 0.05 for monthly-length series
  at every phi, and is the least inflated Mann-Kendall variant for 25-point series.
  It behaves almost exactly like OLS with the AR(1) adjustment, which is reassuring.
* Its power is lower under autocorrelation. That is the honest price: an
  autocorrelated series contains less independent information. Higher "power" in
  the other rows comes together with many false alarms.

**Default: Yue-Wang (AR1).** It is the only variant that kept false alarms near 5% on
monthly-length series for every level of autocorrelation we tried.

**Why the floor at 1.** We tested it on a separate seed (99) after seeing the first
table. Without the floor, a negative sample r1 can shrink Var(S). For white noise
with n = 25 the false-alarm rate was 0.071 without the floor and 0.036 with it
(power 0.573 vs 0.486); for n = 25, phi = 0.3 it went from 0.087 to 0.077; other
settings changed by less than 0.01. OLS with the AR(1) adjustment already used
the same rule.

**What is not solved.** No method we tried keeps false alarms at 5% for short
(25-point), strongly autocorrelated series: the default gives 0.077 at phi = 0.3
and 0.128 at phi = 0.6. The lag-1 autocorrelation estimated from 25 points is
too uncertain (and biased low). The report adds a warning in this case.

**Small p-values.** On a map, the FDR step uses thresholds much smaller than 0.05.
Over 10,000 trend-free series of n = 300 (seed 555), the default test gave:

| | P(p < 0.05) | P(p < 0.01) | P(p < 0.0025) |
|---|---|---|---|
| phi = 0 | 0.0459 | 0.0080 | 0.0015 |
| phi = 0.3 | 0.0526 | 0.0107 | 0.0030 |

So for phi = 0.3 the test is about 20% too liberal at 0.0025 (with roughly
+/-20% sampling uncertainty on that ratio), and somewhat conservative for white noise.

## 6. Many grid cells: false discovery rate

Testing 16,000 cells at p < 0.05 would flag about 800 cells by chance even with no
trend anywhere. The Benjamini and Hochberg (1995) procedure controls the **false
discovery rate**: among the cells called significant, the expected share of false
ones is at most q (we use q = 0.05).

```
sort the m p-values: p(1) <= p(2) <= ... <= p(m)
q-value of p(i) = min over j >= i of ( m * p(j) / j ), capped at 1
significant     = q-value <= 0.05
```

Cells without enough data are not tested and do not count in m.

**Measured** (`tests/test_grid.py`): a 20 x 30 grid, 25 years monthly, seasonal
cycle, AR(1) noise with phi = 0.3, a 30-cell patch with a trend of 1.5 noise SD
over the record, a block of all-missing cells, and 2% scattered gaps.

| | result |
|---|---|
| patch cells detected (10 maps) | 99.0% |
| false discovery proportion, mean of 10 maps (in the test) | 0.075 |
| false discovery proportion, mean of 40 other maps (seeds 100-139) | 0.059 +/- 0.007 |
| false cells per map without FDR (raw p < 0.05) | 31.3 of about 530 |

The 40-map value is close to, but slightly above, the 0.05 target; this matches
the small-p-value inflation measured above at phi = 0.3.

Limit: Benjamini-Hochberg is guaranteed for independent or positively dependent
tests. Neighbouring grid cells are correlated, which makes the false discovery
proportion of a single map more variable; Wilks (2016) discusses this for climate maps.

## 7. Regional averages

`area_weighted_mean` turns a region of the map into one time series. On a regular
latitude-longitude grid, cells near the poles are smaller, so each cell is
weighted by `cos(latitude)`:

```
regional mean(t) = sum(cos(lat) * x(t)) / sum(cos(lat))   over valid cells in the region
```

Limit: if cells drop in and out of the record (sea ice, clouds), the average is taken over
a changing set of cells, which can create a trend that is not in the data.

## 8. Minimum data

A series is judged only if it has **at least 10 years of valid data** and **at least
80% of its time steps valid** (for monthly data: at least 120 valid months, and no more than
20% missing). Below that, `grid_trends` leaves the cell untested and `trend_report`
returns the verdict "insufficient data" with a warning. Ten years is a common minimum
in climate trend work because shorter records are dominated by year-to-year
variability; it is a convention, not a law.

## 9. The report for one series

`trend_report` returns a JSON-ready dict with the Sen slope and CI per decade, the
Mann-Kendall p-value (or a supplied FDR-adjusted one), Kendall's tau, the lag-1
autocorrelation, the OLS cross-check, a `significant` flag, a `verdict`
("increasing", "decreasing", "no significant trend", or "insufficient data") and
plain-language `warnings`: too little data, too many missing values, a constant
series, strong autocorrelation, a short autocorrelated series, the plain test used on
autocorrelated data, OLS and Mann-Kendall disagreeing, or seasonal removal on non-monthly data.

## 10. Checks against reference software

| Our function | Reference | Agreement |
|---|---|---|
| `ols_trend` | `scipy.stats.linregress`, statsmodels OLS CI | relative 1e-8 or better |
| `mann_kendall(method="original")` | `pymannkendall.original_test` (tie-free, and with ties and NaN) | S exact, p relative 1e-9 |
| `mann_kendall(method="hamed_rao")` | `pymannkendall.hamed_rao_modification_test` | S exact, Var(S) relative 1e-9 |
| `mann_kendall(method="tfpw")` | `pymannkendall.trend_free_pre_whitening_modification_test` | S exact, Var(S) relative 1e-9 |
| `sens_slope` | `scipy.stats.theilslopes` (slope and CI) | relative 1e-12 |
| `fdr_bh` | `statsmodels.stats.multitest.multipletests(method="fdr_bh")` | relative 1e-12 |

Yue-Wang (AR1) has no exact reference because of our AR(1) and floor choices; a test
checks that its factor approaches the theoretical (1 + phi)/(1 - phi) on a long AR(1) series.

## Performance

`scripts/benchmark_grid.py`, every cell valid (the worst case):

```
grid_trends on 90x180 cells x 300 months: 52.6 s (308 cells/s), peak memory 0.59 GB
machine: AMD Ryzen 5 3600 6-Core Processor, 12 logical CPUs, Linux 7.0.0-43-generic, Python 3.14.4, numpy 2.5.4
```

## Limits to keep in mind

* All methods look for a **monotonic** (Mann-Kendall) or **linear** (OLS) change. A
  trend that rises and then falls can come out as "no significant trend".
* A sudden jump (for example a new satellite instrument) looks like a trend to these tests.
* Significance is not importance: with long records, tiny trends become significant.
* Short, autocorrelated series still give too many false alarms (section 5).
* Time steps are assumed equally spaced; the autocorrelation corrections count lags in steps.

## References

Benjamini and Hochberg (1995). Gilbert (1987). Hamed and Rao (1998). Hirsch et al. (1982).
Kendall (1975). Mann (1945). Santer et al. (2000). Sen (1968). Wilks (2016).
Yue and Wang (2004). Yue et al. (2002).
