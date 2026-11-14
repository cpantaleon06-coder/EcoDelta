import pytest

from ecodelta_engine.narrate import decimals_for, narrate, p_text
from ecodelta_engine.screen import answers

VAR = {"id": "precip", "name": "Rain and snow (precipitation)", "units": "mm day-1", "public_unit": "mm/day",
       "land_only": False}
LAND = dict(VAR, id="evap", name="Water leaving the land (evapotranspiration)", land_only=True)
REGION = {"id": "sahel", "name": "Sahel", "phrase": "the Sahel", "box": [10, 20, -18, 40]}
PERIOD = {"start": "2001-01", "end": "2025-09", "years": 24.667}


def rr(slope, lo, hi, p, verdict, cov=1.0, cells=145, valid_fraction=1.0):
    rep = {"verdict": verdict, "significant": verdict in ("increasing", "decreasing"), "pvalue": p,
           "slope_per_decade": slope, "ci_low_per_decade": lo, "ci_high_per_decade": hi,
           "method": "Sen's slope; Mann-Kendall test (yue_wang)", "warnings": [],
           "n_valid": 297, "n_total": 297, "valid_fraction": valid_fraction}
    return {"report": rep, "n_box_cells": 145, "n_valid_cells": cells, "covered_fraction": cov,
            "cells_significant_fraction": 0.5, "effect_size": 0.7}


def say(var, r):
    return narrate(answers(var, REGION, r, PERIOD), var, REGION)


def test_significant_sentence_has_period_ci_and_no_causal_words():
    text, cautions = say(VAR, rr(0.212, 0.146, 0.277, 1e-8, "increasing"))
    assert text.startswith("From January 2001 to September 2025, rain and snow (precipitation) in the Sahel")
    assert "+0.212 mm/day per decade (95% confidence interval +0.146 to +0.277)" in text
    assert "statistically significant (p < 0.001)" in text and "an increase of about 0.523 mm/day" in text
    assert "cause" not in text.lower() and cautions == []


def test_decrease_has_no_double_negative():
    text, _ = say(VAR, rr(-0.95, -1.2, -0.69, 1e-10, "decreasing"))
    assert "a decrease of about 2.34 mm/day" in text and "−0.95" in text


def test_not_significant_never_says_no_change():
    text, _ = say(VAR, rr(0.004, -0.008, 0.015, 0.5, "no significant trend"))
    assert "no statistically significant trend (p = 0.50)" in text
    assert "no change" not in text.lower() and "does not mean nothing changed" in text


def test_cautions():
    _, c = say(VAR, rr(0.013, 0.0001, 0.026, 0.04, "increasing"))
    assert any("wide" in x for x in c)
    _, c = say(LAND, rr(0.1, 0.05, 0.15, 0.001, "increasing", cov=0.12))
    assert any("Only 12% of this region's area has land cells" in x for x in c)
    _, c = say(VAR, rr(0.1, 0.05, 0.15, 0.001, "increasing", valid_fraction=0.85))
    assert any("15% of the months have no data" in x for x in c)


def test_insufficient_data_land_only():
    r = {"report": None, "n_box_cells": 2700, "n_valid_cells": 0, "covered_fraction": 0.0,
         "cells_significant_fraction": None, "effect_size": None}
    a = answers(LAND, REGION, r, PERIOD)
    text, _ = narrate(a, LAND, REGION)
    assert "only available over land" in text and a["how_much"]["slope_per_decade"] is None
    assert a["significance"]["verdict"] == "insufficient data"


@pytest.mark.parametrize("ci,d", [([0.258, 0.286], 3), ([-1.2, -0.69], 2), ([-8, 12], 0)])
def test_decimals(ci, d):
    assert decimals_for(ci) == d


def test_p_text():
    assert p_text(0.0004) == "p < 0.001" and p_text(0.0042) == "p = 0.0042" and p_text(0.5) == "p = 0.50"
