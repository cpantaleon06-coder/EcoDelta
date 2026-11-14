"""Time grid_trends on a synthetic 90 x 180 x 300 grid (every cell valid: the worst case)."""

import os
import platform
import resource
import time

import numpy as np
import pandas as pd
import xarray as xr

from trendkit.grid import grid_trends


def cpu_name():
    try:
        with open("/proc/cpuinfo") as f:
            return next(line.split(":", 1)[1].strip() for line in f if line.startswith("model name"))
    except (OSError, StopIteration):
        return platform.processor() or "unknown CPU"


def main():
    rng = np.random.default_rng(0)
    nt, ny, nx = 300, 90, 180
    dates = pd.date_range("2000-01-01", periods=nt, freq="MS")
    cycle = 5 * np.sin(2 * np.pi * np.arange(nt) / 12)[:, None, None]
    data = cycle + rng.normal(size=(nt, ny, nx)) + 0.002 * np.arange(nt)[:, None, None]
    da = xr.DataArray(data, dims=("time", "lat", "lon"),
                      coords={"time": dates, "lat": np.linspace(-89, 89, ny), "lon": np.linspace(-179, 179, nx)})
    t0 = time.perf_counter()
    ds = grid_trends(da)
    elapsed = time.perf_counter() - t0
    peak_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**2  # ru_maxrss is KiB on Linux
    print(f"grid_trends on {ny}x{nx} cells x {nt} months: {elapsed:.1f} s "
          f"({ny * nx / elapsed:.0f} cells/s), peak memory {peak_gb:.2f} GB")
    print(f"significant cells: {int(ds['significant'].sum())} of {ny * nx}")
    print(f"machine: {cpu_name()}, {os.cpu_count()} logical CPUs, {platform.system()} {platform.release()}, "
          f"Python {platform.python_version()}, numpy {np.__version__}")


if __name__ == "__main__":
    main()
