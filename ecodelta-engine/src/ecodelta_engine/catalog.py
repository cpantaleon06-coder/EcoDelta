"""Variable catalog: joins manifest.json, data/catalog/variables.yaml and docs/DATASETS.md."""

import re
from pathlib import Path

import yaml

from . import config

NOT_FOUND = "not found"


def read_variables_yaml(path: Path = config.CATALOG_DIR / "variables.yaml") -> dict:
    return yaml.safe_load(path.read_text())


def parse_datasets_md(path: Path) -> dict:
    """Product rows of the DATASETS.md table, keyed by output variable, plus the citation text.

    Reads the first Markdown table whose header has "Short name", "Version", "DOI" and a
    "Variable (source -> output)" column. Returns {} when the file does not exist.
    """
    if not path.exists():
        return {}
    text = path.read_text()
    citations = [line[2:].strip() for line in text.splitlines() if line.startswith("- ") and "doi:" in line]
    rows = [[c.strip() for c in line.strip().strip("|").split("|")]
            for line in text.splitlines() if line.lstrip().startswith("|")]
    out = {}
    header = None
    for cells in rows:
        if header is None:
            if any(c.startswith("Short name") for c in cells) and any(c.startswith("DOI") for c in cells):
                header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue  # separator row
        if len(cells) != len(header):
            break  # end of the table
        row = dict(zip(header, cells))
        var_col = next(v for k, v in row.items() if k.startswith("Variable"))
        m = re.search(r"->\s*`([^`]+)`", var_col)
        if not m:
            continue
        doi = next(v for k, v in row.items() if k.startswith("DOI"))
        out[m.group(1)] = {
            "product": row.get("Product", NOT_FOUND),
            "short_name": row.get("Short name", NOT_FOUND),
            "version": row.get("Version", NOT_FOUND),
            "doi": doi or NOT_FOUND,
            "citation": next((c for c in citations if doi and doi in c), NOT_FOUND),
        }
    return out


def build_catalog(manifest: dict, datasets: dict, plain: dict | None = None) -> dict:
    """One entry per manifest variable: plain-language fields + manifest facts + product provenance.

    Fails loudly if a manifest variable has no plain-language entry or the reverse, if units
    disagree, or if DATASETS.md and the file metadata give different DOIs.
    """
    plain = read_variables_yaml() if plain is None else plain
    missing_plain = sorted(set(manifest) - set(plain))
    missing_manifest = sorted(set(plain) - set(manifest))
    if missing_plain or missing_manifest:
        raise ValueError(f"catalog/manifest mismatch: no variables.yaml entry for {missing_plain}; "
                         f"not in manifest.json: {missing_manifest}")
    catalog = {}
    for var in sorted(manifest):
        m, p = manifest[var], plain[var]
        if p["manifest_units"] != m["units"]:
            raise ValueError(f"{var}: manifest units {m['units']!r} != variables.yaml {p['manifest_units']!r}")
        d = datasets.get(var, {})
        file_doi = m.get("source_doi") or NOT_FOUND
        doi = d.get("doi", NOT_FOUND)
        if doi == NOT_FOUND and not file_doi.startswith(NOT_FOUND):
            doi = file_doi
        elif doi != NOT_FOUND and not file_doi.startswith(NOT_FOUND) and doi != file_doi:
            raise ValueError(f"{var}: DOI in DATASETS.md ({doi}) != file metadata ({file_doi})")
        catalog[var] = {
            "id": var,
            "name": p["name"],
            "definition": p["definition"],
            "increase_means": p["increase_means"],
            "units": m["units"],
            "public_unit": p["public_unit"],
            "land_only": p["land_only"],
            "caveats": p["caveats"],
            "long_name": m["long_name"],
            "period": m["time_range"],
            "product": {
                "name": d.get("product", NOT_FOUND),
                "short_name": d.get("short_name", m.get("source_product", NOT_FOUND)),
                "version": d.get("version", m.get("source_version", NOT_FOUND)),
                "source_variable": m.get("source_variable", NOT_FOUND),
                "doi": doi,
                "citation": d.get("citation", NOT_FOUND),
                "unit_conversion": m.get("unit_conversion", NOT_FOUND),
            },
        }
    return catalog
