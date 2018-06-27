from gis4wrf.core.util import export, ogr

# TODO currently unused, remove?
#      can be used to save domain outlines to shapefiles
#      (see project_to_gdal_outlines module)
@export
def write_shapefile(path: str, data: ogr.DataSource) -> None:
    drv = ogr.GetDriverByName('ESRI Shapefile') # type: ogr.Driver
    ds = drv.CopyDataSource(data, path) # type: ogr.DataSource