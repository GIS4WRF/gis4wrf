# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

import os
from gis4wrf.core import read_geogrid_tbl, write_geogrid_tbl

TBL_PATH = os.path.join(os.path.dirname(__file__), 'resources', 'GEOGRID.TBL.ARW')

def test_read_geogrid_tbl():
    tbl = read_geogrid_tbl(TBL_PATH)
    check_geogrid_tbl_contents(tbl)

def test_write_geogrid_tbl(tmpdir):
    tbl = read_geogrid_tbl(TBL_PATH)
    path = os.path.join(tmpdir, 'GEOGRID.TBL')
    write_geogrid_tbl(tbl, path)
    tbl = read_geogrid_tbl(path)
    check_geogrid_tbl_contents(tbl)

def check_geogrid_tbl_contents(tbl):
    v = tbl.variables

    assert v.keys() == set([
        'HGT_M', 'LANDUSEF', 'SOILTEMP', 'SOILCTOP', 'SOILCBOT',
        'ALBEDO12M', 'GREENFRAC', 'LAI12M', 'SNOALB', 'SLOPECAT',
        'CON', 'VAR', 'OA1', 'OA2', 'OA3',
        'OA4', 'OL1', 'OL2', 'OL3', 'OL4',
        'VAR_SSO', 'LAKE_DEPTH', 'URB_PARAM', 'IMPERV', 'CANFRA'])

    assert v['HGT_M'].options == {
        'priority': '1',
        'dest_type': 'continuous',
        'fill_missing': '0.',
        'smooth_option': 'smth-desmth_special; smooth_passes=1'
    }

    assert v['HGT_M'].group_options.keys() == set([
        'gmted2010_30s', 'gtopo_30s', 'gtopo_2m', 'gtopo_5m', 'gtopo_10m', 'default'
    ])

    assert v['HGT_M'].group_options['gtopo_10m'] == {
        'interp_option': 'four_pt',
        'rel_path': 'topo_10m/'
    }

    assert v['LANDUSEF'].group_options['modis_30s_lake'] == {
        'interp_option': 'nearest_neighbor',
        'landmask_water': '17,21',
        'rel_path': 'modis_landuse_20class_30s_with_lakes/'
    }