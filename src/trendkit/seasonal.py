"""Remove the mean seasonal cycle from monthly series."""

import warnings

import numpy as np
import pandas as pd


def deseasonalize_monthly(values, dates, base_period=None):
    """Subtract the mean of each calendar month (monthly climatology).

    Formula:
        climatology[m] = mean of values in calendar month m within the base period (NaN ignored)
        anomaly(t)     = value(t) - climatology[month(t)]

    Parameters
    ----------
    values : array-like, time on axis 0. A 1-D series or an N-D grid such as (time, lat, lon).
    dates : array-like of dates, one per entry on axis 0 (any day within the month).
    base_period : (start, end) or None. Inclusive bounds compared against `dates`
        as given, for example ("1991-01-01", "2020-12-31"). None uses the full record.

    Returns
    -------
    anomalies : ndarray, same shape and units as `values`.
    climatology : ndarray of shape (12, *values.shape[1:]); index 0 is January.
        NaN where a calendar month has no valid data in the base period; the
        anomalies for that month are then NaN as well.

    Assumptions: one value per month, and a fixed seasonal cycle (its shape
    does not change over the record). If some calendar months have many
    more missing values than others, the climatology for those months is
    noisier.
    """
    values = np.asarray(values, dtype=float)
    idx = pd.DatetimeIndex(np.atleast_1d(dates))
    if len(idx) != values.shape[0]:
        raise ValueError(f"{len(idx)} dates for {values.shape[0]} time steps")
    month = idx.month.to_numpy() - 1
    if base_period is None:
        in_base = np.ones(len(idx), dtype=bool)
    else:
        in_base = np.asarray((idx >= pd.Timestamp(base_period[0])) & (idx <= pd.Timestamp(base_period[1])))

    clim = np.full((12,) + values.shape[1:], np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells give NaN, which is what we want
        for m in range(12):
            sel = (month == m) & in_base
            if sel.any():
                clim[m] = np.nanmean(values[sel], axis=0)
    return values - clim[month], clim
