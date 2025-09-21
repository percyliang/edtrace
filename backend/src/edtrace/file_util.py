import os
import re
import hashlib
import shutil
from io import BytesIO
import requests


def ensure_directory_exists(path: str):
    """Create directory at `path` if it doesn't already exist."""
    if not os.path.exists(path):
        os.mkdir(path)


def download_file(url: str, filename: str):
    """Download `url` and save the contents to `filename`.  Skip if `filename` already exists."""
    if not os.path.exists(filename):
        print(f"Downloading {url} to {filename}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
        }
        response = requests.get(url, headers=headers)
        with open(filename, "wb") as f:
            shutil.copyfileobj(BytesIO(response.content), f)


def cached(url: str, prefix: str) -> str:
    """Download `url` if needed and return the location of the cached file."""
    name = re.sub(r"[^\w_-]+", "_", url)
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()

    ensure_directory_exists("var/files")
    path = os.path.join("var/files", prefix + "-" + url_hash + "-" + name)
    download_file(url, path)
    return path


def relativize(path: str) -> str:
    """
    Given a path, return a path relative to the current working directory.
    """
    return os.path.relpath(path, os.getcwd())

