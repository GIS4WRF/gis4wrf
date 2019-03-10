# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List

from gis4wrf.core.util import export
from gis4wrf.core.errors import UserError, UnsupportedError
from gis4wrf.core.project import Project
from gis4wrf.core.crs import CRS, Coordinate2D, LonLat

@export
def convert_wps_nml_to_project(nml: dict, existing_project: Project) -> Project:
    data = existing_project.data.copy()
    try:
        data['domains'] = convert_nml_to_project_domains(nml)
    except KeyError as e:
        raise UserError(f'Invalid namelist, section/variable {e} not found')
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
    ref_lon = nml['ref_lon'] # type: float
    ref_lat = nml['ref_lat'] # type: float
    truelat1 = nml.get('truelat1') # type: float
    truelat2 = nml.get('truelat2') # type: float
    stand_lon = nml.get('stand_lon', 0.0) # type: float

    # Check that there are no domains with 2 nests on the same level
    if parent_id != [1] + list(range(1, max_dom)):
        raise UserError('Due to the way domains are represented in GIS4WRF '
                        'each parent domain can have only one nested domain')

    # Check whether ref_x/ref_y is omitted, so that we can assume ref == center.
    if 'ref_x' in nml or 'ref_y' in nml:
        raise UnsupportedError('ref_x/ref_y is not supported in namelist')

    # Create CRS object from projection metadata.
    # See wps_binary_to_gdal.py for further explanations regarding latitude
    # and longitude of origin.
    if map_proj == 'lat-lon':
        if stand_lon != 0.0:
            raise UnsupportedError('Rotated lat-lon projection is not supported')
        crs = CRS.create_lonlat()
    elif map_proj == 'lambert':
        arbitrary_latitude_origin = (truelat1 + truelat2)/2
        origin = LonLat(lon=stand_lon, lat=arbitrary_latitude_origin)
        crs = CRS.create_lambert(truelat1, truelat2, origin)
    elif map_proj == 'mercator':
        arbitrary_longitude_origin = 0
        crs = CRS.create_mercator(truelat1, arbitrary_longitude_origin)
    elif map_proj == 'polar':
        crs = CRS.create_polar(truelat1, stand_lon)
    else:
        raise UnsupportedError(f'Map projection "{map_proj}" is not supported')

    ref_xy = crs.to_xy(LonLat(lon=ref_lon, lat=ref_lat))
    ref_x = [ref_xy.x] # type: List[float]
    ref_y = [ref_xy.y] # type: List[float]
    min_x = [] # type: List[float]
    min_y = [] # type: List[float]
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
            # Calculate min coordinates for outermost domain
            min_x.append(ref_x[idx] - (dx[idx] * (cols[idx] / 2)))
            min_y.append(ref_y[idx] - (dy[idx] * (rows[idx] / 2)))

        # Calculate min coordinates for outer domain
        min_x.append(min_x[idx] + (dx[idx] * (i_parent_start[idx+1] - 1)))
        min_y.append(min_y[idx] + (dy[idx] * (j_parent_start[idx+1] - 1)))

        # Calculate center coordinates for inner domain
        ref_x.append(min_x[idx+1] + (dx[idx+1] * (cols[idx+1] / 2)))
        ref_y.append(min_y[idx+1] + (dy[idx+1] * (rows[idx+1] / 2)))

        padding_left.append(i_parent_start[idx+1] - 1)
        padding_bottom.append(j_parent_start[idx+1] - 1)

        padding_right.append(cols[idx] - padding_left[idx] - cols[idx+1] // parent_grid_ratio[idx+1])
        padding_top.append(rows[idx] - padding_bottom[idx] - rows[idx+1] // parent_grid_ratio[idx+1])

    ref_lonlat = crs.to_lonlat(Coordinate2D(x=ref_x[-1], y=ref_y[-1]))

    first_domain = {
        'map_proj': map_proj,
        'cell_size': [dx[-1], dy[-1]],
        'center_lonlat': [ref_lonlat.lon, ref_lonlat.lat],
        'domain_size': [cols[-1], rows[-1]],
        'stand_lon': stand_lon,
    }
    if truelat1 is not None:
        first_domain['truelat1'] = truelat1
    if truelat2 is not None:
        first_domain['truelat2'] = truelat2
    if stand_lon is not None:
        first_domain['stand_lon'] = stand_lon

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