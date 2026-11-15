// Selection state of the Explore map, kept in the URL (?var=&region=). Pure functions so the four states
// (overview, variable, region, clear) can be tested without a map.

export interface Selection {
  /** null = overview: the plain basemap, no data layer */
  variable: string | null;
  /** 'global' = no region chosen: whole-world camera, no box highlighted */
  region: string;
}

/** Read the URL; unknown ids fall back to the overview and to the whole world. */
export function readSelection(params: URLSearchParams, variables: string[], regions: string[]): Selection {
  const v = params.get('var');
  const r = params.get('region');
  return { variable: v && variables.includes(v) ? v : null, region: r && regions.includes(r) ? r : 'global' };
}

export type Action = { type: 'variable'; id: string } | { type: 'region'; id: string } | { type: 'clear' };

/** New URL params after an action; other params are kept. Clear removes only the data layer, not the region. */
export function applyAction(params: URLSearchParams, action: Action): URLSearchParams {
  const p = new URLSearchParams(params);
  if (action.type === 'variable') p.set('var', action.id);
  else if (action.type === 'region') p.set('region', action.id);
  else p.delete('var');
  return p;
}

export interface MapView {
  showData: boolean;
  /** box to highlight; null for the whole world */
  highlight: string | null;
  /** dim the other boxes when one region is selected */
  dimOthers: boolean;
}

export const mapView = (s: Selection): MapView => {
  const highlight = s.region === 'global' ? null : s.region;
  return { showData: s.variable !== null, highlight, dimOthers: highlight !== null };
};
