"""Rule-based plain-language sentences (templates only; no language model).

Rules: always state the period and the 95% confidence interval; never say "caused by";
a non-significant result is never described as "no change". Caution lines cover only a wide CI,
missing months, and low regional coverage; trendkit's technical warnings (for example strong
autocorrelation, which the CI and p-value already account for) stay in answers.significance.warnings.
"""

import math

import pandas as pd

from . import config

LIMITED_DATA = 0.95  # caution when fewer than this fraction of months are valid


def month_year(ym: str) -> str:
    return pd.Timestamp(ym + "-01").strftime("%B %Y")


def decimals_for(ci: list[float]) -> int:
    """Decimals so the CI half-width shows about two significant digits."""
    half = abs(ci[1] - ci[0]) / 2
    return max(0, 1 - math.floor(math.log10(half))) if half > 0 else 2


def signed(x: float, d: int) -> str:
    s = f"{x:+.{d}f}"
    return s.replace("-", "−") if float(s) != 0 else f"{0:.{d}f}"


def p_text(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.2g}" if p < 0.01 else f"p = {p:.2f}"


def lower_first(name: str) -> str:
    return name[0].lower() + name[1:] if name[:2] != name[:2].upper() else name


def narrate(a: dict, var: dict, region: dict) -> tuple[str, list[str]]:
    """(one or two sentences, list of caution lines) for one answers object."""
    hm, sig, where = a["how_much"], a["significance"], a["where"]
    period = f"From {month_year(hm['period'][0])} to {month_year(hm['period'][1])}"
    subject = f"{lower_first(var['name'])} in {region['phrase']}"
    unit = hm["public_unit"]
    verdict = sig["verdict"]
    cautions = []

    if verdict == "insufficient data":
        if where["n_valid_cells"] == 0 and var["land_only"]:
            text = (f"{period}, there is no trend estimate for {subject}: this variable is only available over "
                    f"land, and no land cell in this region has enough data.")
        else:
            text = (f"{period}, there are not enough valid data to judge a trend for {subject} "
                    f"(at least 10 years and 80% of months are needed).")
        return text, cautions

    lo, hi = hm["ci_per_decade"]
    d = decimals_for([lo, hi])
    slope_txt = f"{signed(hm['slope_per_decade'], d)} {unit} per decade"
    ci_txt = f"95% confidence interval {signed(lo, d)} to {signed(hi, d)}"
    if verdict in ("increasing", "decreasing"):
        word = "an increase" if verdict == "increasing" else "a decrease"
        total = f"{abs(hm['total_change']):.{d}f}"
        text = (f"{period}, {subject} changed by {slope_txt} ({ci_txt}), which is statistically significant "
                f"({p_text(sig['pvalue'])}). Over the whole {hm['period_years']:.1f}-year period that is {word} "
                f"of about {total} {unit}.")
        if hi - lo > config.WIDE_CI_RATIO * abs(hm["slope_per_decade"]):
            cautions.append("The confidence interval is wide compared with the trend, so the size of the change "
                            "is uncertain.")
    else:
        text = (f"{period}, {subject} shows no statistically significant trend ({p_text(sig['pvalue'])}): the "
                f"estimate is {slope_txt} ({ci_txt}). This does not mean nothing changed; the data cannot tell "
                f"a trend this small apart from natural ups and downs.")

    if where["covered_fraction"] < config.LOW_COVERAGE:
        what = "land cells with enough data" if var["land_only"] else "cells with enough data"
        cautions.append(f"Only {100 * where['covered_fraction']:.0f}% of this region's area has {what}, so the "
                        f"result describes only that part.")
    elif where["n_valid_cells"] < 5:
        cautions.append(f"Based on only {where['n_valid_cells']} grid cells of about 220 km.")
    if a["data"]["valid_fraction"] < LIMITED_DATA:
        cautions.append(f"{100 * (1 - a['data']['valid_fraction']):.0f}% of the months have no data here.")
    return text, cautions
