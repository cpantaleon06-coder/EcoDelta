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
    term: 'Anomaly',
    text: 'The difference between a monthly value and the usual value for that calendar month. Zero means a normal month.',
  },
];
