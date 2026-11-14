"""Convert dates to decimal years.

All trendkit slopes are per year, so time is measured in decimal years
(for example 2000-07-01 -> 2000.4945).
"""

import numpy as np
import pandas as pd


def decimal_year(dates):
    """Convert dates to decimal years.

    Formula: year + (date - Jan 1 of year) / (Jan 1 of next year - Jan 1 of year).
    Leap years are handled exactly because the denominator is the real
    length of that year.

    Parameters
    ----------
    dates : array-like of numpy.datetime64, pandas Timestamps, or ISO date strings.

    Returns
    -------
    numpy.ndarray of float, time in years.

    Assumptions: standard (proleptic Gregorian) calendar. Model output on
    cftime calendars (noleap, 360_day) must be converted to datetime64 first.
    """
    idx = pd.DatetimeIndex(np.atleast_1d(dates))
    years = idx.to_period("Y")
    start = years.start_time
    end = (years + 1).start_time
    return np.asarray(idx.year + (idx - start) / (end - start), dtype=float)


def require_increasing(t):
    """Return t as a float array, or raise ValueError if it is not strictly increasing.

    Order-dependent methods (Mann-Kendall, Sen's slope, autocorrelation)
    assume the series is in time order with no duplicate times.
    """
    t = np.asarray(t, dtype=float)
    if t.ndim != 1:
        raise ValueError(f"time must be 1-D, got shape {t.shape}")
    bad = np.flatnonzero(~(np.diff(t) > 0))
    if bad.size:
        k = bad[0]
        raise ValueError(
            f"time must be strictly increasing; problem at index {k + 1}: "
            f"{t[k]} -> {t[k + 1]}. Sort the series by time and remove duplicate dates."
        )
    return t
