// The ONLY place that knows the web_data format (ecodelta-engine/docs/OUTPUT_SCHEMA.md, schema 1.x).
// A schema change should be a fix in this file only.

export const SUPPORTED_SCHEMA_MAJOR = 1;

export type Verdict = 'increasing' | 'decreasing' | 'no significant trend' | 'insufficient data';
export type Tier = 0 | 1 | 2;
/** [low, high] */
export type Range = [number, number];

export interface Product {
  name: string;
  short_name: string;
  version: string;
  doi: string;
  citation: string;
  variables: string[];
}

export interface Axis {
  first: number;
  last: number;
  step: number;
  n: number;
}

export interface Meta {
  schema_version: string;
  build_date: string;
  source: 'real' | 'fixture' | string;
  synthetic: boolean;
  engine: { version: string; commit: string | null; uncommitted_changes: boolean };
  trendkit: { version: string; commit: string | null; uncommitted_changes: boolean };
  period: { start: string; end: string; n_months: number; years: number };
  grid: { resolution_deg: number; lat: Axis; lon: Axis };
  methods: Record<string, unknown>;
  products: Product[];
  variables_included: string[];
  variables_missing: string[];
  limitations: string[];
  /** 1.1.0+: hash of the data build's manifest.json */
  data?: { manifest_sha256: string | null };
}

/** 1.1.0+: where every number of a variable comes from (values are null when unknown). */
export interface Provenance {
  product_short_name: string | null;
  collection_id: string | null;
  version: string | null;
  doi: string | null;
  source_variable: string | null;
  source_units: string | null;
  units: string | null;
  displayed_units: string | null;
  native_resolution: Record<string, unknown> | null;
  grid: { resolution_deg?: number } & Record<string, unknown>;
  temporal_resolution: Record<string, unknown> | null;
  period: [string, string] | null;
  retrieved: Record<string, unknown> | null;
  processing_steps: { step: string; detail: string }[] | null;
  statistics: Record<string, unknown> | null;
  engine_commit: string | null;
  engine_uncommitted_changes: boolean | null;
  manifest_sha256: string | null;
}

export type EvidenceClass = 'strong' | 'moderate' | 'weak' | 'none' | 'insufficient data';

export interface Variable {
  id: string;
  name: string;
  definition: string;
  increase_means: string;
  units: string;
  public_unit: string;
  land_only: boolean;
  caveats: string[];
  long_name: string;
  period: [string, string];
  product: Omit<Product, 'variables'> & { source_variable: string; unit_conversion: string };
  provenance?: Provenance;
}

/** box = [lat_min, lat_max, lon_min, lon_max]; approximate, not political borders. */
export interface Region {
  id: string;
  name: string;
  phrase: string;
  box: [number, number, number, number];
  /** 1.2.0+: "approximate_box", with the label to show next to the name */
  kind?: string;
  display_note?: string;
}

export interface Grid {
  variable: string;
  slope_units: string;
  lat: Axis;
  lon: Axis;
  // flat row-major arrays: index = i_lat * lon.n + i_lon (lat south->north, lon west->east)
  slope: (number | null)[];
  ci_low: (number | null)[];
  ci_high: (number | null)[];
  p: (number | null)[];
  q: (number | null)[];
  significant: (0 | 1 | null)[];
  n_valid: number[];
}

export interface RankedVariable {
  rank: number;
  variable: string;
  name: string;
  verdict: Verdict;
  tier: Tier;
  significant: boolean;
  pvalue: number | null;
  effect_size: number | null;
  abs_effect_size: number | null;
  slope_per_decade: number | null;
  ci_per_decade: Range | null;
  public_unit: string;
  sentence: string;
  cautions: string[];
  // 1.2.0+
  evidence_class?: EvidenceClass;
  total_change?: number | null;
  standardized_change?: number | null;
  rank_by_magnitude?: number;
  cells_significant_fraction?: number | null;
}

export interface Screening {
  region_id: string;
  region_file: string;
  ranking: RankedVariable[];
  // 1.2.0+: variable ids in the two orderings
  by_evidence?: string[];
  by_magnitude?: string[];
}

/** 1.2.0+: the cells a regional mean is made of */
export interface FixedMask {
  n_cells: number;
  covered_fraction: number;
  n_valid_months: number;
  n_months: number;
  weight_share_min: number | null;
  weight_share_max: number | null;
}

export interface Answers {
  what: { variable: string; name: string; direction: 'increase' | 'decrease' | 'none detected'; verdict: Verdict };
  where: {
    region: string;
    name: string;
    box: Region['box'];
    land_only: boolean;
    n_box_cells: number;
    n_valid_cells: number;
    covered_fraction: number;
    fixed_mask?: FixedMask;
  };
  how_much: {
    period: [string, string];
    period_years: number;
    units: string;
    public_unit: string;
    slope_per_decade: number | null;
    ci_per_decade: Range | null;
    total_change: number | null;
    total_change_ci: Range | null;
    ci_level: number;
  };
  data: { n_valid_months: number | null; n_months: number | null; valid_fraction: number };
  significance: {
    verdict: Verdict;
    significant: boolean;
    pvalue: number | null;
    alpha: number;
    test: string;
    qvalue: number | null;
    cells_significant_after_fdr_fraction: number | null;
    explanation: string;
    warnings: string[];
  };
}

