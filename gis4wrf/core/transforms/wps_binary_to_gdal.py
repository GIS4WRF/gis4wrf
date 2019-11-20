# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Tuple, Callable
import os
import re
from functools import partial


from gis4wrf.core.util import export, gdal, get_temp_dir, get_temp_vsi_path, remove_dir, remove_vsis
from gis4wrf.core.errors import UserError, UnsupportedError
from gis4wrf.core.crs import CRS, LonLat
from gis4wrf.core.readers.wps_binary_index import read_wps_binary_index_file
from .categories_to_gdal import get_gdal_categories

@export
def convert_wps_binary_to_vrt_dataset(folder: str, use_vsi: bool=False) -> Tuple[str,str,str,Callable[[],None]]:
    """Converts a WPS Binary format dataset into a mosaic VRT dataset referencing per-tile VRT datasets."""

    m = read_wps_binary_index_file(folder)

    if m.proj_id == 'regular_ll' and m.stdlon is not None:
        raise UnsupportedError('Rotated pole system is not supported')

    # scan folder for available tiles
    tile_filename_re = re.compile('^({d})-({d})\.({d})-({d})$'.format(d='\d{' + str(m.filename_digits) + '}'))
    tiles = []
    for filename in os.listdir(folder):
        match = tile_filename_re.match(filename)
        if match:
            tiles.append({
                'filename': filename,
                'path': os.path.join(folder, filename),
                'start_x': int(match.group(1)),
                'end_x': int(match.group(2)),
                'start_y': int(match.group(3)),
                'end_y': int(match.group(4))
            })
    if not tiles:
        raise UserError(f'No tiles found in {folder}')

    # determine raster dimensions
    xsize = max(tile['end_x'] for tile in tiles) # type: int
    ysize = max(tile['end_y'] for tile in tiles) # type: int
    zsize = m.tile_z_end - m.tile_z_start + 1

    # convert to GDAL metadata
    dtype_mapping = {
        (1, False): gdal.GDT_Byte, # GDAL only supports unsigned byte
        (2, False): gdal.GDT_UInt16,
        (2, True): gdal.GDT_Int16,
        (3, False): gdal.GDT_UInt32,
        (3, True): gdal.GDT_Int32
    }
    try:
        dtype = dtype_mapping[(m.word_size, m.signed)]
    except KeyError:
        raise UnsupportedError('word_size={} signed={} is not supported'.format(
            m.word_size, m.signed))

    if m.proj_id == 'regular_ll':
        crs = CRS.create_lonlat()
    elif m.proj_id == 'lambert':
        # The map distortion of a Lambert Conformal projection is fully
        # defined by the two true latitudes.
        #
        # However, the longitude of origin is important for WRF as well,
        # since we only deal with upright rectangles (the domains) on the map.
        # For that reason, WRF allows the user to define the "standard longitude"
        # which is the longitude of origin.
        #
        # The latitude of origin on the other hand does not have any significance
        # here and cannot be specified by the user. The geo transform for a given
        # grid is computed based on any arbitrary latitude of origin (see below).
        # In QGIS, the only difference are the displayed projected y coordinates,
        # but the actual grid georeferencing is unaffected.
        # This is possible as WRF's georeferencing metadata is based on geographical
        # reference coordinates for a grid cell, not projected coordinates.
        arbitrary_latitude_origin = (m.truelat1 + m.truelat2)/2
        origin = LonLat(lon=m.stdlon, lat=arbitrary_latitude_origin)
        crs = CRS.create_lambert(m.truelat1, m.truelat2, origin)
    elif m.proj_id == 'mercator':
        # The map distortion of a Mercator projection is fully
        # defined by the true latitude.
        # The longitude of origin does not have any significance and
        # any arbitrary value is handled when computing the geo transform
        # for a given grid (see below). See also the comment above for Lambert.
        arbitrary_longitude_origin = 0
        crs = CRS.create_mercator(m.truelat1, arbitrary_longitude_origin)
    elif m.proj_id == 'albers_nad83':
        # See the comment above for Lambert. The same applies here.
        arbitrary_latitude_origin = (m.truelat1 + m.truelat2)/2
        origin = LonLat(lon=m.stdlon, lat=arbitrary_latitude_origin)
        crs = CRS.create_albers_nad83(m.truelat1, m.truelat2, origin)
    # FIXME handle polar vs polar_wgs84 differently
    elif m.proj_id == 'polar':
        # See the comment above for Lambert. The same applies here.
        crs = CRS.create_polar(m.truelat1, m.stdlon)
    elif m.proj_id == 'polar_wgs84':
        # See the comment above for Lambert. The same applies here.
        crs = CRS.create_polar(m.truelat1, m.stdlon)
    else:
        raise UnsupportedError(f'Projection {m.proj_id} is not supported')

    known_x_idx_gdal = m.known_idx.x - 0.5
    if m.top_bottom:
        known_y_idx_gdal = ysize - m.known_idx.y - 0.5
        dy_gdal = -m.dy
    else:
        known_y_idx_gdal = m.known_idx.y - 0.5
        dy_gdal = m.dy

    known_xy = crs.to_xy(m.known_lonlat)
    upper_left_x = known_xy.x - known_x_idx_gdal * m.dx
    upper_left_y = known_xy.y + known_y_idx_gdal * m.dy
    geo_transform = (upper_left_x, m.dx, 0, upper_left_y, 0, dy_gdal)

    # print('known_x_idx_gdal: {}'.format(known_x_idx_gdal))
    # print('known_y_idx_gdal: {}'.format(known_y_idx_gdal))
    # print('known_xy: {}'.format(m.known_xy))
    # print('upper_left_x: {}'.format(upper_left_x))
    # print('upper_left_y: {}'.format(upper_left_y))

    # VRTRawRasterBand metadata
    line_width = m.word_size * (m.tile_x + m.tile_bdr * 2) # x size incl. border
    tile_size = line_width * (m.tile_y + m.tile_bdr * 2) # tile size incl. border
    line_offset = line_width
    image_offset = m.tile_bdr * line_width + m.tile_bdr * m.word_size
    pixel_offset = m.word_size
    byte_order = 'LSB' if m.little_endian else 'MSB'

    # create tile VRTs
    if use_vsi:
        out_dir = get_temp_vsi_path(ext='')
    else:
        out_dir = get_temp_dir()

    driver = gdal.GetDriverByName('VRT') # type: gdal.Driver
    tile_vrt_paths = {}
    for tile in tiles:
        vsi_path = '{}/{}.vrt'.format(out_dir, tile['filename'])
        vrt = driver.Create(vsi_path, m.tile_x, m.tile_y, 0) # type: gdal.Dataset

        for z in range(m.tile_z_start - 1, m.tile_z_end):
            options = [
                'subClass=VRTRawRasterBand',
                'SourceFilename={}'.format(tile['path']),
                'relativeToVRT=0',
                'ImageOffset={}'.format(z * tile_size + image_offset),
                'PixelOffset={}'.format(pixel_offset),
                'LineOffset={}'.format(line_offset),
                'ByteOrder=' + byte_order
            ]
            vrt.AddBand(dtype, options)
        vrt.FlushCache()

        tile_vrt_paths[tile['filename']] = vsi_path

    # create mosaic VRT
    mosaic_vrt_path = '{}/mosaic.vrt'.format(out_dir)
    vrt = driver.Create(mosaic_vrt_path, xsize, ysize, zsize, dtype) # type: gdal.Dataset
    vrt.SetProjection(crs.wkt)
    vrt.SetGeoTransform(geo_transform)

    if m.categorical:
        color_table, cat_names = get_gdal_categories(m.categories, m.category_min, m.category_max)

    for band_idx in range(1, zsize + 1):
        band = vrt.GetRasterBand(band_idx) # type: gdal.Band
        if m.missing_value is not None:
            band.SetNoDataValue(m.missing_value)

        band.SetScale(m.scale_factor)

        if m.categorical:
            band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
            band.SetRasterColorTable(color_table)
            band.SetRasterCategoryNames(cat_names)

        sources = {}
        for idx, tile in enumerate(tiles):
            tile_vrt_path = tile_vrt_paths[tile['filename']]

            if m.top_bottom:
                end_y = ysize - tile['start_y'] - 1
                start_y = end_y - m.tile_y + 1
            else:
                start_y = tile['start_y'] - 1

            sources['source_{}'.format(idx)] = ('''
                <SimpleSource>
                    <SourceFilename relativeToVRT="0">{path}</SourceFilename>
                    <SourceBand>{band}</SourceBand>
                    <SrcRect xOff="0" yOff="0" xSize="{tile_x}" ySize="{tile_y}" />
                    <DstRect xOff="{offset_x}" yOff="{offset_y}" xSize="{tile_x}" ySize="{tile_y}" />
                </SimpleSource>''').format(
                    path=tile_vrt_path, band=band_idx,
                    tile_x=m.tile_x, tile_y=m.tile_y,
                    offset_x=tile['start_x']-1, offset_y=start_y)
        band.SetMetadata(sources, 'vrt_sources')

    vrt.FlushCache()

    vrt_paths = [mosaic_vrt_path] + list(tile_vrt_paths.values())
    if use_vsi:
        dispose = partial(remove_vsis, vrt_paths)
    else:
        dispose = partial(remove_dir, out_dir)

    short_name = os.path.basename(folder)
    title = short_name
    if m.units and m.units != 'category':
        title += ' in ' + m.units
    if m.description:
        title += ' (' + m.description + ')'

    # The title is returned as VRT does not support dataset descriptions.
    return mosaic_vrt_path, title, short_name, dispose
