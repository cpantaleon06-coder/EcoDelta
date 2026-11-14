"""Monte Carlo comparison of trend tests under AR(1) noise.

False-alarm rate: share of trend-free series flagged at alpha = 0.05.
Power: share of series with a known linear trend flagged at alpha = 0.05.
Noise is AR(1) with unit marginal variance. The trend's total change over the
record is DELTA[n] noise standard deviations.
"""

import numpy as np

from trendkit.mannkendall import mann_kendall
from trendkit.ols import ols_trend

SIMS = 2000
ALPHA = 0.05
PHIS = (0.0, 0.3, 0.6)
DELTA = {300: 0.5, 25: 1.5}
METHODS = {
    "MK original": lambda y, t: mann_kendall(y, "original")["pvalue"],
    "MK Hamed-Rao": lambda y, t: mann_kendall(y, "hamed_rao")["pvalue"],
    "MK Yue-Wang (AR1)": lambda y, t: mann_kendall(y, "yue_wang")["pvalue"],
    "MK TFPW": lambda y, t: mann_kendall(y, "tfpw")["pvalue"],
    "OLS": lambda y, t: ols_trend(y, t)["pvalue"],
    "OLS AR1-adjusted": lambda y, t: ols_trend(y, t, ar1_adjust=True)["pvalue"],
}


def _ar1(rng, phi, sims, n):
    e = rng.normal(size=(sims, n))
    out = np.empty((sims, n))
    out[:, 0] = e[:, 0]
    for k in range(1, n):
        out[:, k] = phi * out[:, k - 1] + np.sqrt(1 - phi**2) * e[:, k]
    return out


def _rejection_rate(test, y, t, chunk=250):
    p = np.concatenate([test(y[i : i + chunk], t) for i in range(0, len(y), chunk)])
    return np.mean(p < ALPHA)


def _table():
    rng = np.random.default_rng(2026)
    rates = {}  # (method, n, phi) -> (false_alarm, power)
    for n in DELTA:
        t = np.arange(n, dtype=float)
        trend = DELTA[n] * t / (n - 1)
        for phi in PHIS:
            noise = _ar1(rng, phi, SIMS, n)
            for name, test in METHODS.items():
                rates[name, n, phi] = (_rejection_rate(test, noise, t), _rejection_rate(test, noise + trend, t))
    return rates


def test_autocorrelation_monte_carlo():
    rates = _table()
    cols = [(n, phi) for n in DELTA for phi in PHIS]
    header = "| Method | " + " | ".join(f"n={n}, phi={phi}" for n, phi in cols) + " |"
    lines = [f"\nFalse-alarm rate / power at alpha={ALPHA}, {SIMS} sims per cell "
             f"(trend: total change {DELTA[300]} SD for n=300, {DELTA[25]} SD for n=25)",
             header, "|" + "---|" * (len(cols) + 1)]
    for name in METHODS:
        cells = [f"{rates[name, n, phi][0]:.3f} / {rates[name, n, phi][1]:.3f}" for n, phi in cols]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    print("\n".join(lines))

    # Assertions mirror the measured table; binomial SE of a 5% rate at 2000 sims is about 0.005.
    fa = {key: v[0] for key, v in rates.items()}
    default, others = "MK Yue-Wang (AR1)", ("MK original", "MK Hamed-Rao", "MK TFPW")
    for phi in PHIS:
        assert fa[default, 300, phi] <= 0.07  # the default holds ~5% on monthly-length series
    assert fa["MK original", 300, 0.6] > 0.25  # autocorrelation inflates plain MK
    assert fa["MK TFPW", 300, 0.6] > fa["MK original", 300, 0.6]  # TFPW is worse than no correction
    assert fa["MK Hamed-Rao", 300, 0.0] > 0.08  # screening all lags over-rejects even white noise
    for phi in (0.3, 0.6):
        assert fa[default, 25, phi] < min(fa[m, 25, phi] for m in others)  # least inflated on short series
    assert fa[default, 25, 0.6] > 0.08  # but no method fixes short, strongly autocorrelated series
