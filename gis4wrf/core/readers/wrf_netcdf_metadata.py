# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Mapping, List, Optional, Dict, Callable, Any
from collections import namedtuple
import os

import netCDF4 as nc

# Optional import for wrf-python as binary wheels are not yet available for all platforms.
# If wrf-python is not available, then derived variables are not offered.
# TODO remove try-except once wheels are available
try:
    import wrf
except ImportError:
    wrf = None

from gis4wrf.core.util import export
from gis4wrf.core.readers.categories import LANDUSE

WRFNetCDFVariable = namedtuple('WRFNetCDFVariable', ['name', 'label', 'extra_dim_name'])
WRFNetCDFExtraDim = namedtuple('WRFNetCDFExtraDim', ['name', 'label', 'steps'])

__all__ = ['WRFNetCDFVariable', 'WRFNetCDFExtraDim']

# from wrf-python
COORD_VARS = ["XLAT", "XLONG", "XLAT_M", "XLONG_M", "XLAT_U", "XLONG_U",
              "XLAT_V", "XLONG_V", "CLAT", "CLONG"]

# Computed diagnostics variables from wrf-python.
MASS = ('Time', 'south_north', 'west_east')
BOTTOM_TOP_MASS = ('Time', 'bottom_top', 'south_north', 'west_east')
DIAG_DIMS = {
    'avo': BOTTOM_TOP_MASS,
    'eth': BOTTOM_TOP_MASS,
    'dbz': BOTTOM_TOP_MASS,
    'mdbz': MASS,
    'geopt': BOTTOM_TOP_MASS,
    'helicity': MASS,
    'omega': BOTTOM_TOP_MASS,
    'pvo': BOTTOM_TOP_MASS,
    'pw': MASS,
    'rh': BOTTOM_TOP_MASS,
    'rh2': MASS,
    'slp': MASS,
    'td2': MASS,
    'td': BOTTOM_TOP_MASS,
    'tc': BOTTOM_TOP_MASS,
    'theta': BOTTOM_TOP_MASS,
    'tk': BOTTOM_TOP_MASS,
    'tv': BOTTOM_TOP_MASS,
    'twb': BOTTOM_TOP_MASS,
    'updraft_helicity': MASS,
    'ua': BOTTOM_TOP_MASS,
    'va': BOTTOM_TOP_MASS,
    'wa': BOTTOM_TOP_MASS,
    'z': BOTTOM_TOP_MASS,
}
DIAG_VARS = {
    name: WRFNetCDFVariable(name, label, DIAG_DIMS[name][1] if len(DIAG_DIMS[name]) == 4 else None)
    for name, label in [
        ('avo', 'AVO* in 10-5 s-1 (Absolute Vorticity)'),
        ('eth', 'ETH* in K (Equivalent Potential Temperature)'),
        ('dbz', 'DBZ* in dBZ (Radar Reflectivity)'),
        ('mdbz', 'MDBZ* in dBZ (Maximum Radar Reflectivity)'),
        ('geopt', 'GEOPT* in m2 s-2 (Geopotential for the Mass Grid)'),
        ('helicity', 'HELICITY* in m2 s-2 (Storm Relative Helicity)'),
        ('omega', 'OMEGA* in Pa s-1 (Omega)'),
        ('pvo', 'PVO* in PVU (Potential Vorticity)'),
        ('pw', 'PW* in kg m-2 (Precipitable Water)'),
        ('rh', 'RH* in % (Relative Humidity)'),
        ('rh2', 'RH2* in % (2m Relative Humidity)'),
        ('slp', 'SLP* in hPA (Sea Level Pressure)'),
        ('td2', 'TD2* in °C (2m Dew Point Temperature)'),
        ('td', 'TD* in °C (Dew Point Temperature)'),
        ('tc', 'TC* in °C (Temperature)'),
        ('theta', 'THETA* in K (Potential Temperature)'),
        ('tk', 'TK* in K (Temperature)'),
        ('tv', 'TV* in K (Virtual Temperature)'),
        ('twb', 'TWB* in K (Wet Bulb Temperature)'),
        ('updraft_helicity', 'UPDRAFT_HELICITY* in m2 s-2 (Updraft Helicity)'),
        ('ua', 'UA* in m s-1 (U-component of Wind on Mass Points)'),
        ('va', 'VA* in m s-1 (V-component of Wind on Mass Points)'),
        ('wa', 'WA* in m s-1 (W-component of Wind on Mass Points)'),
        ('z', 'Z* in m (Model Height (MSL))'),
    ]
}


@export
def get_supported_wrf_nc_variables(path: str) -> Dict[str,WRFNetCDFVariable]:
    extra_dims = get_wrf_nc_extra_dims(path)
    ds = nc.Dataset(path)
    variables = {}
    for var_name in ds.variables:
        if var_name in COORD_VARS:
            print('Ignoring {}, coord var'.format(var_name))
            continue

        var = ds.variables[var_name]
        dims = var.dimensions
        shape = var.shape

        if len(dims) > 4:
            # should never happen
            print('Ignoring {}, too many dims: {}'.format(var_name, dims))
            continue

        if dims[0] != 'Time':
            # should never happen
            print('Ignoring {}, time dim missing, dims: {}'.format(var_name, dims))
            continue

        # TODO support staggered vars
        if dims[-2:] != ('south_north', 'west_east'):
            print('Ignoring {}, staggered, dims: {}'.format(var_name, dims))
            continue

        if len(dims) == 4:
            extra_dim = dims[1]
            if extra_dim not in extra_dims:
                print('Ignoring {}, unsupported z dimension: {}'.format(var_name, extra_dim))
                continue
        else:
            extra_dim = None

        try:
            description = var.getncattr('description')
        except AttributeError:
            description = None
        try:
            units = var.getncattr('units')
        except AttributeError:
            units = None

        label = var_name
        if units and units != '-':
            label += ' in ' + units
        if description and description != '-':
            label += ' (' + description.lower() + ')'

        variables[var_name] = WRFNetCDFVariable(name=var_name, label=label, extra_dim_name=extra_dim)

    if wrf is not None:
        is_wps = 'bottom_top' not in ds.dimensions
        if not is_wps:
            variables.update(DIAG_VARS)
    
    return variables

@export
def get_wrf_nc_extra_dims(path: str) -> Dict[str,WRFNetCDFExtraDim]:
    ds = nc.Dataset(path)
    dims = ds.dimensions
    attrs = ds.__dict__
    extra_dims = {} # type: Dict[str,WRFNetCDFExtraDim]

    def add_dim(name: str, label: str, step_fn: Optional[Callable[[int],Any]]=None):
        if name not in dims:
            return
        if step_fn is None:
            step_fn = lambda i: i
        steps = [str(step_fn(i)) for i in range(1, dims[name].size + 1)]
        extra_dims[name] = WRFNetCDFExtraDim(name=name, label=label, steps=steps)

    add_dim('bottom_top', 'Vertical Level')
    add_dim('soil_layers_stag', 'Soil Depth Layer')

    # the following exist in geogrid output only
    landuse_scheme = attrs.get('MMINLU')
    landuse_categories = LANDUSE.get(landuse_scheme, {})
    add_dim('land_cat', 'Land Use Category', lambda i: landuse_categories.get(i, (str(i), ''))[0])
    add_dim('soil_cat', 'Soil Type Category')
    add_dim('month', 'Month')

    # the following exist in metgrid output only
    add_dim('num_metgrid_levels', 'Vertical Level')
    # TODO add num_st_layers, num_sm_layers, z-dimension00**

    return extra_dims

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
