# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from gis4wrf.core.constants import WRF_EARTH_RADIUS
from gis4wrf.core.util import osr, ogr, export, as_float, Number

@export
class Coordinate2D(object):
    def __init__(self, x: Number, y: Number) -> None:
        self.x = as_float(x)
        self.y = as_float(y)

    def __eq__(self, other) -> bool:
        return self.x == other.x and self.y == other.y

    def __repr__(self) -> str:
        return 'Coordinate2D(x={}, y={})'.format(self.x, self.y)

@export
class LonLat(Coordinate2D):
    def __init__(self, lon: Number, lat: Number) -> None:
        super().__init__(lon, lat)

    @property
    def lon(self) -> float:
        return self.x

    @property
    def lat(self) -> float:
        return self.y

    def __repr__(self) -> str:
        return 'LonLat(lon={}, lat={})'.format(self.lon, self.lat)

@export
class BoundingBox2D(object):
    def __init__(self, minx: Number, miny: Number, maxx: Number, maxy: Number) -> None:
        assert minx <= maxx
        assert miny <= maxy
        self.minx = as_float(minx)
        self.miny = as_float(miny)
        self.maxx = as_float(maxx)
        self.maxy = as_float(maxy)

    @property
    def bottom_left(self) -> Coordinate2D:
        return Coordinate2D(x=self.minx, y=self.miny)

    @property
    def bottom_right(self) -> Coordinate2D:
        return Coordinate2D(x=self.maxx, y=self.miny)

    @property
    def top_left(self) -> Coordinate2D:
        return Coordinate2D(x=self.minx, y=self.maxy)

    @property
    def top_right(self) -> Coordinate2D:
        return Coordinate2D(x=self.maxx, y=self.maxy)

    def __eq__(self, other) -> bool:
        return self.minx == other.minx and \
               self.miny == other.miny and \
               self.maxx == other.maxx and \
               self.maxy == other.maxy

    def __repr__(self) -> str:
        return 'BoundingBox2D(minx={}, miny={}, maxx={}, maxy={})'.format(self.minx, self.miny, self.maxx, self.maxy)

