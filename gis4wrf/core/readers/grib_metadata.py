# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Set, Dict, Tuple, List, Optional
import os
from datetime import datetime

from gis4wrf.core.util import gdal, export

class GribMetadata(object):
    def __init__(self, variables: Dict[str,str], times: List[datetime], path: Optional[str]=None) -> None:
        self.path = path # path to file
        self.variables = variables # maps variable names to labels
        self.times = times # ordered list of datetime objects

    @property
    def time_range(self) -> Tuple[datetime,datetime]:
        assert self.times
        return min(self.times), max(self.times)

    @property
    def interval_seconds(self) -> int:
        assert len(self.times) >= 2
        first, second = self.times[:2]
        return int((second - first).total_seconds())

@export
def read_grib_folder_metadata(folder: str) -> Tuple[GribMetadata, List[GribMetadata]]:
    paths = [os.path.join(folder, filename)
             for filename in os.listdir(folder)
             if not filename.endswith('.aux.xml')]
    return read_grib_files_metadata(paths)

@export
def read_grib_files_metadata(paths: List[str]) -> Tuple[GribMetadata, List[GribMetadata]]:
    ''' Reads metadata of multiple GRIB files which must have non-overlapping time steps.
        Returns aggregated and per-file metadata, where the latter are ordered by time.
    '''
    variables = {} # type: Dict[str,str]
    times = [] # type: List[datetime]

    metas = [] # type: List[GribMetadata]
    for path in paths:
        meta = read_grib_file_metadata(path)
        metas.append(meta)
        if not variables:
            variables = meta.variables
        else:
            variables.update(meta.variables)
            assert not set(meta.times).intersection(times)
        times.extend(meta.times)

    times.sort()
    metas.sort(key=lambda meta: meta.times)

    return GribMetadata(variables, times), metas

@export
def read_grib_file_metadata(path: str) -> GribMetadata:
    ds = gdal.Open(path, gdal.GA_ReadOnly)

    # ds.GetMetadata() returns nothing in gdal < 2.3, but with 2.3 it contains the GRIB_IDS
    # item which contains things like the center (e.g. NCEP). See http://www.gdal.org/frmt_grib.html.

    # TODO read bbox

    variables = dict()
    times = set()

    for i in range(1, ds.RasterCount + 1):
        band = ds.GetRasterBand(i)
        meta = band.GetMetadata()
        var_unit = meta['GRIB_UNIT'] # "[m/s]"
        var_name = meta['GRIB_ELEMENT'] # "VGRD"
        var_label = meta['GRIB_COMMENT'] # "v-component of wind [m/s]"
        valid_time = meta['GRIB_VALID_TIME'] # "  1438754400 sec UTC"

        var_label_without_unit = var_label.replace(var_unit, '').strip()
        variables[var_name] = var_label_without_unit
        
        unix = int(''.join(c for c in valid_time if c.isdigit()))
        time = datetime.utcfromtimestamp(unix)
        times.add(time)

    return GribMetadata(variables, sorted(times), path)