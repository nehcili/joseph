import os
import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from common.base_api import LazyPolarsDataAPI

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

    def _setup_source(self, peeked, source_path):
        """
        Downloads all files in peeked source and saves to source_path.
        """
        os.makedirs(source_path, exist_ok=True)
        for file_name, (url, fname) in peeked.items():
            dest = os.path.join(source_path, fname)
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(dest, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)