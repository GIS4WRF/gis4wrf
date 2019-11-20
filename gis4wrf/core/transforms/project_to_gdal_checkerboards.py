# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List

from gis4wrf.core.project import Project
from gis4wrf.core.util import (
    export, gdal, get_temp_vsi_path, read_vsi_string,
    fix_pixelfunction_vrt
)

@export
def convert_project_to_gdal_checkerboards(project: Project) -> List[str]:
    # https://github.com/OSGeo/gdal/blob/master/autotest/gdrivers/vrtderived.py
    vsi_path = get_temp_vsi_path()

    domains = project.data['domains']
    bboxes = project.bboxes
    vrts = []
    for idx, domain in enumerate(domains):
        bbox = bboxes[idx]
        dx, dy = domain['cell_size']
        w, h = domain['domain_size_padded']

        geo_transform = (bbox.minx, dx, 0, bbox.maxy, 0, -dy)

        driver = gdal.GetDriverByName('VRT') # type: gdal.Driver
        vrt_ds = driver.Create(vsi_path, w, h, 0) # type: gdal.Dataset
        vrt_ds.SetProjection(project.projection.wkt)
        vrt_ds.SetGeoTransform(geo_transform)

        options = [
            'subClass=VRTDerivedRasterBand',
            'PixelFunctionLanguage=Python',
            'PixelFunctionType=gis4wrf.core.gdal_checkerboard_pixelfunction'
        ]
        vrt_ds.AddBand(gdal.GDT_Byte, options)
        vrt_ds.FlushCache()
        vrt = read_vsi_string(vsi_path)

        # PixelFunctionLanguage is lost, see https://github.com/OSGeo/gdal/issues/501.
        # This function call fixes that for older gdal versions.
        vrt = fix_pixelfunction_vrt(vrt)

        vrts.append(vrt)

    return vrts

@export
def gdal_checkerboard_pixelfunction(in_ar, out_ar, xoff, yoff, xsize, ysize, raster_xsize,
                                    raster_ysize, buf_radius, gt):
    '''
        Documentation from http://www.gdal.org/gdal_vrttut.html:
        in_ar: list of input NumPy arrays (one NumPy array for each source)
        out_ar: output NumPy array to fill. The array is initialized at the right dimensions and with the VRTRasterBand.dataType.
        xoff: pixel offset to the top left corner of the accessed region of the band. Generally not needed except if the processing depends on the pixel position in the raster.
        yoff: line offset to the top left corner of the accessed region of the band. Generally not needed.
        xsize: width of the region of the accessed region of the band. Can be used together with out_ar.shape[1] to determine the horizontal resampling ratio of the request.
        ysize: height of the region of the accessed region of the band. Can be used together with out_ar.shape[0] to determine the vertical resampling ratio of the request.
        raster_xsize: total with of the raster band. Generally not needed.
        raster_ysize: total with of the raster band. Generally not needed.
        buf_radius: radius of the buffer (in pixels) added to the left, right, top and bottom of in_ar / out_ar.
                    This is the value of the optional BufferRadius element that can be set so that the original
                    pixel request is extended by a given amount of pixels.
        gt: geotransform. Array of 6 double values.
    '''
    x_even = xoff % 2 == 0
    y_even = yoff % 2 == 0
    is_white = (x_even and y_even) or (not x_even and not y_even)
    out_ar[:] = 1 - is_white
    out_ar[::2, 1::2] = is_white
    out_ar[1::2, ::2] = is_white