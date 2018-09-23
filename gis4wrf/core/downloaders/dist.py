# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Iterable, Tuple
import os
import shutil
import tempfile
import platform

from gis4wrf.core.util import export, remove_dir
from gis4wrf.core.constants import WPS_DIST, WRF_DIST
from gis4wrf.core.errors import UnsupportedError
from .util import download_file_with_progress

@export
def get_wrf_dist_url(mpi: bool) -> str:
    return get_dist_url(WRF_DIST, mpi)

@export
def get_wps_dist_url(mpi: bool) -> str:
    return get_dist_url(WPS_DIST, mpi)

def get_dist_url(dist: dict, mpi: bool) -> str:
    try:
        os_dist = dist[platform.system()]
    except KeyError:
        raise UnsupportedError('Pre-compiled distributions are not available for your operating system')
    if mpi:
        try:
            url = os_dist['dmpar']
        except KeyError:
            assert 'serial' in os_dist
            raise UnsupportedError('A pre-compiled MPI distribution is not available for your operating system')
    else:
        try:
            url = os_dist['serial']
        except KeyError:
            assert 'dmpar' in os_dist
            raise UnsupportedError('A pre-compiled non-MPI distribution is not available for your operating system')
    return url

@export
def download_and_extract_dist(url: str, folder: str) -> Iterable[Tuple[float,str]]:
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, url.split('/')[-1])
    if os.path.exists(folder):
        remove_dir(folder)
    os.makedirs(folder)
    try:
        for progress in download_file_with_progress(url, tmp_path):
            yield progress * 0.95, 'downloading'
        yield 0.95, 'extracting'
        shutil.unpack_archive(tmp_path, folder)
    finally:
        shutil.rmtree(tmp_dir)
    yield 1.0, 'done'
