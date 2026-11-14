import numpy as np
import pandas as pd
import pytest

from trendkit.timeutil import decimal_year, require_increasing


def test_decimal_year_known_values():
    got = decimal_year(["2000-01-01", "2000-07-01", "2001-07-01", "2001-12-31T12:00"])
    # 2000 is a leap year: Jul 1 is day 182 of 366; 2001 has 365 days.
    assert got == pytest.approx([2000.0, 2000 + 182 / 366, 2001 + 181 / 365, 2001 + 364.5 / 365])


def test_decimal_year_accepts_numpy_and_pandas():
    d = pd.date_range("1990-01-01", periods=24, freq="MS")
    a = decimal_year(d)
    b = decimal_year(d.to_numpy())
    np.testing.assert_array_equal(a, b)
    assert np.all(np.diff(a) > 0)
    assert a.shape == (24,)


def test_require_increasing_rejects_unsorted_and_duplicates():
    require_increasing([1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="strictly increasing"):
        require_increasing([1.0, 3.0, 2.0])
    with pytest.raises(ValueError, match="strictly increasing"):
        require_increasing([1.0, 2.0, 2.0])
