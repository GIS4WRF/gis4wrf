# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

WRF_EARTH_RADIUS = 6370000
WRF_PROJ4_SPHERE = '+a={radius} +b={radius}'.format(radius=WRF_EARTH_RADIUS)
PROJECT_JSON_VERSION = 1

# gdal forces us to provide names for categories starting from index 0.
# WRF's categories typically start at 1, so we need to add fake entries
# which we later filter out again from the palette when creating a QGIS raster layer.
UNUSED_CATEGORY_LABEL = '__UNUSED__'

# wrf-python/src/wrf/projection.py
class ProjectionTypes(object):
    LAMBERT_CONFORMAL = 1
    POLAR_STEREOGRAPHIC = 2
    MERCATOR = 3
    LAT_LON = 6

WRF_WPS_DIST_VERSION = '3.9'

WRF_DIST = {
    # keys: platform.system()
    'Windows': {
        'serial': 'https://github.com/GIS4WRF/WRFV3/releases/download/V3.9/wrf-3.9-windows-basic-serial-debug.tar.xz',
    }
}

WPS_DIST = {
    'Windows': {
        'serial': 'https://github.com/GIS4WRF/WPS/releases/download/RELEASE-3-9/wps-3.9-windows-basic-serial-debug.tar.xz',
    }
}