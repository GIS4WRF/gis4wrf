# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
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

WRF_WPS_DIST_OLD_VERSIONS = ['3.9']
WRF_WPS_DIST_VERSION = '4.0'

WRF_DIST = {
    # keys: platform.system()
    'Windows': {
        'serial': 'https://github.com/WRF-CMake/WRF/releases/download/WRF-CMake-4.0/wrf-cmake-4.0-serial-basic-release-windows.zip',
        'dmpar': 'https://github.com/WRF-CMake/WRF/releases/download/WRF-CMake-4.0/wrf-cmake-4.0-dmpar-basic-release-windows.zip'
    },
    'Darwin': {
        'serial': 'https://github.com/WRF-CMake/WRF/releases/download/WRF-CMake-4.0/wrf-cmake-4.0-serial-basic-release-macos.tar.xz',
        'dmpar': 'https://github.com/WRF-CMake/WRF/releases/download/WRF-CMake-4.0/wrf-cmake-4.0-dmpar-basic-release-macos.tar.xz'
    },
    'Linux': {
        'serial': 'https://github.com/WRF-CMake/WRF/releases/download/WRF-CMake-4.0/wrf-cmake-4.0-serial-basic-release-linux.tar.xz',
        'dmpar': 'https://github.com/WRF-CMake/WRF/releases/download/WRF-CMake-4.0/wrf-cmake-4.0-dmpar-basic-release-linux.tar.xz'
    }
}

WPS_DIST = {
    'Windows': {
        'serial': 'https://github.com/WRF-CMake/WPS/releases/download/WPS-CMake-4.0/wps-cmake-4.0-serial-basic-release-windows.zip',
        'dmpar': 'https://github.com/WRF-CMake/WPS/releases/download/WPS-CMake-4.0/wps-cmake-4.0-dmpar-basic-release-windows.zip',
    },
    'Darwin': {
        'serial': 'https://github.com/WRF-CMake/WPS/releases/download/WPS-CMake-4.0/wps-cmake-4.0-serial-basic-release-macos.tar.xz',
        'dmpar': 'https://github.com/WRF-CMake/WPS/releases/download/WPS-CMake-4.0/wps-cmake-4.0-dmpar-basic-release-macos.tar.xz'
    },
    'Linux': {
        'serial': 'https://github.com/WRF-CMake/WPS/releases/download/WPS-CMake-4.0/wps-cmake-4.0-serial-basic-release-linux.tar.xz',
        'dmpar': 'https://github.com/WRF-CMake/WPS/releases/download/WPS-CMake-4.0/wps-cmake-4.0-dmpar-basic-release-linux.tar.xz'
    }
}