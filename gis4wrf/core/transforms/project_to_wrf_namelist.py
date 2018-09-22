# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from collections import OrderedDict
import os
import glob

import netCDF4 as nc

from gis4wrf.core.util import export
from gis4wrf.core.project import Project
from gis4wrf.core.logging import logger

@export
def convert_project_to_wrf_namelist(project: Project) -> dict:
    wrf = OrderedDict() # type: dict

    try:
        met_spec = project.met_dataset_spec
    except KeyError:
        raise RuntimeError('Meteorological data not selected')

    geogrid_nc = [os.path.join(project.run_wps_folder, 'geo_em.d{:02d}.nc'.format(i))
                  for i in range(1, project.domain_count + 1)]
    if not all(map(os.path.exists, geogrid_nc)):
        raise RuntimeError('Geogrid output files not found, run geogrid first')
    
    dx = [] # type: List[float]
    dy = [] # type: List[float]
    for path in geogrid_nc:
        ds = nc.Dataset(path)
        try:
            dx.append(ds.getncattr('DX'))
            dy.append(ds.getncattr('DY'))
            num_land_cat = ds.getncattr('NUM_LAND_CAT')
        finally:
            ds.close()
        logger.debug(f'read metadata from {path}: DX={dx[-1]}, DY={dy[-1]}, NUM_LAND_CAT={num_land_cat}')

    metgrid_nc = glob.glob(os.path.join(project.run_wps_folder, 'met_em.d01.*.nc'))
    if not metgrid_nc:
        raise RuntimeError('Metgrid output files not found, run metgrid first')
    ds = nc.Dataset(metgrid_nc[0])
    try:
        num_metgrid_levels = ds.dimensions['num_metgrid_levels'].size
        num_metgrid_soil_levels = ds.getncattr('NUM_METGRID_SOIL_LEVELS')
    finally:
        ds.close()
    logger.debug(f'read metadata from {metgrid_nc[0]}: num_metgrid_levels={num_metgrid_levels}, ' +
                 f'NUM_METGRID_SOIL_LEVELS={num_metgrid_soil_levels}')
        
    domains = project.data['domains']
    num_domains = len(domains)
    assert num_domains > 0

    start, end = met_spec['time_range']
    wrf['time_control'] = OrderedDict(
        start_year = [start.year] * num_domains,
        start_month = [start.month] * num_domains,
        start_day = [start.day] * num_domains,
        start_hour = [start.hour] * num_domains,
        start_minute = [start.minute] * num_domains,
        start_second = [start.second] * num_domains,
        end_year = [end.year] * num_domains,
        end_month = [end.month] * num_domains,
        end_day = [end.day] * num_domains,
        end_hour = [end.hour] * num_domains,
        end_minute = [end.minute] * num_domains,
        end_second = [end.second] * num_domains,
        interval_seconds = met_spec['interval_seconds'],
        history_interval = [60] * num_domains,
        frames_per_outfile = [100] * num_domains,
        input_from_file = [True] * num_domains,
        nocolons = True
    )

    parent_grid_ratio = [1] + [domain['parent_cell_size_ratio'] for domain in domains[:0:-1]]
    wrf['domains'] = OrderedDict(
        max_dom = num_domains,
        grid_id = list(range(1, num_domains + 1)),
        parent_id = [1] + list(range(1, num_domains)),
        parent_grid_ratio = parent_grid_ratio,
        parent_time_step_ratio = parent_grid_ratio,
        i_parent_start = [domain['parent_start'][0] for domain in domains[::-1]],
        j_parent_start = [domain['parent_start'][1] for domain in domains[::-1]],
        # e_we and e_sn represent the number of velocity points (i.e., u-staggered or v-staggered points)
        # which is one more than the number of cells in each dimension.
        e_we = [domain['domain_size'][0] + domain['padding_left'] + domain['padding_right'] + 1 for domain in domains[::-1]],
        e_sn = [domain['domain_size'][1] + domain['padding_bottom'] + domain['padding_top'] + 1 for domain in domains[::-1]],
        e_vert = [30] * num_domains,
        # dx/dy is not the same as in the WPS namelist, instead it is always meters
        # and is written to the geogrid output files (see above).
        dx = dx,
        dy = dy,
        num_metgrid_levels = num_metgrid_levels,
        num_metgrid_soil_levels = num_metgrid_soil_levels
    )

    wrf['physics'] = OrderedDict(
        num_land_cat = num_land_cat
    )

    return wrf