"""MERRA-2 M2TMNXSLV granule names per month from CMR, and global attributes of one granule per stream."""
import json, re, sys
from collections import OrderedDict
import earthaccess

earthaccess.login(strategy="netrc")
grans = earthaccess.search_data(short_name="M2TMNXSLV", version="5.12.4", temporal=("2001-01", "2025-09-28"))
rows = []
for g in grans:
    m = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:7]
    if "2001-01" <= m <= "2025-09":
        url = [u["URL"] for u in g["umm"].get("RelatedUrls", []) if "opendap" in u["URL"].lower()][0]
        rows.append((m, g["umm"]["GranuleUR"], url))
rows.sort()
streams = OrderedDict()
for m, name, url in rows:
    s = re.search(r"MERRA2_(\d{3})", name).group(1)
    streams.setdefault(s, []).append(m)
print("n granules:", len(rows))
for s, ms in streams.items():
    print(f"stream {s}: {len(ms)} months, {ms[0]}..{ms[-1]}" + ("" if len(ms) < 12 else ""), [] if len(ms) > 40 else ms)
session = earthaccess.get_requests_https_session()
attrs = {}
for s, ms in streams.items():
    url = next(u for m, n, u in rows if m == ms[0])
    r = session.get(url + ".dmr.xml", timeout=120)
    keep = {}
    for k in ("Filename", "History", "Source", "Title", "ProductionDateTime", "GranuleID", "VersionID", "ProcessingLevel", "Contact"):
        mm = re.search(rf'name="{k}"[^>]*>\s*<Value>(.*?)</Value>', r.text, re.S)
        if mm: keep[k] = mm.group(1).strip()[:200]
    attrs[s] = (ms[0], r.status_code, keep)
print(json.dumps(attrs, indent=1))
json.dump({"rows": rows}, open(sys.argv[1], "w"))