@export
class CRS(object):
    #FIXME: temporary fix -- we assume that the datum is WGS84 sphere and not lat-lon
    WRF_DATUM_PROJ4 = '+datum=WGS84'
    # '+towgs84=0,0,0 {sphere}'.format(sphere=WRF_PROJ4_SPHERE)

    def __init__(self, proj4: str=None, srs: osr.SpatialReference=None) -> None:
        if proj4:
            self.proj4 = proj4 + ' +no_defs'
        else:
            self.proj4 = srs.ExportToProj4()

    def __repr__(self) -> str:
        return 'CRS(proj4="{}")'.format(self.proj4)

    @staticmethod
    def create_lonlat():
        return CRS('+proj=latlong ' + CRS.WRF_DATUM_PROJ4)

    @staticmethod
    def create_lambert(truelat1: float, truelat2: float, origin: LonLat):
        assert truelat1 is not None
        assert truelat2 is not None
        assert origin is not None
        return CRS(
            ('+proj=lcc +lat_1={lat1} +lat_2={lat2} +lat_0={lat0} +lon_0={lon0} '
             '+x_0=0 +y_0=0 {datum}').format(
                 lat1=truelat1, lat2=truelat2,
                 lon0=origin.lon, lat0=origin.lat,
                 datum=CRS.WRF_DATUM_PROJ4))

    @staticmethod
    def create_albers_nad83(truelat1: float, truelat2: float, origin: LonLat):
        assert truelat1 is not None
        assert truelat2 is not None
        assert origin is not None
        return CRS(
            ('+proj=aea +lat_1={lat1} +lat_2={lat2} +lat_0={lat0} +lon_0={lon0} '
             '+x_0=0 +y_0=0 +datum=NAD83').format(
                 lat1=truelat1, lat2=truelat2,
                 lon0=origin.lon, lat0=origin.lat,
                 datum=CRS.WRF_DATUM_PROJ4))

    @staticmethod
    def create_mercator(truelat1: float, origin_lon: float):
        ''' Note: Latitude of origin is always the equator. '''
        assert truelat1 is not None
        assert origin_lon is not None
        return CRS(
            ('+proj=merc +lat_ts={lat1} +lon_0={lon0} '
             '+x_0=0 +y_0=0 {datum}').format(
                 lat1=truelat1, lon0=origin_lon,
                 datum=CRS.WRF_DATUM_PROJ4))

    @staticmethod
    def create_polar(truelat1: float, origin_lon: float):
        assert truelat1 is not None
        assert origin_lon is not None
        return CRS(
            ('+proj=stere +lat_ts={lat1} +lat_0={lat0} +lon_0={lon0} '
             '+x_0=0 +y_0=0 {datum}').format(
                 lat1=truelat1, lon0=origin_lon,
                 lat0=90 if truelat1 > 0 else -90,
                 datum=CRS.WRF_DATUM_PROJ4))

    @property
    def srs(self) -> osr.SpatialReference:
        srs = osr.SpatialReference()
        srs.ImportFromProj4(self.proj4)
        return srs

    @property
    def wkt(self) -> str:
        return self.srs.ExportToWkt()

    def to_xy(self, latlon: LonLat) -> Coordinate2D:
        ''' Convert from geographic coordinates using the same datum as this CRS to avoid datum shift. '''
        return self.transform_point(srs_in=self.lonlat_srs, srs_out=self.srs, point=latlon)

    def to_lonlat(self, point: Coordinate2D) -> LonLat:
        ''' Convert to geographic coordinates using the same datum as this CRS to avoid datum shift. '''
        out = self.transform_point(srs_in=self.srs, srs_out=self.lonlat_srs, point=point)
        return LonLat(lon=out.x, lat=out.y)

    def transform(self, point: Coordinate2D, srs_out: osr.SpatialReference) -> Coordinate2D:
        ''' Convert to coordinates in given system. Note that datum shift may be applied.
            Use to_xy and to_lonlat to avoid that. '''
        return self.transform_point(self.srs, srs_out, point)

    def transform_bbox(self, bbox: BoundingBox2D, srs_out: osr.SpatialReference) -> BoundingBox2D:
        # convert bbox corners to domain crs and then re-compute bbox
        # If the CRSs are different the resulting bbox may not fully cover the input bbox.
        # To achieve that we would have to trace along the input bbox edges.
        # TODO add option to trace along bbox
        bottom_left = self.transform(bbox.bottom_left, srs_out)
        bottom_right = self.transform(bbox.bottom_right, srs_out)
        top_left = self.transform(bbox.top_left, srs_out)
        top_right = self.transform(bbox.top_right, srs_out)
        minx = min(bottom_left.x, bottom_right.x, top_left.x, top_right.x)
        maxx = max(bottom_left.x, bottom_right.x, top_left.x, top_right.x)
        miny = min(bottom_left.y, bottom_right.y, top_left.y, top_right.y)
        maxy = max(bottom_left.y, bottom_right.y, top_left.y, top_right.y)
        return BoundingBox2D(minx=minx, miny=miny, maxx=maxx, maxy=maxy)

    @staticmethod
    def is_wrf_sphere_datum(srs: osr.SpatialReference) -> bool:
        return srs.GetSemiMajor() == srs.GetSemiMinor() == WRF_EARTH_RADIUS

    @property
    def lonlat_srs(self) -> osr.SpatialReference:
        ''' Return a Lat/Lon CRS using the same datum as used in this object's CRS. '''
        srs = self.srs
        datum = self.srs.GetAttrValue('datum')
        srs_out = osr.SpatialReference()
        srs_out.SetGeogCS('', datum, '', srs.GetSemiMajor(), srs.GetInvFlattening())
        assert not srs_out.EPSGTreatsAsLatLong(), 'expected lon/lat axis order'
        return srs_out

    @staticmethod
    def transform_point(srs_in: osr.SpatialReference, srs_out: osr.SpatialReference, point: Coordinate2D) -> Coordinate2D:
        point_geom = ogr.Geometry(ogr.wkbPoint)
        point_geom.AddPoint(point.x, point.y)
        transform = osr.CoordinateTransformation(srs_in, srs_out)
        point_geom.Transform(transform)
        return Coordinate2D(x=point_geom.GetX(), y=point_geom.GetY())