import re
import xml.etree.ElementTree as ET
from file_util import cached
from reference import Reference


def canonicalize(text: str):
    """Remove newlines and extra whitespace with one space."""
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def is_arxiv_link(url: str) -> bool:
    return url.startswith("https://arxiv.org/")

def arxiv_reference(url: str, **kwargs) -> Reference:
    """
    Parse an arXiv reference from a URL (e.g., https://arxiv.org/abs/2005.14165).
    Cache the result.
    """
    # Figure out the paper ID
    paper_id = None
    m = re.search(r'arxiv.org\/...\/(\d+\.\d+)(v\d)?(\.pdf)?$', url)
    if not m:
        raise ValueError(f"Cannot handle this URL: {url}")
    paper_id = m.group(1)

    metadata_url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
    metadata_path = cached(metadata_url, "arxiv")
    with open(metadata_path, "r") as f:
        contents = f.read()
    root = ET.fromstring(contents)

    # Extract the relevant metadata
    entry = root.find('{http://www.w3.org/2005/Atom}entry')
    title = canonicalize(entry.find('{http://www.w3.org/2005/Atom}title').text)
    authors = [canonicalize(author.find('{http://www.w3.org/2005/Atom}name').text) for author in entry.findall('{http://www.w3.org/2005/Atom}author')]
    summary = canonicalize(entry.find('{http://www.w3.org/2005/Atom}summary').text)
    published = entry.find('{http://www.w3.org/2005/Atom}published').text

    return Reference(
        title=title,
        authors=authors,
        url=url,
        date=published,
        description=summary,
        **kwargs,
    )