# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List
import os

import netCDF4 as nc

from gis4wrf.core.util import export

@export
def get_wrf_nc_time_steps(path: str) -> List[str]:
    ds = nc.Dataset(path)
    steps = []
    # Each time step is stored as a sequence of 1-byte chars, e.g.:
    # array([b'2', b'0', b'0', b'5', b'-', b'0', b'8', b'-', b'2', b'8', b'_',
    #   b'0', b'0', b':', b'0', b'0', b':', b'0', b'0'],
    #  dtype='|S1')
    # ... which we convert to a plain string '2005-08-28_00:00:00'
    # and replace the underscore with a space: '2005-08-28 00:00:00'.
    for val in ds.variables['Times']:
        time = ''.join([c.decode() for c in val])
        time = time.replace('_', ' ')
        steps.append(time)
    return steps
