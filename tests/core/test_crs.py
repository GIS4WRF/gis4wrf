# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2019 D. Meyer and M. Riechert. Licensed under MIT.

import pytest

from gis4wrf.core import (
    CRS, LonLat, Coordinate2D
)

@pytest.mark.parametrize('crs_name', ['lonlat', 'lambert', 'mercator', 'polar', 'albers_nad83'])
def test_geo_roundtrip(crs_name: str):
    if crs_name == 'lonlat':
        crs = CRS.create_lonlat()
    elif crs_name == 'lambert':
        crs = CRS.create_lambert(truelat1=3.5, truelat2=7, origin=LonLat(lon=4, lat=0))
    elif crs_name == 'mercator':
        crs = CRS.create_mercator(truelat1=3.5, origin_lon=4)
    elif crs_name == 'polar':
        crs = CRS.create_polar(truelat1=3.5, origin_lon=4)
    elif crs_name == 'albers_nad83':
        crs = CRS.create_albers_nad83(truelat1=3.5, truelat2=7, origin=LonLat(lon=4, lat=0))
    lonlat = LonLat(lon=10, lat=30)
    xy = crs.to_xy(lonlat)
    lonlat2 = crs.to_lonlat(xy)
    assert lonlat.lon == pytest.approx(lonlat2.lon)
    assert lonlat.lat == pytest.approx(lonlat2.lat)

@pytest.mark.parametrize('crs_name', ['lambert', 'mercator', 'polar', 'albers_nad83'])
def test_projection_origin(crs_name: str):
    origin_lonlat = LonLat(lon=4, lat=0)
    if crs_name == 'lambert':
        crs = CRS.create_lambert(truelat1=3.5, truelat2=7, origin=origin_lonlat)
    elif crs_name == 'mercator':
        crs = CRS.create_mercator(truelat1=3.5, origin_lon=origin_lonlat.lon)
    elif crs_name == 'polar':
        origin_lonlat = LonLat(lon=origin_lonlat.lon, lat=90)
        crs = CRS.create_polar(truelat1=3.5, origin_lon=origin_lonlat.lon)
    elif crs_name == 'albers_nad83':
        crs = CRS.create_albers_nad83(truelat1=3.5, truelat2=7, origin=origin_lonlat)
    origin_xy = crs.to_xy(origin_lonlat)
    assert origin_xy.x == pytest.approx(0)
    assert origin_xy.y == pytest.approx(0, abs=1e-9)
