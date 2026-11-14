import json
import math

import numpy as np

from ecodelta_engine.export import clean, rnd, write_json


def test_rnd_significant_digits_and_nan():
    assert rnd(0.271713678) == 0.2717 and rnd(-1.40456) == -1.405 and rnd(8.581125e-39) == 8.581e-39
    assert rnd(float("nan")) is None and rnd(math.inf) is None and rnd(None) is None


def test_clean_converts_numpy_and_is_deterministic(tmp_path):
    obj = {"b": np.float32(0.123456), "a": [np.int64(3), np.bool_(True), np.nan], "c": (1.0, 2)}
    assert clean(obj) == {"b": 0.1235, "a": [3, True, None], "c": [1.0, 2]}
    write_json(tmp_path / "x.json", obj)
    first = (tmp_path / "x.json").read_text()
    write_json(tmp_path / "x.json", dict(reversed(list(obj.items()))))
    assert (tmp_path / "x.json").read_text() == first
    assert list(json.loads(first)) == ["a", "b", "c"]
