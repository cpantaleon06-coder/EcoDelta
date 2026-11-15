"""Rank the variables of a region and build the four answers (what, where, how much, significance).

Evidence (how sure we are that there is a trend) and magnitude (how big it is) are kept apart:
  evidence class: strong / moderate / weak / none / insufficient data, from p, whether the 95% CI
                  excludes 0, and the fixed mask's coverage (evidence_code, evidence)
  magnitude:      slope per decade, total change, and standardized_change = total change / SD of the
                  detrended deseasonalized monthly series (computed in compute.region_result)
Two orderings are exported (ORDERINGS); `rank` follows by_evidence. The 1.1.0 score (tier, p,
effect size) is still exported for old readers.
"""

import numpy as np
import pandas as pd
from trendkit.timeutil import decimal_year

from . import config
from .narrate import narrate

EVIDENCE_CLASSES = ("strong", "moderate", "weak", "none", "insufficient data")  # strongest first
EVIDENCE_DEFINITION = {
    "strong": f"p < {config.EVIDENCE_STRONG_P} and the 95% confidence interval of the slope excludes 0",
    "moderate": f"p < {config.ALPHA} and the 95% confidence interval excludes 0 (not strong)",
    "weak": f"p < {config.EVIDENCE_WEAK_P} (not moderate or strong), or p < {config.ALPHA} with a confidence "
            "interval that includes 0",
    "none": "everything else with enough data",
    "insufficient data": "no regional report, or fewer than 10 years or 80% of months with data",
    "coverage_cap": f"when the fixed mask covers less than {config.LOW_COVERAGE:.0%} of the region box, strong and "
                    "moderate become weak",
    "maps": "grid cells use the same thresholds with the Benjamini-Hochberg q-value in place of p; cells that fail "
            "the data requirement are insufficient data",
}
MAGNITUDE_DEFINITION = (
    "slope_per_decade and total_change (slope x period years / 10) in the variable's units; standardized_change = "
    "total_change / residual_sd, where residual_sd is the standard deviation of the deseasonalized monthly regional "
    "series after removing the Sen trend line (no unit: how many typical monthly swings the trend added up to). "
    "Limits: not a measure of importance; smaller for noisy variables and larger for big regions, so compare "
    "variables within one region, not regions; smaller than the same measure on annual means; grows with the "
    "period length. No percent-of-mean is given (meaningless for temperature in degC).")
ORDERINGS = {
    "by_evidence": "evidence class (strong, moderate, weak, none, insufficient data); ties: smaller regional p-value, "
                   "then larger |standardized_change|, then variable id",
    "by_magnitude": "larger |standardized_change| first, results without one last; ties: stronger evidence class, "
                    "then smaller p-value, then variable id",
}
SCORE_DEFINITION = ("rank follows by_evidence: " + ORDERINGS["by_evidence"] + ". A second ordering, by_magnitude, is "
                    "exported next to it. The tier, p-value and effect_size of schema 1.1.0 are still exported.")

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
            "fixed_mask": rr["fixed_mask"],
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


def evidence_code(p, ci_low, ci_high):
    """Evidence class index into EVIDENCE_CLASSES per element: 0 strong, 1 moderate, 2 weak, 3 none,
    4 insufficient data (p is NaN). Works on scalars and arrays (maps pass q as p)."""
    p, lo, hi = (np.asarray(x, dtype=float) for x in (p, ci_low, ci_high))
    excludes_zero = (lo > 0) | (hi < 0)
    with np.errstate(invalid="ignore"):
        code = np.select([(p < config.EVIDENCE_STRONG_P) & excludes_zero, (p < config.ALPHA) & excludes_zero,
                          p < config.EVIDENCE_WEAK_P], [0, 1, 2], 3)
    return np.where(np.isnan(p), 4, code)


def evidence(rr: dict) -> dict:
    """Evidence class of one regional result (compute.region_result)."""
    rep = rr["report"]
    if not rep or rep["verdict"] == "insufficient data":
        return {"class": "insufficient data", "ci_excludes_zero": None, "capped_by_coverage": False}
    lo, hi = rep["ci_low_per_decade"], rep["ci_high_per_decade"]
    code = int(evidence_code(rep["pvalue"], lo, hi))
    capped = code < 2 and rr["fixed_mask"]["covered_fraction"] < config.LOW_COVERAGE
    return {"class": EVIDENCE_CLASSES[2 if capped else code], "ci_excludes_zero": bool(lo > 0 or hi < 0),
            "capped_by_coverage": capped}


def magnitude(rr: dict, units: str) -> dict:
    rep = rr["report"]
    ok = rr["standardized_change"] is not None
    return {"slope_per_decade": rep["slope_per_decade"] if ok else None, "total_change": rr["total_change"],
            "units": units, "residual_sd": rr["residual_sd"], "standardized_change": rr["standardized_change"]}


def evidence_key(e: dict) -> tuple:
    p = e["score"]["pvalue"]
    m = e["magnitude"]["standardized_change"]
    return (EVIDENCE_CLASSES.index(e["evidence"]["class"]), 1.0 if p is None else p,
            -abs(m) if m is not None else 0.0, e["variable"])


def magnitude_key(e: dict) -> tuple:
    p = e["score"]["pvalue"]
    m = e["magnitude"]["standardized_change"]
    return (m is None, -abs(m) if m is not None else 0.0, EVIDENCE_CLASSES.index(e["evidence"]["class"]),
            1.0 if p is None else p, e["variable"])


def screen_region(region: dict, region_results: dict, catalog: dict, period: dict) -> list[dict]:
    """All variables of one region, ranked. region_results: {variable: compute.region_result}."""
    entries = []
    for var in sorted(region_results):
        a = answers(catalog[var], region, region_results[var], period)
        sentence, cautions = narrate(a, catalog[var], region)
        rr = region_results[var]
        entries.append({"variable": var, "score": score(rr), "evidence": evidence(rr),
                        "magnitude": magnitude(rr, catalog[var]["units"]), "answers": a,
                        "sentence": sentence, "cautions": cautions})
    for i, e in enumerate(sorted(entries, key=magnitude_key), 1):
        e["rank_by_magnitude"] = i
    entries.sort(key=evidence_key)
    for i, e in enumerate(entries, 1):
        e["rank"] = i
    return entries
