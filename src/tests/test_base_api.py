import shutil
import tempfile
import pytest
from pathlib import Path
from src.common.base_api import CachedDataAPI

class DummyCachedDataAPI(CachedDataAPI):
    def __init__(self, database_path):
        super().__init__(database_path)
        self.counter = 0

    def update(self):
        self.counter += 1

    def _peek_source(self, *args, **kwargs):
        # Just return a dummy dict based on args for testing
        return {"counter": self.counter}

    def _setup_source(self, dist_folder: Path, peeked_sources, *args, **kwargs):
        counter = peeked_sources['counter']

        # Simulate saving a source file
        file_path = dist_folder / f"source_{counter}.txt"
        file_path.write_text(f"source data {counter}")
        return {"source": str(file_path)}

    def _setup_data(self, dist_folder: Path, source_paths, *args, **kwargs):
        # Read the file from peeked_sources['dummy']
        dummy_file_path = Path(source_paths['source'])
        counter = dummy_file_path.read_text().split(' ')[-1]
        
        # Simulate saving a derived file
        file_path = dist_folder / f"derived_{counter}.txt"
        file_path.write_text(f"derived data {counter}")
        return {"derived": str(file_path)}

    def _get(self, *args, data_paths=None, **kwargs):
        # Return the contents of the derived file
        with open(data_paths["derived"], "r") as f:
            return {"derived": f.read().split(' ')[-1]}
        

@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_db"
    yield db_path
    shutil.rmtree(temp_dir)


def test_meta_populated_correctly(temp_db):
    db = DummyCachedDataAPI(temp_db)
    db.setup("foo", bar=1)
    meta = db.meta

    # Check all required meta keys exist
    for key in db.META_KEYS:
        assert key in meta

    # Check hashes and args are populated
    assert len(meta["hashes"]) == 1
    assert len(meta["args"]) == 1
    assert isinstance(meta["hashes"][0], str)
    assert isinstance(meta["args"][0], dict)
    assert meta["args"][0]["args"] == ("foo",)
    assert meta["args"][0]["kwargs"] == {"bar": 1}
    assert isinstance(meta["args"][0]["peeked_source"], dict)

    # Check source_data_paths and derived_data_paths are populated
    assert len(meta["source_data_paths"]) == 1
    assert len(meta["derived_data_paths"]) == 1
    assert "source" in meta["source_data_paths"][0]
    assert "derived" in meta["derived_data_paths"][0]
    assert Path(meta["source_data_paths"][0]["source"]).exists()
    assert Path(meta["derived_data_paths"][0]["derived"]).exists()


