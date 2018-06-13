# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List, Tuple, Set, Dict, Optional
from collections import defaultdict
import os
import re

from gis4wrf.core.util import export
from gis4wrf.core.readers.wps_binary_index import read_wps_binary_index_file

@export
class GeogridTblKeys(object):
    NAME = 'name'
    INTERP_OPTION = 'interp_option'
    LANDMASK_WATER = 'landmask_water'
    REL_PATH = 'rel_path'
    # derived
    RESOLUTION = '_resolution'
    ABS_PATH = '_abs_path'
    MISSING = '_missing'

    @staticmethod
    def is_derived(key: str) -> bool:
        return key.startswith('_')

@export
class GeogridTblVar(object):
    def __init__(self, name: str) -> None:
        self.name = name
        self.options = dict() # type: Dict[str,str]
        self.group_options = dict() # type: Dict[str,Dict[str,str]]

@export
class GeogridTbl(object):
    def __init__(self) -> None:
        self.variables = dict() # type: Dict[str,GeogridTblVar]

    def add(self, group_name: str, var_name: str, dataset_path: str, geog_path: str,
            interp: str, landmask_water: Optional[List[int]]=None) -> None:
        rel_path = os.path.relpath(dataset_path, geog_path).replace('\\', '/') + '/'

        opts = self.variables[var_name].group_options[group_name] = {
            GeogridTblKeys.INTERP_OPTION: interp,
            GeogridTblKeys.REL_PATH: rel_path
        }
        if landmask_water:
            opts[GeogridTblKeys.LANDMASK_WATER] = ','.join(map(str, landmask_water))

    def remove(self, group_name: str, var_name: Optional[str]=None) -> None:
        variables = [self.variables[var_name]] if var_name else self.variables.values()

        for variable in variables:
            if group_name in variable.group_options:
                del variable.group_options[group_name]
    
    @property
    def group_names(self) -> Set[str]:
        names = set() # type: Set[str]
        for var in self.variables.values():
            names |= var.group_options.keys()
        return names

# Each variable defines datasets local to that variable.
# These parameters appear per such dataset.
PER_DATASET = [GeogridTblKeys.INTERP_OPTION,
               GeogridTblKeys.LANDMASK_WATER,
               GeogridTblKeys.REL_PATH]

# matches key=value lines and ignores '#' comments at the end
PATTERN = re.compile(r'[\t ]*(\w+)[\t ]*=[\t ]*([^#]+)')

@export
def read_geogrid_tbl(path: str) -> GeogridTbl:
    with open(path) as fp:
        lines = fp.readlines() # type: List[str]

    tbl = GeogridTbl()
    for line in lines:
        match = PATTERN.match(line)
        if match is None:
            continue
        key, val = match.groups()
        val = val.rstrip()
        if key == GeogridTblKeys.NAME:
            var_name = val
            if var_name not in tbl.variables:
                tbl.variables[var_name] = GeogridTblVar(var_name)
            variable = tbl.variables[var_name]
        elif key in PER_DATASET:
            group_name, group_option_val = val.split(':')
            if group_name not in variable.group_options:
                variable.group_options[group_name] = dict()
            variable.group_options[group_name][key] = group_option_val
        else:
            tbl.variables[var_name].options[key] = val
    
    return tbl

@export
def add_derived_metadata_to_geogrid_tbl(tbl: GeogridTbl, geog_path: str) -> None:
    for variable in tbl.variables.values():
        for group_options in variable.group_options.values():
            rel_path = group_options[GeogridTblKeys.REL_PATH]
            dataset_path = os.path.join(geog_path, rel_path)

            group_options[GeogridTblKeys.ABS_PATH] = os.path.abspath(dataset_path)
            group_options[GeogridTblKeys.MISSING] = not os.path.exists(dataset_path)

            if group_options[GeogridTblKeys.MISSING]:
                continue

            meta = read_wps_binary_index_file(dataset_path)

            if meta.proj_id == 'regular_ll':
                degrees, minutes, seconds = dd_to_dms(meta.dx)
                seconds = round(seconds, 2)
                res_parts = []
                if degrees > 0:
                    res_parts.append('{}°'.format(degrees))
                if minutes > 0:
                    res_parts.append('{}′'.format(minutes))
                if seconds > 0:
                    if seconds == int(seconds):
                        seconds = int(seconds) # avoid trailing .0
                    res_parts.append('{}″'.format(seconds))
                res = ' '.join(res_parts)
            else:
                res = '{} m'.format(dx)

            group_options[GeogridTblKeys.RESOLUTION] = res

def dd_to_dms(value: float) -> Tuple[int,int,float]:
    ''' Convert decimal degrees to degrees, minutes, seconds.
    See https://anothergisblog.blogspot.co.uk/2011/11/convert-decimal-degree-to-degrees.html.
    '''
    degrees = int(value)
    submin = abs((value - int(value)) * 60)
    minutes = int(submin)
    subseconds = abs((submin - int(submin)) * 60)
    return degrees, minutes, subseconds

