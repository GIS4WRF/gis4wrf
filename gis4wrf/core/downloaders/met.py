# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

"""This module is an interface to the Research Data Archive (RDA) API"""

from typing import List, Iterable, Tuple, Union
import time
import requests
from pathlib import Path
from datetime import datetime

from .util import download_file, requests_retry_session
from gis4wrf.core.util import export, remove_dir

DATE_FORMAT = '%Y%m%d%H%M'
ERROR_STATUS = ['No request information found']
IGNORE_FILES = ['.csh']

@export
def get_met_products(dataset_name: str, auth: tuple) -> dict:
    # Retrieve raw metadata
    response = requests_retry_session().get(f'https://rda.ucar.edu/apps/metadata/{dataset_name}', auth=auth)
    response.raise_for_status()
    # Split into rows and columns
    all_rows = [x.split('|') for x in response.text.splitlines()]
    # filter out non-data rows like header and footer
    data_rows = [row for row in all_rows if len(row) >= 12][1:]
    products = {} # type: dict
    for row in data_rows:
        product_name = row[6]
        param_name = row[1]
        param_label = row[2]
        start_date = datetime.strptime(row[3], DATE_FORMAT)
        end_date = datetime.strptime(row[4], DATE_FORMAT)
        if product_name not in products:
            products[product_name] = {}
        product = products[product_name]
        if param_name not in product:
            product[param_name] = {
                'start_date': start_date,
                'end_date': end_date,
                'label': param_label
            }
    return products

# TODO not used currently
def get_enabled_param_names(products: dict, product_name: str,
                            user_start: datetime, user_end: datetime) -> List[str]:
    product = products[product_name]
    enabled_param_names = []
    for param_name, param in product.items():
        start = param['start_date']
        end = param['end_date']
        if start <= user_start and user_end <= end:
            enabled_param_names.append(param_name)
    return enabled_param_names

@export
def get_met_dataset_path(base_dir: Union[str,Path], dataset_name: str, product_name: str,
                         start_date: datetime, end_date: datetime) -> Path:
    datetime_range = '{}-{}'.format(start_date.strftime(DATE_FORMAT), end_date.strftime(DATE_FORMAT))
    base_dir = Path(base_dir)
    product_dir = base_dir / dataset_name / product_name
    path = product_dir / datetime_range
    return path

@export
def is_met_dataset_downloaded(base_dir: Union[str,Path], dataset_name: str, product_name: str,
                              start_date: datetime, end_date: datetime) -> bool:
    path = get_met_dataset_path(base_dir, dataset_name, product_name, start_date, end_date)
    return path.exists()

@export
def download_met_dataset(base_dir: Union[str,Path], auth: tuple,
                         dataset_name: str, product_name: str, param_names: List[str],
                         start_date: datetime, end_date: datetime,
                         lat_south: float, lat_north: float, lon_west: float, lon_east: float
                         ) -> Iterable[Tuple[int,str]]:
    path = get_met_dataset_path(base_dir, dataset_name, product_name, start_date, end_date)

    if path.exists():
        remove_dir(path)

    request_data = {
        'dataset': dataset_name,
        'product': product_name,
        'date': start_date.strftime(DATE_FORMAT) + '/to/' + end_date.strftime(DATE_FORMAT),
        'param': '/'.join(param_names),
        "nlat": lat_north,
        "slat": lat_south,
        "wlon": lon_west,
        "elon": lon_east
    }

    yield 5, 'submitting'
    request_id = rda_submit_request(request_data, auth)
    yield 10, 'submitted'

    # Check when the dataset is available for download
    # simply by checking the status of the request every 1 minute.
    rda_status = rda_check_status(request_id, auth)
    while rda_status != 'O - Online' and not rda_is_error_status(rda_status):
        time.sleep(60)
        rda_status = rda_check_status(request_id, auth)
        yield 10, 'RDA: ' + rda_status
    
    if rda_is_error_status(rda_status):
        raise RuntimeError('Unexpected status from RDA: ' + rda_status)

    yield 20, 'ready'
    try:
        for ratio in rda_download_dataset(request_id, auth, path):
            yield 20 + int((95 - 20) * ratio), 'downloading'
    finally:
        yield 95, 'purging'
        rda_purge_request(request_id, auth)    
    

def rda_submit_request(request_data: dict, auth: tuple) -> str:
    headers = {'Content-type': 'application/json'}
    # Note that requests_retry_session() is not used here since any error may be due
    # to invalid input and the user should be alerted immediately.
    response = requests.post('https://rda.ucar.edu/apps/request', auth=auth, headers=headers, json=request_data)
    response.raise_for_status()
    try:
        response_fmt = [x.split(':') for x in response.text.splitlines()]
        request_id = [x[1].strip() for x in response_fmt if x[0].strip() == 'Index'][0]
    except:
        raise RuntimeError('RDA error: ' + response.text.strip())
    return request_id

def rda_check_status(request_id: str, auth: tuple) -> str:
    response = requests_retry_session().get(f'https://rda.ucar.edu/apps/request/{request_id}/-proc_status', auth=auth)
    # We don't invoke raise_for_status() here to account for temporary network issues.
    return response.text

def rda_is_error_status(status: str) -> bool:
    return any(error_status in status for error_status in ERROR_STATUS)

def rda_download_dataset(request_id: str, auth: tuple, path: Path) -> Iterable[float]:
    path_tmp = path.with_name(path.name + '_tmp')
    if path_tmp.exists():
        remove_dir(path_tmp)
    path_tmp.mkdir(parents=True)
    urls = rda_get_urls_from_request_id(request_id, auth)
    count = len(urls)
    with requests_retry_session() as s:
        login_data = {'email': auth[0], 'passwd': auth[1], 'action': 'login'}
        response = s.post('https://rda.ucar.edu/cgi-bin/login', login_data)
        response.raise_for_status()
        for i, url in enumerate(urls):
            file_name = url.split('/')[-1]
            download_file(url, path_tmp / file_name, session=s)
            yield (i + 1) / count
    path_tmp.rename(path)

def rda_get_urls_from_request_id(request_id: str, auth: tuple) -> List[str]:
    response = requests_retry_session().get(f'https://rda.ucar.edu/apps/request/{request_id}/filelist', auth=auth)
    response.raise_for_status()
    urls = response.json()
    filtered = []
    for url in urls:
        if any(url.endswith(ignore) for ignore in IGNORE_FILES):
            continue
        filtered.append(url)
    return filtered

def rda_purge_request(request_id: str, auth: tuple) -> None:
    response = requests_retry_session().delete(f'https://rda.ucar.edu/apps/request/{request_id}', auth=auth)
    response.raise_for_status()
