// Static explanatory copy (not results). Kept short; every result text comes from the data files.
export const EXPLAINERS = [
  {
    term: 'Trend per decade',
    text: "The typical change over 10 years, estimated with Sen's slope: the median of the slopes between all pairs of months, after the usual seasonal cycle is removed.",
  },
  {
    term: '95% confidence interval (CI)',
    text: 'The range of trend values that fit the data. If the analysis were repeated on many similar records, about 95% of such ranges would contain the true trend. A wide range means the size of the change is uncertain.',
  },
  {
    term: 'Statistically significant',
    text: 'A trend this strong would appear by chance less than 5% of the time if there were no real trend. It does not mean the change is large or important, and it says nothing about the cause.',
  },
  {
    term: 'Not significant',
    text: 'This does not mean nothing changed. The data cannot tell a trend this small apart from natural ups and downs.',
  },
  {
    term: 'False discovery rate (FDR) on the map',
    text: 'The map tests thousands of grid cells at once, so some would look significant by luck. The Benjamini-Hochberg correction keeps the expected share of false alarms among the cells marked significant at about 5%.',
  },
  {
    term: 'Evidence',
    text: 'How sure we can be that there is a trend at all, in four classes: strong (p below 0.01 and the 95% confidence interval excludes zero), moderate (p below 0.05 and the interval excludes zero), weak, and none. When less than 30% of a study area has data, strong and moderate are lowered to weak.',
  },
  {
    term: 'Magnitude and effect size',
    text: 'How big the change is: the trend per decade and the total change over the period, in the variable\'s units. The effect size divides the total change by the usual month-to-month swings, so it has no unit. A big change can come with weak evidence, and a small one with strong evidence.',
  },
  {
    term: 'Anomaly',
    text: 'The difference between a monthly value and the usual value for that calendar month. Zero means a normal month.',
  },
];

// Ranking legend and the "for experts" note on p, q and effect size.
export const EVIDENCE_LEGEND =
  'Evidence says how sure we can be that there is a trend at all: ●●● strong, ●●○ moderate, ●○○ weak, ○○○ none. Magnitude says how big the change is: the bar runs from zero to the trend per decade and the thin line is its 95% confidence interval. The two are separate: a small change can have strong evidence and a large one weak evidence.';
export const P_Q_EFFECT =
  'p tests this one regional average. q comes from the map, where every grid cell is tested and the false discovery rate correction is applied across all of them. The effect size says how big the change is compared with the usual month-to-month swings, not how sure we are.';
export const MAP_CORRELATION_NOTE =
  'Neighbouring grid cells are correlated, so among the cells marked significant after FDR the share of false discoveries can be higher than the nominal';
export const NOT_CAUSAL_LIST = [
  'It does not show what caused the change.',
  'The region is an approximate study area, not a political border.',
  'It is not a forecast: it describes the past period only.',
];
