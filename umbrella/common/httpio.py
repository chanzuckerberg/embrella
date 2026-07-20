"""HTTP file access helpers.

The file server exposes processing artifacts (CSVs, thumbnails, zarr
volumes, ...) over HTTP. This module is the HTTP counterpart to
``common.clusterio.read_remote_file`` (SFTP)
"""

import requests
from umbrella_logger import logger

DEFAULT_TIMEOUT = 10


def fetch_remote_text(url, timeout=DEFAULT_TIMEOUT):
    """Read a text file served over HTTP and return its content as a string.

    Args:
        url: Fully-resolved HTTP(S) URL of the file (e.g. built via
            ``stores.models.resolve_review_path`` with a ``*_url`` data_type).
        timeout: Request timeout in seconds.

    Returns:
        File content as a string.

    Raises:
        FileNotFoundError: if the server returns 404 (keeps callers' existing
            missing-file handling working).
        requests.HTTPError: for any other non-2xx response.
        requests.RequestException: on connection/timeout errors.
    """
    logger.info(f"Fetching remote file over HTTP: {url}")
    response = requests.get(url, timeout=timeout)
    if response.status_code == 404:
        raise FileNotFoundError(url)
    response.raise_for_status()
    return response.text
