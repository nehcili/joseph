import shutil
import tempfile
import pytest
import polars as pl
from common.data.base_api import CachedDataAPI, LazyPolarDataAPI

class DummyAPI(CachedDataAPI):
    def _setup_source(self, source_path, *args, **kwargs):
        # No-op for testing
        pass

    def _setup_data(self, source_path, *args, **kwargs):
        # Return a dict of polars DataFrames
        df1 = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
        df2 = pl.DataFrame({"x": [10, 20]})
        return {"table1": df1, "table2": df2}

    def _get(self, data_path=None):
        # Read all parquet files in data_path
        data = {}
        for file in data_path.glob("*.parquet"):
            name = file.stem
            data[name] = pl.read_parquet(file)
        return data

@pytest.fixture
def temp_db_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)

def test_setup_and_get_creates_and_reads_data(temp_db_dir):
    api = DummyAPI(temp_db_dir)
    api.setup(foo=1)
    version = api.get_version()
    assert version == 0
    data = api.get()
    assert "table1" in data and "table2" in data
    assert isinstance(data["table1"], pl.DataFrame)
    assert data["table1"].shape == (2, 2)
    assert data["table2"].shape == (2, 1)

def test_setup_idempotent(temp_db_dir):
    api = DummyAPI(temp_db_dir)
    api.setup(foo=1)
    v1 = api.get_version()
    api.setup(foo=1)
    v2 = api.get_version()
    assert v1 == v2  # No new version if args are the same

def test_setup_new_version_on_args_change(temp_db_dir):
    api = DummyAPI(temp_db_dir)
    api.setup(foo=1)
    v1 = api.get_version()
    api.setup(foo=2)
    v2 = api.get_version()
    assert v2 == v1 + 1

def test_get_param_and_history(temp_db_dir):
    api = DummyAPI(temp_db_dir)
    api.setup(foo=1)
    api.setup(foo=2)
    assert api.get_param(1)["kwargs"]["foo"] == 1
    assert api.get_param(2)["kwargs"]["foo"] == 2
    history = api.get_history()
    assert len(history) == 2
    assert history[0]["kwargs"]["foo"] == 1
    assert history[1]["kwargs"]["foo"] == 2

def test_get_raises_for_missing_version(temp_db_dir):
    api = DummyAPI(temp_db_dir)
    api.setup(foo=1)
    with pytest.raises(FileNotFoundError):
        api.get(version=1)  # must call setup first

def test_lazy_polar_data_api_reads_lazyframes(temp_db_dir):
    class DummyLazy(LazyPolarDataAPI):
        def _setup_source(self, source_path, *args, **kwargs):
            pass
        def _setup_data(self, source_path, *args, **kwargs):
            df = pl.DataFrame({"a": [1, 2]})
            return {"lazy": df}

    api = DummyLazy(temp_db_dir)
    api.setup()
    data = api.get()
    assert "lazy" in data
    assert isinstance(data["lazy"], pl.LazyFrame)
    # Collect to verify data
    df = data["lazy"].collect()
    assert df.shape == (2, 1)
    assert df["a"].to_list() == [1, 2]