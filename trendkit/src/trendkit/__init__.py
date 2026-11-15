"""trendkit: trend detection for monthly Earth-system time series and grids."""

from .mannkendall import mann_kendall, sens_slope
from .fdr import fdr_bh
from .grid import area_weighted_mean, fixed_mask_mean, grid_trends
from .ols import ols_trend
from .report import trend_report
from .seasonal import deseasonalize_monthly
from .timeutil import decimal_year

__version__ = "0.1.0"
