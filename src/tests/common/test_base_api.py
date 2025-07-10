import shutil
import tempfile
import pytest
import polars as pl
from src.common.base_api import CachedDataAPI, LazyPolarsDataAPI

class DummyAPI(CachedDataAPI):
    def __init__(self, db_dir):
        super().__init__(database_path=db_dir)
        self.counter = 0

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
    
    def update(self):
        self.counter += 1

    def _peek_source(self, *args, **kwargs):
        # Return a preview of the data for testing
        return {"table1": f"preview of table1={self.counter}", "table2": f"preview of table2={self.counter}"}

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

def test_updated_setup(temp_db_dir):
    api = DummyAPI(temp_db_dir)
    api.setup(foo=1)
    assert api.counter == 0  # Counter should increment on setup
    assert api.get_version() == 0  # Version should be 0 after first setup

    api.update()  # Simulate an update
    assert api.counter == 1  # Counter should increment again
    assert api.get_version() == 0  # Version should still be 0

    api.setup(foo=1)
    assert api.counter == 1  # Counter should increment again
    assert api.get_version() == 1  # Version should still be 0
    
    api.setup(foo=2)
    assert api.get_version() == 2  # New version created

    api.setup(foo=3)
    assert api.get_version() == 3  # New version created

    api.setup(foo=3)
    assert api.get_version() == 3  # No new version if args are the same

    api.update()  # Simulate another update
    assert api.counter == 2  # Counter should increment again

    api.setup(foo=3)
    assert api.get_version() == 4  # New version created

def test_get_param_and_history(temp_db_dir):
    api = DummyAPI(temp_db_dir)
    api.setup(foo=1)
    api.setup(foo=2)
    assert api.get_param(0)["kwargs"]["foo"] == 1
    assert api.get_param(1)["kwargs"]["foo"] == 2
    history = api.get_history()
    assert len(history) == 2
    assert history[0]["kwargs"]["foo"] == 1
    assert history[1]["kwargs"]["foo"] == 2

def test_get_raises_for_missing_version(temp_db_dir):
    api = DummyAPI(temp_db_dir)
    api.setup(foo=1)
    with pytest.raises(FileNotFoundError):
        api.get(version=1)  # must call setup first

def test_peek_source_returns_preview(temp_db_dir):
    api = DummyAPI(temp_db_dir)
    preview = api._peek_source(temp_db_dir)
    assert "table1" in preview and "table2" in preview
    assert preview["table1"] == "preview of table1=0"
    assert preview["table2"] == "preview of table2=0"

def test_lazy_polar_data_api_reads_lazyframes(temp_db_dir):
    class DummyLazy(LazyPolarsDataAPI):
        def _setup_source(self, source_path, *args, **kwargs):
            pass
        def _setup_data(self, source_path, *args, **kwargs):
            df = pl.DataFrame({"a": [1, 2]})
            return {"lazy": df}
        def _peek_source(self, *args, **kwargs):
            return {"lazy": "preview of lazy"}

    api = DummyLazy(temp_db_dir)
    api.setup()
    data = api.get()
    assert "lazy" in data
    assert isinstance(data["lazy"], pl.LazyFrame)
    # Collect to verify data
    df = data["lazy"].collect()
    assert df.shape == (2, 1)
    assert df["a"].to_list() == [1, 2]

    # Test _peek_source for LazyPolarsDataAPI
    preview = api._peek_source(temp_db_dir)
    assert "lazy" in preview
    assert preview["lazy"] == "preview of lazy"
