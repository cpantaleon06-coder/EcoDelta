"""trendkit: trend detection for monthly Earth-system time series and grids."""

from .mannkendall import mann_kendall, sens_slope
from .ols import ols_trend
from .seasonal import deseasonalize_monthly
from .timeutil import decimal_year

__version__ = "0.1.0"