export interface TrendReport {
  slope_per_decade: number;
  ci_low_per_decade: number;
  ci_high_per_decade: number;
  ci_level: number;
  pvalue: number;
  kendall_tau: number;
  lag1_autocorrelation: number;
  ols: { slope_per_decade: number; ci_low_per_decade: number; ci_high_per_decade: number; pvalue: number };
  n_valid: number;
  n_total: number;
  valid_fraction: number;
  period_start: string;
  period_end: string;
  method: string;
  verdict: Verdict;
  significant: boolean;
  warnings: string[];
}

export interface RegionVariable {
  rank: number;
  score: { tier: Tier; significant: boolean; pvalue: number | null; effect_size: number | null; abs_effect_size: number | null };
  answers: Answers;
  sentence: string;
  cautions: string[];
  report: TrendReport | null;
  series: { anomaly: (number | null)[]; running_mean_12: (number | null)[] } | null;
  // 1.2.0+
  rank_by_magnitude?: number;
  evidence?: { class: EvidenceClass; ci_excludes_zero: boolean; capped_by_coverage: boolean };
  magnitude?: {
    slope_per_decade: number | null;
    total_change: number | null;
    units: string;
    residual_sd: number | null;
    standardized_change: number | null;
  };
  map_cells?: {
    n_tested: number;
    n_significant: number;
    n_significant_increasing: number;
    n_significant_decreasing: number;
    share_significant: number | null;
  };
}

export interface RegionTrend {
  slope_per_decade: number | null;
  ci_per_decade: Range | null;
  pvalue: number | null;
  evidence_class: EvidenceClass;
}

/** 1.2.0+: does the trend of region_a differ from region_b? D = A - B, tested by the engine. */
export interface ComparePair {
  region_a: string;
  region_b: string;
  verdict: 'trends differ' | 'no evidence that trends differ' | 'insufficient data';
  difference_slope_per_decade: number | null;
  difference_ci_per_decade: Range | null;
  pvalue: number | null;
  q_across_pairs: number | null;
  n_common_months: number | null;
  trend_a: RegionTrend;
  trend_b: RegionTrend;
  overlap_fraction: number;
  independent: boolean;
}

export interface CompareFile {
  variable: string;
  units: string;
  public_unit: string;
  period: [string, string];
  method: string;
  note: string;
  q_note: string;
  pairs: ComparePair[];
}

export interface RegionDetail {
  region: Region;
  dates: string[];
  variables: Record<string, RegionVariable>;
}

// ---- loading ----

const BASE = `${import.meta.env.BASE_URL}web_data/`;
const cache = new Map<string, Promise<unknown>>();

function checkVersion(path: string, data: unknown) {
  const v = (data as { schema_version?: string })?.schema_version;
  if (typeof v !== 'string' || Number(v.split('.')[0]) !== SUPPORTED_SCHEMA_MAJOR) {
    throw new Error(`${path}: unsupported schema_version ${String(v)} (this app reads ${SUPPORTED_SCHEMA_MAJOR}.x)`);
  }
}

// ids come from our own JSON, but they go into a URL: only allow plain names like "grids/t2m.json".
const SAFE_PATH = /^([a-z0-9_]+\/)?[a-z0-9_]+\.json$/i;

function getJson<T>(path: string): Promise<T> {
  if (!SAFE_PATH.test(path)) return Promise.reject(new Error(`Invalid data path: ${path}`));
  let p = cache.get(path) as Promise<T> | undefined;
  if (!p) {
    p = fetch(BASE + path).then(async (r) => {
      if (!r.ok) throw new Error(`Could not load ${path} (HTTP ${r.status}). Did you run "npm run sync-data"?`);
      const data = await r.json();
      checkVersion(path, data);
      return data as T;
    });
    p.catch(() => cache.delete(path)); // allow retry after a failure
    cache.set(path, p);
  }
  return p;
}

export const loadMeta = () => getJson<Meta>('meta.json');
export const loadCatalog = () => getJson<{ variables: Variable[] }>('catalog.json').then((c) => c.variables);
export const loadRegions = () =>
  getJson<{ note: string; regions: Region[] }>('regions.json').then(({ note, regions }) => ({ note, regions }));
export const loadGrid = (variable: string) => getJson<Grid>(`grids/${variable}.json`);
export const loadScreening = (regionId: string) => getJson<Screening>(`screening/${regionId}.json`);
export const loadRegionDetail = (regionId: string) => getJson<RegionDetail>(`regions/${regionId}.json`);
export const loadCompare = (variable: string) => getJson<CompareFile>(`compare/${variable}.json`);

/** True when the data must carry the DEMO DATA banner. */
export const isDemoData = (meta: Meta) => meta.synthetic !== false || meta.source !== 'real';
