# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
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


def test_wrf_namelist_verify_valid():
    namelist = {
        'time_control': {
            'start_year': [2018, 2018],
            'interval_seconds': 21600,
            'input_from_file': [True, True],
            'restart': False,
            'restart_interval': 7200,
            'io_form_history': 2
        },
        'domains': {
            'time_step': 40,
            'max_dom': 2
        },
        'physics': {
            'physics_suite': 'CONUS'
        }
    }
    gis4wrf.core.verify_namelist(namelist, 'wrf')

def test_wrf_namelist_verify_invalid():
    namelist = {
        'time_control': {
            'start_year': ['2018']
        }
    }
    with pytest.raises(TypeError):
        gis4wrf.core.verify_namelist(namelist, 'wrf')