def test_meta_history_on_update_and_different_args(temp_db):
    db = DummyCachedDataAPI(temp_db)
    # Initial setup
    db.setup("foo", bar=1)
    meta1 = db.meta.copy()
    assert len(meta1["hashes"]) == 1
    assert meta1["args"][0]["args"] == ("foo",)
    assert meta1["args"][0]["kwargs"] == {"bar": 1}
    first_hash = meta1["hashes"][0]

    # Call setup() again with same args (should NOT add new version)
    db.setup("foo", bar=1)
    meta2 = db.meta.copy()
    assert meta2 == meta1  # No new version added

    # Call update() to change internal state, then setup() again (should add new version)
    db.update()
    db.setup("foo", bar=1)
    meta3 = db.meta.copy()
    assert len(meta3["hashes"]) == 2
    assert meta3["hashes"][0] == first_hash
    assert meta3["args"][1]["args"] == ("foo",)
    assert meta3["args"][1]["kwargs"] == {"bar": 1}
    # The peeked_source should reflect the updated counter
    assert meta3["args"][1]["peeked_source"]["counter"] == 1
    # Source and derived data paths should be different for the new version
    assert meta3["source_data_paths"][0] != meta3["source_data_paths"][1]
    assert meta3["derived_data_paths"][0] != meta3["derived_data_paths"][1]
    # Files for both versions should exist
    assert Path(meta3["source_data_paths"][0]["source"]).exists()
    assert Path(meta3["source_data_paths"][1]["source"]).exists()
    assert Path(meta3["derived_data_paths"][0]["derived"]).exists()
    assert Path(meta3["derived_data_paths"][1]["derived"]).exists()
    # The derived file contents should match the counter
    with open(meta3["derived_data_paths"][0]["derived"]) as f0, open(meta3["derived_data_paths"][1]["derived"]) as f1:
        assert f0.read().strip() == "derived data 0"
        assert f1.read().strip() == "derived data 1"
    # The hashes should be different for the two versions
    assert meta3["hashes"][0] != meta3["hashes"][1]

    # Call update() and setup() with different args/kwargs (should add another version)
    db.update()
    db.setup("bar", baz=2)
    meta4 = db.meta.copy()
    assert len(meta4["hashes"]) == 3
    # The new args/kwargs should be reflected in the last entry
    assert meta4["args"][2]["args"] == ("bar",)
    assert meta4["args"][2]["kwargs"] == {"baz": 2}
    # The peeked_source should reflect the updated counter
    assert meta4["args"][2]["peeked_source"]["counter"] == 2
    # Source and derived data paths should be different for the new version
    assert meta4["source_data_paths"][2] != meta4["source_data_paths"][1]
    assert meta4["derived_data_paths"][2] != meta4["derived_data_paths"][1]
    # Files for all versions should exist
    assert Path(meta4["source_data_paths"][2]["source"]).exists()
    assert Path(meta4["derived_data_paths"][2]["derived"]).exists()
    # The derived file contents should match the counter
    with open(meta4["derived_data_paths"][2]["derived"]) as f2:
        assert f2.read().strip() == "derived data 2"
    # The hashes should all be unique
    assert len(set(meta4["hashes"])) == 3

    # Call setup() with yet another set of args/kwargs
    db.setup("baz", qux=3)
    meta5 = db.meta.copy()
    assert len(meta5["hashes"]) == 4
    # The new args/kwargs should be reflected in the last entry
    assert meta5["args"][3]["args"] == ("baz",)
    assert meta5["args"][3]["kwargs"] == {"qux": 3}
    # The peeked_source should reflect the updated counter
    assert meta5["args"][3]["peeked_source"]["counter"] == 2  # counter not incremented since update() wasn't called
    # Source and derived data paths should be different for the new version
    assert meta5["source_data_paths"][3] != meta5["source_data_paths"][2]
    assert meta5["derived_data_paths"][3] != meta5["derived_data_paths"][2]
    # Files for all versions should exist
    assert Path(meta5["source_data_paths"][3]["source"]).exists()
    assert Path(meta5["derived_data_paths"][3]["derived"]).exists()
    # The derived file contents should match the counter
    with open(meta5["derived_data_paths"][3]["derived"]) as f3:
        assert f3.read().strip() == "derived data 2"
    # The hashes should all be unique
    assert len(set(meta5["hashes"])) == 4


def test_get_returns_correct_data_for_each_version(temp_db):
    db = DummyCachedDataAPI(temp_db)
    # Initial setup
    db.setup("foo", bar=1)
    # Should return the derived value for counter=0
    result_v0 = db.get()
    assert result_v0 == {"derived": "0"}

    # Call update() and setup() again (should add new version)
    db.update()
    db.setup("foo", bar=1)
    # Should return the derived value for counter=1 (latest version)
    result_v1 = db.get()
    assert result_v1 == {"derived": "1"}

    # Should also be able to get previous version by version index
    result_v0_again = db.get(version=0)
    assert result_v0_again == {"derived": "0"}
    result_v1_again = db.get(version=1)
    assert result_v1_again == {"derived": "1"}

    # If we call setup with new args, should get new version
    db.update()
    db.setup("bar", baz=2)
    result_v2 = db.get()
    assert result_v2 == {"derived": "2"}
    # Check all versions
    assert db.get(version=0) == {"derived": "0"}
    assert db.get(version=1) == {"derived": "1"}
    assert db.get(version=2) == {"derived": "2"}
