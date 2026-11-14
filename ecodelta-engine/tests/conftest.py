import pytest

from ecodelta_engine.fixtures import write_fixture


@pytest.fixture(scope="session")
def fixture_root(tmp_path_factory):
    """Synthetic processed data, written once per test session."""
    root = tmp_path_factory.mktemp("fixture")
    write_fixture(root)
    return root
