"""Rank the variables of a region and build the four answers (what, where, how much, significance).

Ranking (sorted ascending by this key; all ingredients are exported):
  1. tier: 0 = significant regional trend (trendkit trend_report, p < ALPHA),
           1 = not significant, 2 = insufficient data
  2. p-value of the regional Mann-Kendall test (smaller first)
  3. |effect size| = |trend per decade| / standard deviation of the regional anomalies (larger first)
Effect size only breaks ties between equal p-values, which in practice happens for "insufficient data"
entries; it is exported so the web app can show it.
"""

import pandas as pd
from trendkit.timeutil import decimal_year

from . import config
from .narrate import narrate

SCORE_DEFINITION = ("Sort by (1) tier: significant regional trend, then not significant, then insufficient data; "
                    "(2) smaller regional p-value first; (3) larger |effect size| first, where effect size = "
                    "trend per decade / standard deviation of the deseasonalized regional series.")

EXPLANATIONS = {
    "increasing": "A rising trend this strong would show up by chance less than 5% of the time if there were no "
                  "real trend, taking month-to-month memory in the data into account.",
    "decreasing": "A falling trend this strong would show up by chance less than 5% of the time if there were no "
                  "real trend, taking month-to-month memory in the data into account.",
    "no significant trend": "The estimated trend is small compared with the natural ups and downs, so the data "
                            "cannot tell it apart from chance. This does not prove that nothing changed.",
    "insufficient data": "There are not enough valid data here to judge a trend (at least 10 years and 80% of "
                         "months are needed).",
}


def period_info(dates) -> dict:
    """Start and end month and the length in years between the first and last month."""
    idx = pd.DatetimeIndex(dates)
    t = decimal_year(idx)
    return {"start": idx[0].strftime("%Y-%m"), "end": idx[-1].strftime("%Y-%m"), "years": float(t[-1] - t[0])}


def answers(var: dict, region: dict, rr: dict, period: dict) -> dict:
    """The four answers for one variable in one region. var: catalog entry; rr: compute.region_result."""
    rep = rr["report"]
    verdict = rep["verdict"] if rep else "insufficient data"
    slope = rep and rep["slope_per_decade"]
    decades = period["years"] / 10
    has_slope = slope is not None and verdict != "insufficient data"
    return {
        "what": {
            "variable": var["id"],
            "name": var["name"],
            "direction": {"increasing": "increase", "decreasing": "decrease"}.get(verdict, "none detected"),
            "verdict": verdict,
        },
        "where": {
            "region": region["id"],
            "name": region["name"],
            "box": region["box"],
            "land_only": var["land_only"],
            "n_box_cells": rr["n_box_cells"],
            "n_valid_cells": rr["n_valid_cells"],
            "covered_fraction": rr["covered_fraction"],
        },
        "how_much": {
            "period": [period["start"], period["end"]],
            "period_years": round(period["years"], 3),
            "units": var["units"],
            "public_unit": var["public_unit"],
            "slope_per_decade": slope if has_slope else None,
            "ci_per_decade": [rep["ci_low_per_decade"], rep["ci_high_per_decade"]] if has_slope else None,
            "total_change": slope * decades if has_slope else None,
            "total_change_ci": [rep["ci_low_per_decade"] * decades, rep["ci_high_per_decade"] * decades]
            if has_slope else None,
            "ci_level": 1 - config.ALPHA,
        },
        "data": {
            "n_valid_months": rep and rep["n_valid"],
            "n_months": rep and rep["n_total"],
            "valid_fraction": rep["valid_fraction"] if rep else 0.0,
        },
        "significance": {
            "verdict": verdict,
            "significant": bool(rep and rep["significant"]),
            "pvalue": rep and rep["pvalue"],
            "alpha": config.ALPHA,
            "test": rep["method"] if rep else None,
            "qvalue": None,  # one regional test per variable and region: no multiple-testing adjustment
            "cells_significant_after_fdr_fraction": rr["cells_significant_fraction"],
            "explanation": EXPLANATIONS[verdict],
            "warnings": rep["warnings"] if rep else [],
        },
    }


def score(rr: dict) -> dict:
    rep = rr["report"]
    verdict = rep["verdict"] if rep else "insufficient data"
    tier = 2 if verdict == "insufficient data" else 0 if rep["significant"] else 1
    eff = rr["effect_size"] if tier < 2 else None
    return {"tier": tier, "significant": tier == 0, "pvalue": rep["pvalue"] if tier < 2 else None,
            "effect_size": eff, "abs_effect_size": abs(eff) if eff is not None else None}


def _key(s: dict) -> tuple:
    p = s["pvalue"] if s["pvalue"] is not None else 1.0
    return (s["tier"], p, -(s["abs_effect_size"] or 0.0))


def screen_region(region: dict, region_results: dict, catalog: dict, period: dict) -> list[dict]:
    """All variables of one region, ranked. region_results: {variable: compute.region_result}."""
    entries = []
    for var in sorted(region_results):
        a = answers(catalog[var], region, region_results[var], period)
        sentence, cautions = narrate(a, catalog[var], region)
        entries.append({"variable": var, "score": score(region_results[var]), "answers": a,
                        "sentence": sentence, "cautions": cautions})
    entries.sort(key=lambda e: (_key(e["score"]), e["variable"]))
    for i, e in enumerate(entries, 1):
        e["rank"] = i
    return entries
