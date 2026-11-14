import numpy as np
import pytest
from statsmodels.stats.multitest import multipletests

from trendkit.fdr import fdr_bh


@pytest.mark.parametrize("seed", range(3))
def test_matches_statsmodels(seed):
    rng = np.random.default_rng(seed)
    p = np.concatenate([rng.uniform(size=400), rng.uniform(0, 0.002, size=50)])
    rng.shuffle(p)
    qv, sig = fdr_bh(p, 0.05)
    reject, ref, _, _ = multipletests(p, alpha=0.05, method="fdr_bh")
    np.testing.assert_allclose(qv, ref, rtol=1e-12)
    np.testing.assert_array_equal(sig, reject)


def test_nan_is_skipped_and_shape_kept():
    rng = np.random.default_rng(5)
    p = rng.uniform(0, 0.1, size=(6, 7))
    p[0, :] = np.nan
    qv, sig = fdr_bh(p)
    assert qv.shape == sig.shape == (6, 7)
    assert np.isnan(qv[0]).all() and not sig[0].any()
    _, ref, _, _ = multipletests(p[1:].ravel(), method="fdr_bh")
    np.testing.assert_allclose(qv[1:].ravel(), ref, rtol=1e-12)


def test_edge_cases():
    qv, sig = fdr_bh(np.full(5, np.nan))
    assert np.isnan(qv).all() and not sig.any()
    qv, sig = fdr_bh([])
    assert qv.size == 0
    qv, sig = fdr_bh([0.01, 0.01, 0.01])  # ties
    np.testing.assert_allclose(qv, 0.01)
    assert fdr_bh(0.03)[1]  # scalar
