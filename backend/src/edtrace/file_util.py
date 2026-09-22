import os
import re
import hashlib
import shutil
import time
from io import BytesIO
from urllib.parse import urlparse
import requests


def download_file(url: str, filename: str):
    """Download `url` and save the contents to `filename`.  Skip if `filename` already exists."""
    if not os.path.exists(filename):
        print(f"Downloading {url} to {filename}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
        }
        for attempt in range(50):
            response = requests.get(url, headers=headers)
            if response.status_code == 429:
                wait = 2 ** attempt
                print(f"Rate limited (429), retrying in {wait}s...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            if not response.content:
                raise ValueError(f"Empty response from {url}")
            with open(filename, "wb") as f:
                shutil.copyfileobj(BytesIO(response.content), f)
            return
        raise RuntimeError(f"Failed to download {url} after retries (rate limited)")


def cached(url: str, prefix: str) -> str:
    """Download `url` if needed and return the location of the cached file."""
    name = re.sub(r"[^\w_-]+", "_", url)
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    # Preserve the original extension (e.g. ".svg") so static file servers can
    # infer the correct Content-Type; without it, browsers refuse to render
    # SVGs served via <img> even though the content is valid.
    ext = os.path.splitext(urlparse(url).path)[1]

    os.makedirs("var/files", exist_ok=True)
    path = os.path.join("var/files", prefix + "-" + url_hash + "-" + name + ext)
    download_file(url, path)
    return path


def relativize(path: str) -> str:
    """
    Given a path, return a path relative to the current working directory.
    """
    return os.path.relpath(path, os.getcwd())

