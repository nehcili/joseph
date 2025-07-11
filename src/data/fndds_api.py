import os
import re
import logging
from pathlib import Path
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import polars as pl

from src.common.base_api import CachedDataAPI
from src.common.utils import download_file

logger = logging.getLogger(__name__)


class FNDDSDataAPI(CachedDataAPI):
    # Each pattern is a tuple: (file_name, pattern)
    patterns = (
        # phase 1
        ('ingredient_nutrient_values', 'FNDDS At A Glance - Ingredient Nutrient Values.xlsx'),
        ('nutrient_values', 'FNDDS At A Glance - FNDDS Nutrient Values.xlsx'),

        # phase 2
        ('foods_and_beverages', 'FNDDS At A Glance - Foods and Beverages.xlsx'),
        
        ('ingredients', 'FNDDS At A Glance - FNDDS Ingredients.xlsx'),
        ('portions_and_weights', 'FNDDS At A Glance - Portions and Weights.xlsx'),
    )
    _default_source_url = "https://www.ars.usda.gov/northeast-area/beltsville-md-bhnrc/beltsville-human-nutrition-research-center/food-surveys-research-group/docs/fndds-download-databases/"
    
    # Add Headers to Mimic a Browser
    headers = headers = (
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Referer", "https://www.ars.usda.gov/"),
    )

    def __init__(self, database_path, source_url=None):
        super().__init__(database_path)
        self.source_url = source_url or self._default_source_url

    def _peek_source(self) -> Dict[str, str]:
        """
        Navigates to the source_url and finds all .xlsx and .pdf links or files
        that match any pattern in patterns. For each pattern, selects the latest
        version (last in sorted order).
        Returns a dict: {file_name: (url, file_name)}
        """
        response = requests.get(self.source_url, allow_redirects=True, headers=dict(self.headers))
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
                result[file_name] = latest

        return result

    def _setup_source(self, dest_folder: Path, peeked_sources: Dict[str, str]=None, max_workers=5):
        """
        Downloads all files in peeked source and saves to source_path.
        """
        if peeked_sources is None:
            logger.warning("_peeked_source is None in _setup_source; nothing to download.")
            return
        
        os.makedirs(dest_folder, exist_ok=True)
        
        # save source data paths into meta
        source_data_paths = {}
        
        # Use ThreadPoolExecutor to download files concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for fname, url in peeked_sources.items():
                dest = os.path.join(dest_folder, fname + '.xlsx')
                futures[executor.submit(download_file, url, dest, dict(self.headers))] = fname
                source_data_paths[fname] = dest

            # Process results as they complete
            for future in as_completed(futures):
                filename = futures[future]
                try:
                    result = future.result()
                    if result:
                        logger.info(f"Successfully processed: {result}; name: {filename}")
                except Exception as exc:
                    logger.warning(f"{url} generated an exception: {exc}; name: {filename}")
    
        # Save the source data paths to meta
        # no need to save meta here, as it is already handled in the base class
        return source_data_paths
    
    def _setup_data(self, dest_folder: Path, source_paths: Dict[str, str]) -> Dict[str, pl.DataFrame]:
        """
        Reads all parquet files in source_path and returns a dict of LazyFrames.
        """
        os.makedirs(dest_folder, exist_ok=True)
        data = {}
        for fname, path in source_paths.items():
            if path.endswith('.xlsx') and os.path.exists(path):
                df = pl.read_excel(path, read_options={"header_row": 1})
        
                # Save each DataFrame as a parquet file in dest_folder
                parquet_path = os.path.join(dest_folder, f"{fname}.parquet")
                df.write_parquet(parquet_path)

                data[fname] = parquet_path
                logger.info(f"Saved {fname} to {parquet_path}")

        return data

    def _get(self, data_paths: Dict[str, str], lazy=True) -> Dict[str, pl.LazyFrame]:
        out = {
            file_name: pl.scan_parquet(path) for file_name, path in data_paths.items()
        }

        if not lazy:
            out = {k: v.collect() for k, v in out.items()}
        return out
