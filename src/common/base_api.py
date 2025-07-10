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
    """
    meta data contains
    - history: list of hashes of args and kwargs used to set up the database
    - params: list of dicts with args and kwargs used to set up the database
    - version: current version of the database
    - source_data_paths: dict of source data paths
    """
    META_KEYS = (
        # All lists are sorted by version
        # the index of the list is the version number
        "hashes",  # A list of dicts with args and kwargs used to set up the database
        "args",  # A list of hashes of args and kwargs used to set up the database         
        "source_data_paths",  # A list of dicts of source data paths
        "derived_data_paths",  # A list of dicts of derived data paths
    )
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.meta_path = self.database_path / "meta.json"
        self.source_path = self.database_path / "source"
        self.data_path = self.database_path / "data"
        self._load_meta()

    def _check_meta(self):
        missing = [key for key in self.META_KEYS if key not in self.meta]
        if missing:
            raise ValueError(f"Meta file is missing keys: {missing}. Please check the meta file at {self.meta_path}.")

    def _load_meta(self):
        if self.meta_path.exists():
            with open(self.meta_path, "r") as f:
                self.meta = json.load(f)

            self._check_meta()
        else:
            self.meta = {
                "hashes": [],
                "args": [],
                "source_data_paths": [],
                "derived_data_paths": [],
            }

    def _save_meta(self):
        # Ensure all required keys are present
        self._check_meta()
        
        # save the meta information to a JSON file
        with open(self.meta_path, "w") as f:
            json.dump(self.meta, f, indent=2)

    def _hash_args(self, args, kwargs, peeked_source_dict):
        # Use json to ensure consistent hashing
        args_repr = json.dumps({"args": args, "kwargs": kwargs, "peeked_source": peeked_source_dict}, sort_keys=True, default=str)
        return hashlib.sha256(args_repr.encode()).hexdigest()

    def get_version(self) -> int:
        return len(self.meta["hashes"]) - 1

    def get_args(self, version: int=-1) -> Dict[str, Any]:
        raise copy.deepcopy(self.meta["args"][version])

    def get_hash(self, version: int=-1) -> List[Dict[str, Any]]:
        return self.meta["hashes"][version]
    
    def get_source_data_paths(self, version: int=-1) -> Dict[str, str]:
        return self.meta["source_data_paths"][version]
    
    def get_derived_data_paths(self, version: int=-1) -> Dict[str, str]:
        return self.meta["derived_data_paths"][version]

    def get(self, *args, version=None, **kwargs) -> Dict[str, Any]:
        """
        Fetch data for a specific version (default: current version).
        """
        if version is None:
            version = self.get_version()
            if version < 0:
                raise ValueError("No data available. Please call setup() first.")

        data_paths = self.get_derived_data_paths(version)
        return self._get(*args, data_paths=data_paths, **kwargs)
    

    def setup(self, *args, **kwargs):
        """
        Essentiall does the following:
        1. Creates the database folder if it doesn't exist.
        2. Loads the meta information.
        3. Checks if the current args are the same as the last time.
        4. If not, increments the version and saves the new args.
        5. Creates versioned folders for source and data.
        6. Calls user-defined methods to set up source and data.
        7. Saves the meta information.
        """
        os.makedirs(self.source_path, exist_ok=True)
        os.makedirs(self.data_path, exist_ok=True)

        peeked_source_dict = self._peek_source(*args, **kwargs)
        args_hash = self._hash_args(args, kwargs, peeked_source_dict)

        if len(self.meta["hashes"]) > 0 and self.meta["hashes"][-1] == args_hash:
            # Same args as last time, do nothing
            return
        
        # Version up
        self.meta["hashes"].append(args_hash)
        self.meta["args"].append({"args": args, "kwargs": kwargs, "peeked_source": peeked_source_dict})

        # Prepare versioned folders
        version_str = f"v{self.get_version()}"
        source_dist_folder = self.source_path / version_str
        data_dist_folder = self.data_path / version_str
        os.makedirs(source_dist_folder, exist_ok=True)
        os.makedirs(data_dist_folder, exist_ok=True)

        # User-defined source setup
        source_data_paths = self._setup_source(source_dist_folder, peeked_source_dict, *args, **kwargs)
        source_data_paths = copy.deepcopy(source_data_paths)
        self.meta["source_data_paths"].append(source_data_paths)
        
        # User-defined data setup
        source_data_paths = copy.deepcopy(source_data_paths)
        self.meta["derived_data_paths"].append(self._setup_data(data_dist_folder, source_data_paths, *args, **kwargs))

        # Finally, update meta
        self._save_meta()

    # The user must implement these two methods in their subclass
    def _get(self, *args, data_paths: Dict[str, str]=None, **kwargs) -> Dict[str, Any]:
        """
        Fetch all data for a specific version in the data_folder and return it as a dictionary.
        The keys of the dictionary are the keys of self.meta.
        """
        raise NotImplementedError(
            "This method should be implemented in the subclass to return actual data."
        )
    
    def _peek_source(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Peek at the source data without modifying it.
        This method should return a dictionary with some lazy information about the source data
        for caching purposes. For example, it could return the name and the associated data's
        latest url.

        NOTE: output must be json serializable.
        """
        raise NotImplementedError("This method should be implemented in the subclass.")

    def _setup_source(self, dist_folder: Path, peeked_sources: Dict[str, Any], *args, **kwargs) -> Dict[str, str]:
        """
        This method should do minimum processing on the source data and save it in the dist_folder.
        It must return a dictionary with the source data paths, where the keys are the names of the sources
        and the values are the paths to the processed source data files.
        """
        raise NotImplementedError

    def _setup_data(self, dist_folder: Path, source_paths: Dict[str, str], *args, **kwargs) -> Dict[str, str]:
        """
        Loads the source data from source_paths and processes it to create derived data.
        This method should return a dictionary with the derived data paths, where the keys are the names
        of the derived data and the values are the paths to the processed derived data files.
        """
        raise NotImplementedError
