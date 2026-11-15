# Open problems and things not verified

- `meta.json` has no `is_mock`. The DEMO DATA banner shows unless `synthetic` is `false` AND `source` is `"real"`.
- Real data (`ecodelta-engine/web_data/`) does not exist yet. The app has only been checked with the synthetic fixture.
- The fixture's `products` entry is a placeholder (`"not found"`). Real product names, versions and DOIs have not been seen yet.
- Font: Poppins (OFL-1.1) is the only typeface, self-hosted (Latin subset, weights 400, 600 and 700). Characters outside the Latin subset fall back to Arial or Helvetica.
- `maplibre-gl` is BSD-3-Clause, not MIT/Apache-2.0. It is part of the fixed stack, so it stays; listed in THIRD_PARTY.md.
- The Claude desktop app's built-in browser has WebGL turned off, so the map was checked in headless Chromium (Playwright, SwiftShader) instead. Browsers without WebGL now see a message in place of the map.
- Cell details on the map appear on mouse hover or tap only. Keyboard and screen reader users choose regions with the region list, and they cannot read single cells yet.
- Map cells are clipped at 85° north and south so they stay finite in Web Mercator. The polar caps above that are not drawn.
- No coastline file yet (`public/data/coastlines.geojson`), so the map has no land outlines.
- The chart's trend line has the engine's slope but no exported intercept. It is drawn through zero at the middle of the period, which fits because the anomalies are relative to the 2001-2025 average. Only the slope carries meaning, and the chart key says so. TODO: ask the engine to export an intercept if a fitted line is wanted.
- On the flat map, polar regions (Arctic, Antarctica) are strongly stretched by Web Mercator. The globe view shows them better.
- The accessibility check was a custom Playwright script, not a full audit tool like axe. It covered text contrast (WCAG AA), sideways overflow at 360, 768, 1024 and 1366 px, and visible keyboard focus. Since design pass v2 it also checks chart text inside the SVG; it does not check the map canvas or screen reader output. No real screen reader was tried.
- Switching variables on the map still causes long tasks of about 50 to 120 ms in headless Chromium with software WebGL (SwiftShader). Most of it is MapLibre loading about 15,000 cell polygons; the new glow and fade effects made no measurable difference. Not measured on a real GPU.

## Content and honesty pass (schema 1.2.0)

- The compare files have no difference series D(t), only its slope, CI and p. The Compare page shows the two regions' exported 12-month means and says "not available" for the difference series; the browser does not compute it. TODO: ask the engine to export D(t) per pair (or per region pair on demand).
- In the fixture most provenance fields are null (collection, DOI, source units, native and temporal resolution, retrieval dates); the About page shows them as "not available". Product is "FIXTURE", version "0". Real values have not been seen yet.
- The "approximate study area" tag is shown for every region with `kind: "approximate_box"`, including Global, because the data marks Global as a box too.
- The Earth system profile and "signals found together" line use the fixture's synthetic results. The rule is fixed: variables with moderate or strong evidence and a direction, in catalog order.
- The ranking's magnitude bar shows each variable's own trend per decade and CI on its own scale (bars are not comparable across variables; the effect size number is the comparable measure within one region).
- The Playwright web server builds with `ALLOW_FIXTURE=1`; a plain `npm run build` stops on demo data.
