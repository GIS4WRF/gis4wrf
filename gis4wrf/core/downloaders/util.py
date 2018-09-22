# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def download_file(url: str, path: str, session=None) -> None:
    for _ in download_file_with_progress(url, path, session):
        pass

def download_file_with_progress(url: str, path: str, session=None) -> Iterable[float]:
    new_session = session is None
    if new_session:
        session = requests_retry_session()
    try:
        response = session.get(url, stream=True)
        response.raise_for_status()
        total = response.headers.get('content-length')
        if total is not None:
            total = int(total)
        downloaded = 0
        with open(path, 'wb') as f:
            for data in response.iter_content(chunk_size=1024*1024):
                downloaded += len(data)
                f.write(data)
                if total is not None:
                    yield downloaded / total
        if total is None:
            yield 1.0
        else:
            assert total == downloaded, f'Did not receive all data: {total} != {downloaded}'
    finally:
        if new_session:
            session.close()

# https://www.peterbe.com/plog/best-practice-with-retries-with-requests
def requests_retry_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504), session=None):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        status=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
