# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Union
import platform
import os
import shutil
from pathlib import Path
import tarfile

from gis4wrf.core.util import export
from .util import download_file

# TODO we may want to host the datasets somewhere else, the UCAR website is often down
EXT = '.tar.bz2'
URL_TEMPLATE = 'http://www2.mmm.ucar.edu/wrf/src/wps_files/{dataset_name}' + EXT

@export
def is_geo_dataset_downloaded(dataset_name: str, base_dir: Union[str,Path]) -> bool:
    return get_geo_dataset_path(dataset_name, base_dir).exists()

@export
def get_geo_dataset_path(dataset_name: str, base_dir: Union[str,Path]) -> Path:
    base_dir = Path(base_dir)
    dataset_folder = base_dir / dataset_name
    return dataset_folder

@export
def download_and_extract_geo_dataset(dataset_name: str, base_dir: Union[str,Path]) -> None:
    base_dir = Path(base_dir)
    url = URL_TEMPLATE.format(dataset_name=dataset_name)
    path_to_archive = base_dir / (dataset_name + EXT)
    path_to_folder = base_dir / dataset_name

    if path_to_folder.exists():
        return
    
    base_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        download_file(url, path_to_archive)
        if dataset_name.startswith('orogwd') and platform.system() == 'Windows':
            # The orogwd* datasets contain a folder with name 'con' which
            # is reserved on Windows and has to be handled specially.
            # Note that the extracted 'con' folder cannot be accessed or deleted from
            # Windows Explorer. It can be deleted from the command line
            # with `rd /q /s \\?\c:\path\to\geog\dataset\con`.
            windows_extract_with_reserved_names(str(path_to_archive), str(base_dir))
        else:
            shutil.unpack_archive(str(path_to_archive), str(base_dir))
    finally:
        if path_to_archive.exists():
            path_to_archive.unlink()

def windows_extract_with_reserved_names(tar_path: str, dst_path: str) -> None:
    ''' 
    This function extracts tar archives that can contain the reserved folder name
    'con' at the last hierarchy level.
    See https://stackoverflow.com/a/50810859.
    '''
    CON = 'con' # reserved name on Windows
    dst_path = os.path.abspath(dst_path)
    with tarfile.open(tar_path) as tar:
        members = tar.getmembers()
        for member in members:
            name = member.name.replace('/', '\\')
            path = os.path.join(dst_path, name)
            if member.isdir():
                if os.path.basename(name) == CON:
                    path = r'\\?' + '\\' + path
                os.mkdir(path)
            elif member.isfile():
                if os.path.dirname(name) == CON:
                    path = r'\\?' + '\\' + path
                with open(path, 'wb') as fp:
                    shutil.copyfileobj(tar.extractfile(member), fp)
            else:
                raise RuntimeError('unsupported tar item type')
            
