# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List
from gis4wrf.core.util import export
from gis4wrf.core.project import Project

@export
def convert_wps_nml_to_project(nml: dict, existing_project: Project) -> Project:
    data = existing_project.data.copy()
    data['domains'] = convert_nml_to_project_domains(nml)
    project = Project(data, existing_project.path)
    return project

def convert_nml_to_project_domains(nml: dict) -> List[dict]:
    max_dom = nml['share']['max_dom'] # type: int

    nml = nml['geogrid']
    map_proj = nml['map_proj'] # type: str
    parent_id = nml['parent_id'] # type: List[int]
    parent_grid_ratio = nml['parent_grid_ratio'] # type: List[int]
    i_parent_start = nml['i_parent_start'] # type: List[int]
    j_parent_start = nml['j_parent_start'] # type: List[int]
    e_we = nml['e_we'] # type: List[int]
    e_sn = nml['e_sn'] # type: List[int]
    dx = [nml['dx']] # type: List[float]
    dy = [nml['dy']] # type: List[float]
    ref_lon = [nml['ref_lon']] # type: List[float]
    ref_lat = [nml['ref_lat']] # type: List[float]

    # Check that there are no domains with 2 nests on the same level
    if parent_id != [1] + list(range(1, max_dom)):
        raise RuntimeError('We only support 1 nested domain per parent domain.')

    # Check if projection is currently supported
    SUPPORTED_PROJ = ['lat-lon']
    if map_proj not in SUPPORTED_PROJ:
        raise NotImplementedError(f'Map projection in namelist not currently supported. \n\
                        Currently supported projections are {SUPPORTED_PROJ}.')

    min_lon = [] # type: List[float]
    min_lat = [] # type: List[float]
    padding_left = [] # type: List[int]
    padding_bottom = [] # type: List[int]
    padding_right = [] # type: List[int]
    padding_top = [] # type: List[int]

    cols = [i - 1 for i in e_we]
    rows = [i - 1 for i in e_sn]

    for idx in range(max_dom - 1):
        # Calculate horizontal grid spacing for inner domain
        dx.append(dx[idx] / parent_grid_ratio[idx+1])
        dy.append(dy[idx] / parent_grid_ratio[idx+1])

        if idx == 0:
            # Find the min coordinates for the outermost domain
            min_lon.append(ref_lon[idx] - (dx[idx] * (cols[idx] / 2)))
            min_lat.append(ref_lat[idx] - (dy[idx] * (rows[idx] / 2)))

        # Find the min coordinates for the outer domain
        min_lon.append(min_lon[idx] + (dx[idx] * (i_parent_start[idx+1] - 1)))
        min_lat.append(min_lat[idx] + (dy[idx] * (j_parent_start[idx+1] - 1)))

        # Find center coordinates for inner domain
        ref_lon.append(min_lon[idx+1] + (dx[idx+1] * (cols[idx+1] / 2)))
        ref_lat.append(min_lat[idx+1] + (dy[idx+1] * (rows[idx+1] / 2)))

        padding_left.append(i_parent_start[idx+1] - 1)
        padding_bottom.append(j_parent_start[idx+1] - 1)

        padding_right.append(cols[idx] - padding_left[idx] - cols[idx+1] // parent_grid_ratio[idx+1])
        padding_top.append(rows[idx] - padding_bottom[idx] - rows[idx+1] // parent_grid_ratio[idx+1])

    first_domain = {
        'map_proj': map_proj,
        'cell_size': [dx[-1], dy[-1]],
        'center_lonlat': [ref_lon[-1], ref_lat[-1]],
        'domain_size': [cols[-1], rows[-1]],
        'stand_lon': 0.0,
    }

    domains = [first_domain]
    for i in range(max_dom - 1):
        domains.append({
            'parent_cell_size_ratio': parent_grid_ratio[::-1][:-1][i],
            "padding_left": padding_left[::-1][i],
            "padding_right": padding_right[::-1][i],
            "padding_bottom": padding_bottom[::-1][i],
            "padding_top": padding_top[::-1][i]
        })

    return domains