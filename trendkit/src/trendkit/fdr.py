"""Benjamini-Hochberg false discovery rate control."""

import numpy as np


def fdr_bh(pvalues, q=0.05):
    """Benjamini-Hochberg (1995) adjusted p-values (q-values) and rejection mask.

    Formula: sort the m valid p-values ascending, p_(1) <= ... <= p_(m). Then
        q_(i) = min over j >= i of ( m * p_(j) / j ), capped at 1,
    and a test is a discovery when q_(i) <= q. On average, at most a fraction q of
    the discoveries are false.

    Parameters
    ----------
    pvalues : array-like of any shape; NaN marks cells that were not tested
        (for example land cells or cells with too little data).
    q : float, target false discovery rate.

    Returns
    -------
    qvalues : ndarray, same shape as `pvalues`, NaN where the input is NaN.
    significant : bool ndarray, same shape, False where the input is NaN.

    Assumptions: the tests are independent or positively dependent. NaN
    entries do not count toward m.
    """
    p = np.asarray(pvalues, dtype=float)
    flat = p.ravel()
    idx = np.flatnonzero(~np.isnan(flat))
    order = idx[np.argsort(flat[idx], kind="stable")]
    m = order.size
    adjusted = flat[order] * m / np.arange(1, m + 1)
    adjusted = np.minimum(np.minimum.accumulate(adjusted[::-1])[::-1], 1.0)
    qvalues = np.full(flat.shape, np.nan)
    qvalues[order] = adjusted
    qvalues = qvalues.reshape(p.shape)
    return qvalues, np.nan_to_num(qvalues, nan=np.inf) <= q
