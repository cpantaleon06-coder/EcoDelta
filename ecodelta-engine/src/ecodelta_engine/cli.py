"""Command line: python -m ecodelta_engine build --source fixture|real ; ... validate --source fixture|real"""

import argparse
import json
import sys

from . import config
from .catalog import build_catalog, parse_datasets_md, read_variables_yaml
from .compute import compare_regions, compute_all, sanity_checks
from .export import export
from .fixtures import write_fixture
from .load import available, manifest_sha256, read_manifest
from .quality import load_gate, statuses
from .regions import load_regions
from .screen import period_info, screen_region

SIZE_BUDGET = 25 * 1024**2


def source_root(source: str):
    if source == "fixture":
        if not (config.processed_dir(config.FIXTURE_DIR) / "manifest.json").exists():
            print(f"writing fixture data to {config.FIXTURE_DIR}")
            write_fixture()
        return config.FIXTURE_DIR
    return config.DATA_DIR


def apply_holds(manifest: dict, plain: dict) -> tuple[dict, dict, dict]:
    """Drop variables whose variables.yaml entry has `hold` (owner decision): (manifest, plain, {var: reason})."""
    held = {k: v["hold"] for k, v in sorted(plain.items()) if v.get("hold")}
    return ({k: v for k, v in manifest.items() if k not in held},
            {k: v for k, v in plain.items() if k not in held}, held)


def build(source: str, allow_missing: bool = False, workers: int | None = None) -> int:
    root = source_root(source)
    print(f"source={source} data={root}")
    manifest = read_manifest(root)
    plain = read_variables_yaml()
    held = {}
    if source == "real":  # the fixture keeps every variable so the tests cover all of them
        manifest, plain, held = apply_holds(manifest, plain)
        for k, reason in held.items():
            print(f"HELD (not exported): {k}: {reason}")
    not_in_manifest = sorted(set(plain) - set(manifest))
    if not_in_manifest and allow_missing:
        plain = {k: v for k, v in plain.items() if k in manifest}
    catalog = build_catalog(manifest, parse_datasets_md(config.datasets_doc(root)), plain)
    have, missing_files = available(root, manifest)
    missing = sorted(missing_files + not_in_manifest + list(held))
    if missing:
        print(f"MISSING variables (listed in meta.json): {missing}")
    if not have:
        print("no variable files found; nothing to build")
        return 1
    regions = load_regions()
    gate = load_gate(source, have, regions)  # fail before the slow part
    ranges = {k: v["plausible_range"] for k, v in plain.items()}
    results, timing = compute_all(root, manifest, have, regions, ranges, workers)
    print("timing:", json.dumps(timing))
    sanity, blockers = sanity_checks(results)
    print("sanity:", json.dumps(sanity, indent=1))
    if blockers:
        print("BLOCKERS, nothing exported:\n  " + "\n  ".join(blockers))
        return 2
    period = period_info(next(iter(results.values()))["dates"])
    quality = statuses(gate, results, regions)
    held_pairs = [(v, r) for v in quality for r, s in quality[v].items() if s["status"] == "held"]
    if held_pairs:
        print(f"quality gate: {len(held_pairs)} (variable, region) pairs held, not exported as results")
    ranked = {r["id"]: screen_region(r, {v: results[v]["regions"][r["id"]] for v in results
                                         if quality[v][r["id"]]["status"] != "held"}, catalog, period)
              for r in regions}
    compare = {v: compare_regions(results[v], regions) for v in results}
    out = config.OUTPUT_DIRS[source]
    info = export(out, source, catalog, regions, results, ranked, period, missing, timing, sanity,
                  manifest_sha256(root), compare, quality, gate)
    print(f"wrote {info['n_files']} files, {info['total_bytes'] / 1024**2:.2f} MB to {out}")
    print("largest:", info["largest"])
    print(f"compare/: {info['compare_bytes'] / 1024**2:.2f} MB")
    if info["total_bytes"] > SIZE_BUDGET:
        print(f"WARNING: over the {SIZE_BUDGET / 1024**2:.0f} MB budget")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ecodelta_engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="compute everything and write web_data/ (or web_data_fixture/)")
    b.add_argument("--source", choices=["fixture", "real"], required=True)
    b.add_argument("--allow-missing", action="store_true",
                   help="build even if manifest.json lacks variables that variables.yaml describes")
    b.add_argument("--workers", type=int, default=None)
    v = sub.add_parser("validate", help="check exported files against schema/ and recompute golden numbers")
    v.add_argument("--source", choices=["fixture", "real"], required=True)
    args = ap.parse_args(argv)
    if args.cmd == "build":
        return build(args.source, args.allow_missing, args.workers)
    from .validate import validate
    return validate(args.source)


if __name__ == "__main__":
    sys.exit(main())
