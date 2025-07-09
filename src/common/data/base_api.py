from abc import ABC, abstractmethod
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import polars as pl

class BaseDataAPI(ABC):
    @abstractmethod
    def setup(self, *args, **kwargs):
        """
        Set up the database connection or initialize the database.
        """
        pass

    @abstractmethod
    def get(self, *args, **kwargs):
        """
        Fetch data from the database for downstream users.
        """
        pass


class CachedDataAPI(BaseDataAPI):
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.meta_path = self.database_path / "meta.json"
        self.source_path = self.database_path / "source"
        self.data_path = self.database_path / "data"
        self._load_meta()

    def _load_meta(self):
        if self.meta_path.exists():
            with open(self.meta_path, "r") as f:
                self.meta = json.load(f)
        else:
            self.meta = {
                "history": [],
                "params": [],
                "version": -1
            }

    def _save_meta(self):
        with open(self.meta_path, "w") as f:
            json.dump(self.meta, f, indent=2)

    def _hash_args(self, args, kwargs):
        # Use json to ensure consistent hashing
        args_repr = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(args_repr.encode()).hexdigest()

    def setup(self, *args, **kwargs):
        os.makedirs(self.source_path, exist_ok=True)
        os.makedirs(self.data_path, exist_ok=True)
        args_hash = self._hash_args(args, kwargs)
        if self.meta["history"] and self.meta["history"][-1] == args_hash:
            # Same args as last time, do nothing
            return
        # Version up
        self.meta["version"] += 1
        self.meta["history"].append(args_hash)
        self.meta["params"].append({"args": args, "kwargs": kwargs})

        # Prepare versioned folders
        version_str = f"v{self.meta['version']}"
        version_source = self.source_path / version_str
        version_data = self.data_path / version_str
        os.makedirs(version_source, exist_ok=True)
        os.makedirs(version_data, exist_ok=True)

        # User-defined source setup
        self._setup_source(version_source, *args, **kwargs)
        # User-defined data setup
        data_dict = self._setup_data(version_source, *args, **kwargs)
        for fname, df in data_dict.items():
            if not isinstance(df, pl.DataFrame):
                raise ValueError(f"Value for {fname} is not a polars DataFrame")
            df.write_parquet(version_data / f"{fname}.parquet")

        self._save_meta()

    def get_version(self) -> int:
        return self.meta["version"]

    def get_param(self, version: int) -> Dict[str, Any]:
        if 0 <= version < len(self.meta["params"]):
            return copy.deepcopy(self.meta["params"][version])
        raise IndexError("Version out of range")

    def get_history(self) -> List[Dict[str, Any]]:
        return self.meta["params"]
    
    def get(self, *args, version=None, **kwargs) -> Dict[str, pl.LazyFrameDataFrame]:
        """
        Fetch data for a specific version (default: current version).
        """
        if version is None:
            version = self.get_version()
        version_str = f"v{version}"
        version_data_path = self.data_path / version_str
        if not version_data_path.exists():
            raise FileNotFoundError(f"Data for version {version} not found at {version_data_path}")
        
        return self._get(*args, data_path=version_data_path, **kwargs)
    
    # The user must implement these two methods in their subclass
    def _get(self, *args, version=None, **kwargs) -> Dict[str, pl.DataFrame]:
        raise NotImplementedError(
            "This method should be implemented in the subclass to return actual data."
        )

    def _setup_source(self, source_path: Path, *args, **kwargs):
        raise NotImplementedError

    def _setup_data(self, source_path: Path, *args, **kwargs) -> Dict[str, pl.DataFrame]:
        raise NotImplementedError
    
class LazyPolarDataAPI(CachedDataAPI):
    def _get(self, data_path=None) -> Dict[str, pl.LazyFrame]:
        data = {}
        for file in data_path.glob("*.parquet"):
            name = file.stem
            # Read the parquet file into a Polars DataFrame lazily.
            data[name] = pl.scan_parquet(file)
        return data
