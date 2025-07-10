from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re
from typing import Dict
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from common.base_api import LazyPolarsDataAPI
import logging

from common.utils import download_file

logger = logging.getLogger(__name__)

class FNDDSDataAPI(LazyPolarsDataAPI):
    # Each pattern is a tuple: (file_name, pattern)
    patterns = (
        # Example: ('FoodData', None),
        # Add your (file_name, pattern) tuples here
    )

    def __init__(self, database_path, source_url):
        super().__init__(database_path)
        self.source_url = source_url

    def _peek_source(self):
        """
        Navigates to the source_url and finds all .xlsx and .pdf links or files
        that match any pattern in patterns. For each pattern, selects the latest
        version (last in sorted order).
        Returns a dict: {file_name: (url, file_name)}
        """
        response = requests.get(self.source_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all .xlsx and .pdf links
        links = []
        for tag in soup.find_all(['a', 'link']):
            href = tag.get('href')
            if href and (href.endswith('.xlsx') or href.endswith('.pdf')):
                links.append(urljoin(self.source_url, href))

        result = {}
        for file_name, pattern in self.patterns:
            # If pattern is None, match all files with file_name in the link
            if pattern is None:
                matched = [l for l in links if file_name in os.path.basename(l)]
            else:
                matched = [l for l in links if re.search(pattern, os.path.basename(l))]
            if matched:
                matched_sorted = sorted(matched)
                latest = matched_sorted[-1]
                result[file_name] = (latest, os.path.basename(latest))
        return result

    def _setup_source(self, source_path, _peeked_source: Dict[str, str]=None, max_workers=5):
        """
        Downloads all files in peeked source and saves to source_path.
        """
        if _peeked_source is None:
            logger.warning("_peeked_source is None in _setup_source; nothing to download.")
            return
        
        os.makedirs(source_path, exist_ok=True)
        
        # save source data paths into meta
        source_data_paths = {}
        
        # Use ThreadPoolExecutor to download files concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = set()
            for fname, url in _peeked_source.items():
                dest = os.path.join(source_path, fname)
                futures.add(
                    executor.submit(download_file, url, dest)
                )
                source_data_paths[fname] = dest

            # Process results as they complete
            for future in as_completed(futures):
                url, filename = futures[future]
                try:
                    result = future.result()
                    if result:
                        logger.info(f"Successfully processed: {result}; file: {filename}")
                except Exception as exc:
                    logger.warning(f"{url} generated an exception: {exc}; file: {filename}")
    
        # Save the source data paths to meta
        # no need to save meta here, as it is already handled in the base class
        self.meta["source_data_paths"] = source_data_paths
    
    def _setup_data(self, source_path: str) -> Dict[str, pl.DataFrame]:
        """
        Reads all parquet files in source_path and returns a dict of LazyFrames.
        """
        data_dict = {}
        for fname in os.listdir(source_path):
            if fname.endswith('.parquet'):
                file_path = os.path.join(source_path, fname)
                data_dict[fname] = pl.scan_parquet(file_path)
        return data_dict
    

        for fname, df in data_dict.items():
            if not isinstance(df, pl.DataFrame):
                raise ValueError(f"Value for {fname} is not a polars DataFrame")
            df.write_parquet(version_data / f"{fname}.parquet")

