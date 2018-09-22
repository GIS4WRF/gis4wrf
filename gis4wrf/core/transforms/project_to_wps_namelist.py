# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from collections import OrderedDict

from gis4wrf.core.util import export
from gis4wrf.core.project import Project

@export
def convert_project_to_wps_namelist(project: Project) -> dict:
    wps = OrderedDict() # type: dict

    domains = project.data['domains']
    num_domains = len(domains)
    assert num_domains > 0
    innermost_domain = domains[0]
    outermost_domain = domains[-1]

    map_proj = innermost_domain['map_proj']

    def to_wrf_date(date):
        return date.strftime('%Y-%m-%d_%H:%M:%S')

    wps['share'] = OrderedDict(
        nocolons = True,
        max_dom = num_domains
    )
    try:
        met_spec = project.met_dataset_spec
    except KeyError:
        pass
    else:
        wps['share'].update(
            start_date = [to_wrf_date(met_spec['time_range'][0])] * num_domains,
            end_date = [to_wrf_date(met_spec['time_range'][1])] * num_domains,
            interval_seconds = met_spec['interval_seconds']
        )

    # When a GIS4WRF project is not used, we construct the path 
    # to the geog folder with a dummy string.
    try:
        geog_data_path = project.geog_data_path + '/'
    except:
        geog_data_path = '/path/to/geog/folder'
    
    wps['geogrid'] = OrderedDict(
        parent_id = [1] + list(range(1, num_domains)),
        parent_grid_ratio = [1] + [domain['parent_cell_size_ratio'] for domain in domains[:0:-1]],
        i_parent_start = [domain['parent_start'][0] for domain in domains[::-1]],
        j_parent_start = [domain['parent_start'][1] for domain in domains[::-1]],
        # e_we and e_sn represent the number of velocity points (i.e., u-staggered or v-staggered points)
        # which is one more than the number of cells in each dimension.
        e_we = [domain['domain_size'][0] + domain['padding_left'] + domain['padding_right'] + 1 for domain in domains[::-1]],
        e_sn = [domain['domain_size'][1] + domain['padding_bottom'] + domain['padding_top'] + 1 for domain in domains[::-1]],
        map_proj = map_proj,
        dx = outermost_domain['cell_size'][0],
        dy = outermost_domain['cell_size'][1],
        ref_lon = outermost_domain['center_lonlat'][0],
        ref_lat = outermost_domain['center_lonlat'][1],
        geog_data_res = project.geo_dataset_specs[::-1],
        geog_data_path = geog_data_path
    )

    if map_proj in ['lambert', 'mercator', 'polar']:
        wps['geogrid']['truelat1'] = innermost_domain['truelat1']

    if map_proj == 'lambert':
        wps['geogrid']['truelat2'] = innermost_domain['truelat2']

    if map_proj in ['lambert', 'polar']:
        wps['geogrid']['stand_lon'] = innermost_domain['center_lonlat'][0]

    if map_proj == 'lat-lon':
        wps['geogrid']['stand_lon'] = innermost_domain['stand_lon'] # rotation
    #    wps['geogrid']['pole_lat'] = innermost_domain['pole_lat']
    #    wps['geogrid']['pole_lon'] = innermost_domain['pole_lon']

    wps['metgrid'] = OrderedDict(
        fg_name = ['FILE']
    )

    return wps