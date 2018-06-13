# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

import pytest
import gis4wrf.core

def test_wps_namelist_verify_valid():
    namelist = {
        'share': {
            'wrf_core': 'ARW',
            'max_dom': 2,
            'start_month': [12, 1],
            'end_date': ["2016-01-01_00:00:00"],
            'active_grid': [True, False],
            'io_form_geogrid': 3
        },
        'geogrid': {
            'parent_grid_ratio': [4]
        }
    }
    gis4wrf.core.verify_namelist(namelist, 'wps')

def test_wps_namelist_verify_invalid():
    namelist = {
        'share': {
            'end_date': ["2016-01-01"]
        }
    }
    with pytest.raises(ValueError):
        gis4wrf.core.verify_namelist(namelist, 'wps')