# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

import os
import sys
from collections import namedtuple

import numpy as np
import pytest

from gis4wrf.bootstrap import bootstrap
for t, v in bootstrap():
    print('{}: {}'.format(t, v))

from gis4wrf.core.constants import WRF_PROJ4_SPHERE
from gis4wrf.core import Coordinate2D
from gis4wrf.core.util import osr, gdal, gdal_array

# check if GDAL has access to its data folder (CRS database etc.)
assert 'GDAL_DATA' in os.environ
assert '"' not in os.environ['GDAL_DATA'],\
    "Your conda gdal install is broken, see https://github.com/ContinuumIO/anaconda-issues/issues/2167"

Bounds2D = namedtuple('Bounds2D', ['min', 'max'])


@pytest.fixture(scope="session",
                params=["lonlat", "lambert", "albers_nad83", "mercator", "polar_wgs84", "polar"])
def landcover_dataset_path(request, tmpdir_factory):
    ''' Generate a landcover dataset with geographic CRS, save as GeoTIFF, and return path. '''
    proj = request.param
    path = str(tmpdir_factory.mktemp('data').join('lc_{}.geotiff'.format(proj)))
    data = np.arange(8, dtype=np.uint8).reshape(2, 4)
    crs = osr.SpatialReference()

    if proj == 'lonlat':
        bounds = Bounds2D(min=Coordinate2D(x=150, y=60), max=Coordinate2D(x=154, y=62))
        crs.ImportFromProj4('+proj=latlong {sphere} +no_defs '.format(sphere=WRF_PROJ4_SPHERE))
        assert not crs.EPSGTreatsAsLatLong(), "expected lon/lat axis order"

    elif proj == 'lambert':
        bounds = Bounds2D(min=Coordinate2D(x=-600000, y=-1000000), max=Coordinate2D(x=-500000, y=-800000))
        # The following is EPSG:42304 with datum replaced by the WRF sphere (original is NAD83)
        crs.ImportFromProj4(
            ('+proj=lcc +lat_1=49 +lat_2=77 +lat_0=49 +lon_0=-95 '
             '+x_0=0 +y_0=0 +units=m {sphere} +no_defs').format(sphere=WRF_PROJ4_SPHERE))

    elif proj == 'albers_nad83':
        bounds = Bounds2D(min=Coordinate2D(x=1600000, y=500000), max=Coordinate2D(x=1700000, y=600000))
        crs.ImportFromEPSG(3005)

    elif proj == 'mercator':
        bounds = Bounds2D(min=Coordinate2D(x=1300000, y=6500000), max=Coordinate2D(x=1400000, y=6600000))
        # The following is EPSG:3395 with datum replaced by the WRF sphere (original is WGS84)
        crs.ImportFromProj4(
            ('+proj=merc +lon_0=0 +lat_ts=40 +x_0=0 +y_0=0 +units=m {sphere} +no_defs').format(sphere=WRF_PROJ4_SPHERE))

    elif proj == 'polar_wgs84':
        bounds = Bounds2D(min=Coordinate2D(x=6000000, y=6100000), max=Coordinate2D(x=7000000, y=6500000))
        crs.ImportFromEPSG(3032)

    elif proj == 'polar':
        bounds = Bounds2D(min=Coordinate2D(x=6000000, y=6100000), max=Coordinate2D(x=7000000, y=6500000))
        # The following is EPSG:3032 with datum replaced by the WRF sphere (original is WGS84)
        crs.ImportFromProj4(
            ('+proj=stere +lat_0=-90 +lat_ts=-71 +lon_0=70 +k=1 '
             '+x_0=6000000 +y_0=6000000 +units=m {sphere} +no_defs').format(sphere=WRF_PROJ4_SPHERE))

    array_to_raster(path, data, bounds, crs)
    return path


def array_to_raster(path, array, bounds, crs):
    '''
    path: str
    array: 2D array, north up (array[0,0] is most north west pixel)
    bounds: Bounds2D, minimum and maximum extent of data in CRS coordinates (measured at corners of pixels)
    :param osgeo.osr.SpatialReference crs: the CRS to be used
    '''

    # TODO generalize to arbitrary number of bands
    rows, cols = array.shape
    bands = 1

    # Image pixel coordinates start at (0,0) which corresponds to the top left corner of array[0,0]

    # CRS coordinates of top left corner of array[0,0]
    origin_x = bounds.min.x
    origin_y = bounds.max.y

    # Size in CRS units of each array element
    pixel_width = (bounds.max.x - bounds.min.x)/cols
    pixel_height = (bounds.max.y - bounds.min.y)/rows

    assert pixel_width > 0
    assert pixel_height > 0

    # Setup driver
    driver = gdal.GetDriverByName('GTiff')
    type_code = gdal_array.NumericTypeCodeToGDALTypeCode(array.dtype)
    out_raster = driver.Create(path, cols, rows, bands, type_code)
    out_raster.SetGeoTransform((origin_x, pixel_width, 0, origin_y, 0, -pixel_height))

    # Write input data to first raster band
    out_raster.GetRasterBand(1).WriteArray(array)

    # Set projection
    wkt = crs.ExportToWkt()
    out_raster.SetProjection(wkt)

    # Write to disk
    out_raster.FlushCache()
