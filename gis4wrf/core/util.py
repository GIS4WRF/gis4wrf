# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Union
import os
import sys
from pathlib import Path
import platform
import random
import tempfile
import shutil
import time

import numpy as np

# for import by other modules to avoid repeating UseExceptions()
from osgeo import gdal, ogr, osr, gdal_array
gdal.UseExceptions()
ogr.UseExceptions()
osr.UseExceptions()
gdal.SetConfigOption('GDAL_VRT_ENABLE_PYTHON', 'YES')

def export(fn):
    ''' Function decorator that adds the function to `__all__`.
        See https://stackoverflow.com/a/35710527.
    '''
    mod = sys.modules[fn.__module__]
    if hasattr(mod, '__all__'):
        mod.__all__.append(fn.__name__)
    else:
        mod.__all__ = [fn.__name__]
    return fn

Number = Union[int,np.integer,float,np.floating]

def as_float(val: Number) -> float:
    if isinstance(val, float):
        return val
    if isinstance(val, np.floating):
        return val.item()
    if isinstance(val, (int, np.integer)):
        return float(val)
    raise TypeError('Value is not an int or float type: {}'.format(type(val)))

def get_temp_vsi_path(ext: str='.vrt') -> str:
    return '/vsimem/tmp{}{}'.format(random.randint(10000, 99999), ext)

def read_vsi_string(path: str, remove: bool=True) -> str:
    fp = gdal.VSIFOpenL(path, 'r')
    content = gdal.VSIFReadL(1, 1000000, fp).decode('ascii')
    gdal.VSIFCloseL(fp)
    if remove:
        gdal.Unlink(path)
    return content

def remove_vsis(paths) -> None:
    for path in paths:
        gdal.Unlink(path)

def link(src_path: str, link_path: str) -> None:
    assert os.path.isfile(src_path)
    if os.path.exists(link_path) or os.path.islink(link_path):
        os.remove(link_path)
    try:
        # Windows: requires admin rights, but not restricted to same drive
        os.symlink(src_path, link_path)
    except:
        # Windows: does not require admin rights, but restricted to same drive
        os.link(src_path, link_path)

def link_or_copy(src: str, dst: str) -> None:
    try:
        link(src, dst)
    except:
        # fall-back for Windows if hard/sym links couldn't be created
        shutil.copy(src, dst)

def get_temp_dir() -> str:
    return tempfile.mkdtemp(prefix='gis4wrf')

def remove_dir(path: Union[str,Path]) -> None:
    # This function avoids two issues occuring on Windows:
    # 1. If a file within the folder is still in use (=locked), then removing the folder would fail.
    #    This can happen in event handlers, e.g. when removing temporary raster datasets as soon as
    #    the raster layer was removed. In this case, waiting and retrying works around this issue.
    # 2. The removal of a folder may be successful but if a new folder at the same location with
    #    the same name is created immediately afterwards then this may fail as the operating system
    #    (or other processes) may still have a lock on the already "removed" folder.
    #    The work-around is to rename the folder first and then remove it.
    path = Path(path)
    tmp = path.with_name(str(random.randint(10000, 99999)))
    retry(lambda: path.rename(tmp))
    retry(lambda: shutil.rmtree(tmp))

def retry(fn, retries=3, sleep=1):
    while True:
        try:
            return fn()
        except:
            retries -= 1
            if retries > 0:
                time.sleep(sleep)
            else:
                raise
