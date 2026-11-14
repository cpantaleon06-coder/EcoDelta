# Problems log

What went wrong or could not be verified, and how it was handled.

| When | Problem | Handling |
|---|---|---|
| Step 1 | No commits yet: commits for this project need the owner's go-ahead (target repo `cpantaleon06-coder/EcoDelta`). | `git init` only. `meta.json` will report the commit as missing until a first commit exists. |
| Step 2 | `nasa-data/data/processed/` is still empty (download running), so there is no real `manifest.json` to mirror. | Fixture manifest copies the keys written by `assemble()` in `nasa-data/scripts/build_coarse_grid.py`; a test pins that key set. Re-check when the real manifest appears. |
| Step 2 | Fixture land mask is a set of crude boxes, not real coastlines. | Fine for tests; real land/ocean NaN patterns come from GLDAS. |
| Step 2 | Fixture precipitation is NaN poleward of 80 degrees. The data session's DATASETS.md (written later) says real IMERG is missing only at abs(lat) >= 89.25 and the 2 degree rows at +-89 keep a value, so the real precip grid has no NaN rows. | Kept on purpose to exercise NaN handling; real coverage comes from the data. |
| Step 3 | Fixture region coverage is unrealistic (box land mask: Mexico shows 100% land). | Real `n_valid_cells` and `covered_fraction` must be re-read after the real run. |
| Step 3 | Plain-language text in `variables.yaml` has not been reviewed by anyone outside the engine team. | Marked `status: provisional` in the file. |
| Step 4 | `grid_trends` runs slower when 5 variables run in parallel (t2m 121 s vs 52.6 s alone in trendkit's benchmark); the data download was also running on the same machine. | Total wall time still about 2 minutes; logged in docs/TRENDKIT_ISSUES.md. |
| Step 5 | Ranking puts the p-value before effect size (as specified), so effect size almost never changes the order. | Documented in `meta.methods.ranking`; changing it is one line in `screen._key`. |
| Step 6 | `meta.engine.commit` is null because this repository has no commit yet. | Will fill in automatically after the first commit. |
| Step 6 | Real data not built yet: on 2026-11-14 the download had finished 162 of 297 MERRA-2 months and had not started IMERG or GLDAS (the data session's own estimate was about 9 hours in total). | `web_data/` (real) does not exist yet; only `web_data_fixture/`. |
