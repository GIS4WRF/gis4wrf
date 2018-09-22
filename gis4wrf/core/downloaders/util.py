# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def download_file(url: str, path: str, session=None) -> None:
    new_session = session is None
    if new_session:
        session = requests_retry_session()
    try:
        response = session.get(url)
        response.raise_for_status()
        with open(path, 'wb') as f:
            f.write(response.content)
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
