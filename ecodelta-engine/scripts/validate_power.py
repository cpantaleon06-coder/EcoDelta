"""Compare one exported regional T2M trend with NASA POWER monthly T2M for the same box and period.

NASA POWER's API names its own source in the response header ("sources"); for T2M it reports MERRA2,
so this comparison checks our pipeline (subsetting, unit conversion, regridding, area averaging,
deseasonalizing, trend), NOT the science. The script prints that header so the claim is checked live.

POWER's regional endpoint accepts at most 10 x 10 degrees, so the box is fetched in tiles. The POWER
box is the union of the 2 degree cells whose centers lie in the region box (the engine's rule), so both
sides cover the same area. Same statistics: regional_report from the engine (trendkit trend_report on
the deseasonalized cos(latitude)-weighted mean).

Run: .venv/bin/python scripts/validate_power.py [region_id]   (needs web_data/ from a real build)
"""

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from ecodelta_engine import config
from ecodelta_engine.compute import regional_report
from ecodelta_engine.regions import load_regions

sys.path.insert(0, str(config.REPO.parent / "trendkit" / "scripts"))
from smoke_power import monthly_series  # noqa: E402  (reused: drops month "13", maps the fill value to NaN)

API = ("https://power.larc.nasa.gov/api/temporal/monthly/regional?parameters=T2M&community=RE"
       "&latitude-min={0}&latitude-max={1}&longitude-min={2}&longitude-max={3}&start={4}&end={5}&format=JSON")
CACHE = config.REPO / "build" / "power"


def tiles(lo, hi, step=10):
    edges = list(np.arange(lo, hi, step)) + [hi]
    return list(zip(edges[:-1], edges[1:]))


def fetch_box(box, start_year, end_year):
    """{(lat, lon): pd.Series} of POWER T2M at native points inside box, plus the response headers."""
    points, headers = {}, []
    for la in tiles(box[0], box[1]):
        for lo in tiles(box[2], box[3]):
            url = API.format(*la, *lo, start_year, end_year)
            cache = CACHE / f"{la[0]}_{la[1]}_{lo[0]}_{lo[1]}_{start_year}_{end_year}.json"
            if not cache.exists():
                cache.parent.mkdir(parents=True, exist_ok=True)
                with urllib.request.urlopen(url, timeout=300) as r:
                    cache.write_bytes(r.read())
            payload = json.loads(cache.read_text())
            headers.append(payload["header"])
            for f in payload["features"]:
                lon, lat = f["geometry"]["coordinates"][:2]
                dates, values, units, _ = monthly_series({"properties": f["properties"], "header": payload["header"],
                                                          "parameters": payload.get("parameters", {})})
                points[(lat, lon)] = pd.Series(values, index=dates)  # tile edges repeat: same point, same data
    return points, headers, units


def main(region_id="western_europe"):
    region = next(r for r in load_regions() if r["id"] == region_id)
    exported = json.loads((config.OUTPUT_DIRS["real"] / "regions" / f"{region_id}.json").read_text())
    dates = pd.to_datetime(exported["dates"])
    lat_min, lat_max, lon_min, lon_max = region["box"]
    # 2 degree cells with centers inside the box (centers at odd degrees), as edges
    centers_lat = np.arange(-89, 90, 2)[(np.arange(-89, 90, 2) >= lat_min) & (np.arange(-89, 90, 2) <= lat_max)]
    centers_lon = np.arange(-179, 180, 2)[(np.arange(-179, 180, 2) >= lon_min) & (np.arange(-179, 180, 2) <= lon_max)]
    edges = [centers_lat[0] - 1, centers_lat[-1] + 1, centers_lon[0] - 1, centers_lon[-1] + 1]
    points, headers, units = fetch_box(edges, dates[0].year, dates[-1].year)
    # Strictly inside the edges: a native point on an edge belongs half to a neighbouring cell; dropping it
    # is a small, documented difference.
    keep = {k: v for k, v in points.items() if edges[0] < k[0] < edges[1] and edges[2] < k[1] < edges[3]}
    frame = pd.DataFrame({k: v for k, v in keep.items()}).reindex(dates)
    w = np.cos(np.deg2rad([k[0] for k in frame.columns]))
    series = (frame.values * w).sum(1) / (np.isfinite(frame.values) * w).sum(1)
    anomalies, report = regional_report(series, dates.values, units)
    ours = exported["variables"]["t2m"]
    a, b = np.asarray(anomalies, float), np.array([np.nan if x is None else x for x in ours["series"]["anomaly"]])
    ok = np.isfinite(a) & np.isfinite(b)
    keys = ("slope_per_decade", "ci_low_per_decade", "ci_high_per_decade", "pvalue", "lag1_autocorrelation")
    out = {
        "region": region_id, "box": region["box"], "power_box_edges": edges,
        "period": [exported["dates"][0], exported["dates"][-1]], "n_months": len(dates),
        "power_sources_header": sorted({s for h in headers for s in h.get("sources", [])}),
        "power_api_version": headers[0].get("api", {}).get("version"), "power_units": units,
        "power_time_standard": headers[0].get("time_standard"),
        "power_native_points": len(keep), "power_missing_values": int(np.isnan(frame.values).sum()),
        "ecodelta": {k: ours["report"][k] for k in keys},
        "power": {k: report[k] for k in keys},
        "slope_difference_per_decade": ours["report"]["slope_per_decade"] - report["slope_per_decade"],
        "anomaly_correlation": float(np.corrcoef(a[ok], b[ok])[0, 1]),
        "anomaly_rms_difference": float(np.sqrt(np.mean((a[ok] - b[ok]) ** 2))),
        "anomaly_max_abs_difference": float(np.max(np.abs(a[ok] - b[ok]))),
    }
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main(*sys.argv[1:2])
