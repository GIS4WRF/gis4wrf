# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Optional, Tuple, Dict, Any, Iterable, Union
from decimal import Decimal
import math
import os
import sys
import shutil
import errno
import tempfile
import pathlib
import xml.etree.ElementTree as ET
from itertools import product
from collections import namedtuple

import numpy as np
import numpy.ma as ma

from gis4wrf.core.constants import WRF_EARTH_RADIUS
from gis4wrf.core.util import export, gdal, gdal_array, ogr, osr
from gis4wrf.core.crs import CRS, Coordinate2D, LonLat

# Maximum number of rows or columns that a WPS binary format file can have.
MAX_SIZE = 999999
TILE_THRESHOLD = 2400 # axis size after which tiling is applied

# Size-ordered GDAL data types.
DTYPE_INT_UNSIGNED = [
    gdal.GDT_Byte,
    gdal.GDT_UInt16,
    gdal.GDT_UInt32
]

DTYPE_INT_SIGNED = [
    gdal.GDT_Int16,
    gdal.GDT_Int32
]

DTYPE_INT = DTYPE_INT_UNSIGNED + DTYPE_INT_SIGNED

DTYPE_FLOAT = [
    gdal.GDT_Float32,
    gdal.GDT_Float64
]


def gdal_dtype_is_integer(dtype: int) -> bool:
    return dtype in DTYPE_INT


def gdal_dtype_is_signed(dtype: int) -> bool:
    return dtype in DTYPE_INT_SIGNED


def get_gdal_dtype_range(dtype: int) -> Tuple[int,int]:
    np_dtype = gdal_array.GDALTypeCodeToNumericTypeCode(dtype)
    return (np.iinfo(np_dtype).min, np.iinfo(np_dtype).max)


def get_optimal_dtype(min_: float, max_: float) -> int:
    dtypes = DTYPE_INT_SIGNED if min_ < 0 else DTYPE_INT_UNSIGNED
    for dtype in dtypes:
        dtype_min, dtype_max = get_gdal_dtype_range(dtype)
        if dtype_min <= min_ <= max_ <= dtype_max:
            return dtype
    raise ValueError('Data value range exceeds available GDAL data type ranges')


def get_no_data_value(dtype: int, min_: float, max_: float) -> float:
    dtype_min, dtype_max = get_gdal_dtype_range(dtype)
    if max_ < dtype_max:
        return dtype_max
    elif dtype_min < min_:
        return dtype_min
    else:
        raise ValueError('Unable to compute no-data value as data value range is equal to data type range')


GeogridBinaryDataset = namedtuple('GeogridBinaryDataset', ['index_path', 'datum_mismatch'])
DatumMismatch = namedtuple('DatumMismatch', ['expected', 'actual'])

def find_tile_size(axis_size: int, try_hard: bool) -> int:
    if axis_size <= TILE_THRESHOLD:
        return axis_size
    # try to find a tile size that is a multiple of the axis size
    for tile_size in range(3000, 1000, -100):
        if axis_size % tile_size == 0:
            return tile_size
    if try_hard:
        for tile_size in range(4000, 100, -1):
            if axis_size % tile_size == 0:
                return tile_size
    return TILE_THRESHOLD

@export
def convert_to_wps_binary(input_path: str, output_folder: str, is_categorical: bool,
                          units: Optional[str]=None, description: Optional[str]=None,
                          strict_datum: bool=True) -> GeogridBinaryDataset:
    '''
    Losslessly convert common geo formats to WPS binary format.
    If the given input file has a CRS or data type unsupported by WRF then an error is raised.

    :param input_path: Path to GDAL-supported raster file.
    :param output_folder: Path to output folder, will be created if not existing
    :param is_categorical: Whether the data is categorical, otherwise continuous
    :param units: units for continuous data
    :param description: single-line dataset description
    :param strict_datum: if True, fail if the input datum is not supported by WRF, otherwise ignore mismatch
    '''
    os.makedirs(output_folder, exist_ok=True)
    if os.listdir(output_folder):
        raise ValueError("Output folder must be empty")

    # FIXME if there is no nodata value, ask the user if it really has no nodata or ask for the value

    src_ds = gdal.Open(input_path) # type: gdal.Dataset
    xsize, ysize = src_ds.RasterXSize, src_ds.RasterYSize
    if xsize > MAX_SIZE or ysize > MAX_SIZE:
        raise ValueError('Dataset has more than {} rows or columns: {} x {}'.format(MAX_SIZE, ysize, xsize))

    filename_digits = 6 if xsize > 99999 or ysize > 99999 else 5

    if src_ds.GetLayerCount() > 1:
        raise ValueError('Dataset has more than one layer')

    band = src_ds.GetRasterBand(1) # type: gdal.Band
    src_no_data_value = band.GetNoDataValue()
    has_no_data_value = src_no_data_value is not None

    tilesize_x = find_tile_size(xsize, try_hard=not has_no_data_value)
    tilesize_y = find_tile_size(ysize, try_hard=not has_no_data_value)
    is_perfect_tiling = xsize % tilesize_x == 0 and ysize % tilesize_y == 0

    if is_categorical or (tilesize_x == xsize and tilesize_y == ysize):
        tile_bdr = 0
    else:
        # TODO write unit test that checks whether halo areas have correct values
        tile_bdr = 3

    if tile_bdr > 0 and not has_no_data_value:
        raise ValueError('No-data value required as dataset is continuous and halo is non-zero')

    if not is_perfect_tiling and not has_no_data_value:
        raise ValueError('No-data value required as no perfect tile size could be found')

    tilesize_bdr_x = tilesize_x + 2*tile_bdr
    tilesize_bdr_y = tilesize_y + 2*tile_bdr

    tiles_x = list(range(0, xsize, tilesize_x))
    tiles_y = list(range(0, ysize, tilesize_y))
    ysize_pad = tilesize_y * len(tiles_y) # ysize including padding caused by imperfect tiling

    # write 'index' file with metadata
    index_path = os.path.join(output_folder, 'index')
    index_dict, datum_mismatch, inv_scale_factor, dst_dtype, dst_no_data_value = create_index_dict(
        src_ds, tilesize_x, tilesize_y, ysize_pad, tile_bdr, filename_digits,
        is_categorical, units, description, strict_datum)
    write_index_file(index_path, index_dict)

    np_dst_dtype = gdal_array.GDALTypeCodeToNumericTypeCode(dst_dtype)
    needs_scaling = inv_scale_factor is not None

    # As we have no control over the auxiliarly files that are created as well during conversion
    # we do everything in a temporary folder and move the binary file out after the conversion.
    # This keeps everything clean and tidy.
    tmp_dir = tempfile.mkdtemp()
    tmp_bin_path = os.path.join(tmp_dir, 'data.bin')

    driver = gdal.GetDriverByName('ENVI') # type: gdal.Driver#

    dy = src_ds.GetGeoTransform()[5]

    try:
        for start_x in tiles_x:
            for start_y in tiles_y:
                end_x = start_x + tilesize_x - 1
                end_y = start_y + tilesize_y - 1
                start_bdr_x = start_x - tile_bdr
                start_bdr_y = start_y - tile_bdr
                end_bdr_x = end_x + tile_bdr
                end_bdr_y = end_y + tile_bdr

                # read source data
                offset_x = max(0, start_bdr_x)
                offset_y = max(0, start_bdr_y)
                if end_bdr_x >= xsize:
                    datasize_x = xsize - offset_x
                else:
                    datasize_x = end_bdr_x - offset_x + 1

                if end_bdr_y >= ysize:
                    datasize_y = ysize - offset_y
                else:
                    datasize_y = end_bdr_y - offset_y + 1

                src_data = band.ReadAsArray(offset_x, offset_y, datasize_x, datasize_y)
                if dy > 0:
                    src_data = src_data[::-1]

                # scale if necessary (float data only)
                if needs_scaling:
                    # TODO test if scaling with no-data works
                    if has_no_data_value:
                        src_data = ma.masked_equal(src_data, src_no_data_value)
                    src_data *= inv_scale_factor
                    np.round(src_data, out=src_data)
                    if has_no_data_value:
                        src_data = ma.filled(src_data, dst_no_data_value)

                # pad incomplete tile with nodata value
                if datasize_x == tilesize_bdr_x and datasize_y == tilesize_bdr_y:
                    dst_data = src_data
                else:
                    assert has_no_data_value
                    dst_data = np.empty((tilesize_bdr_y, tilesize_bdr_x), np_dst_dtype)
                    data_start_x = offset_x - start_bdr_x
                    data_start_y = offset_y - start_bdr_y
                    dst_data[data_start_y:data_start_y+datasize_y,data_start_x:data_start_x+datasize_x] = src_data

                    if start_bdr_x < 0:
                        dst_data[:,:data_start_x] = dst_no_data_value
                    if start_bdr_y < 0:
                        dst_data[:data_start_y,:] = dst_no_data_value
                    if end_bdr_x >= xsize:
                        dst_data[:,data_start_x+datasize_x:] = dst_no_data_value
                    if end_bdr_y >= ysize:
                        dst_data[data_start_y+datasize_y:,:] = dst_no_data_value


                # create tile file
                dst_ds = driver.Create(tmp_bin_path, tilesize_bdr_x, tilesize_bdr_y, 1, dst_dtype) # type: gdal.Dataset
                dst_band = dst_ds.GetRasterBand(1) # type: gdal.Band
                dst_band.WriteArray(dst_data)

                # write to disk
                dst_ds.FlushCache()
                del dst_ds

                # move to final location with WPS-specific filename convention
                fmt_int = '{:0' + str(filename_digits) + 'd}'
                fmt_filename = '{fmt}-{fmt}.{fmt}-{fmt}'.format(fmt=fmt_int)
                if dy < 0:
                    end_y = ysize_pad - start_y - 1
                    start_y = end_y - tilesize_y + 1
                final_path = os.path.join(output_folder, fmt_filename.format(
                    start_x + 1, end_x + 1, start_y + 1, end_y + 1))
                shutil.move(tmp_bin_path, final_path)

        return GeogridBinaryDataset(index_path, datum_mismatch)
    finally:
        shutil.rmtree(tmp_dir)

INDEX_FIELDS_QUOTED = ['units', 'description', 'MMINLU']


def create_index_dict(dataset: gdal.Dataset, tilesize_x: int, tilesize_y: int, ysize_pad: int, tile_bdr: int,
                      filename_digits: int, is_categorical: bool,
                      units: Optional[str]=None, description: Optional[str]=None,
                      strict_datum: bool=True) -> Tuple[Dict[str, Any], DatumMismatch, Optional[float], int, Optional[float]]:
    '''
    Returns a dictionary that can be used for writing a WPS Binary format index file.
    If the given dataset has a CRS or data type unsupported by WRF then an error is raised.
    See also :func:`write_index_file`.
    '''
    band = dataset.GetRasterBand(1) # type: gdal.Band
    dtype = band.DataType
    if dtype in DTYPE_INT:
        no_data_value = band.GetNoDataValue() # type: Optional[float]
        scale_factor = band.GetScale()
        inv_scale_factor = None
        if band.GetOffset() != 0:
            raise NotImplementedError('Integer data with offset not supported')
    elif dtype in DTYPE_FLOAT:
        if is_categorical:
            raise ValueError('Categorical data must have integer-type data but is float')
        assert band.GetOffset() == 0
        assert band.GetScale() == 1
        # WPS binary doesn't support floating point data.
        # Floating point data must be converted to integers by scaling and rounding.
        inv_scale_factor, min_max = compute_inv_scale_factor(read_blocks(band))
        scale_factor = 1/inv_scale_factor
        min_, max_ = min_max
        min_scaled = round(min_ * inv_scale_factor)
        max_scaled = round(max_ * inv_scale_factor)
        dtype = get_optimal_dtype(min_scaled, max_scaled)
        if band.GetNoDataValue() is None:
            no_data_value = None
        else:
            # TODO may fail if value range equals dtype range
            #      adjusting the scaling factor slightly to make room for a no-data value may help
            no_data_value = get_no_data_value(dtype, min_scaled, max_scaled)

        #print('Scale factor: {}'.format(scale_factor))
        #print('Min/max: {}'.format(min_max))
        #print('Min/max scaled: {}'.format((min_scaled, max_scaled)))
        #print('No data: {}'.format(no_data_value))
    else:
        assert False, "Unsupported data type: {}".format(gdal.GetDataTypeName(dtype))

    signed = gdal_dtype_is_signed(dtype)
    wordsize = gdal.GetDataTypeSize(dtype) // 8

    wkt = dataset.GetProjection()
    srs = osr.SpatialReference(wkt)

    truelat1 = truelat2 = stand_lon = None

    geotransform = dataset.GetGeoTransform()
    dx = geotransform[1]
    dy = geotransform[5]
    assert dx > 0
    # dy can be negative, see below

    projection = None
    datum_mismatch = None

    if srs.IsGeographic():
        if srs.EPSGTreatsAsLatLong():
            raise ValueError("Unsupported axis order: Lat/Lon, must be Lon/Lat")

        if not CRS.is_wrf_sphere_datum(srs):
            datum_mismatch = DatumMismatch(expected='WRF Sphere (6370km)', actual='a={}m b={}m'.format(srs.GetSemiMajor(), srs.GetSemiMinor()))
        if datum_mismatch and strict_datum:
            raise ValueError(
                "Unsupported datum, must be based on a sphere with " +
                "radius {}m, but is an ellipsoid with a={}m b={}m".format(WRF_EARTH_RADIUS, srs.GetSemiMajor(), srs.GetSemiMinor()))

        projection = 'regular_ll'

    elif srs.IsProjected():
        proj = srs.GetAttrValue('projection')
        datum = srs.GetAttrValue('datum')

        if proj in ['Albers_Conic_Equal_Area', 'Lambert_Conformal_Conic_2SP', 'Mercator_2SP']:
            truelat1 = srs.GetNormProjParm('standard_parallel_1')

        if proj == 'Polar_Stereographic':
            truelat1 = srs.GetNormProjParm('latitude_of_origin')

        if proj in ['Albers_Conic_Equal_Area', 'Lambert_Conformal_Conic_2SP']:
            truelat2 = srs.GetNormProjParm('standard_parallel_2')

        if proj == 'Albers_Conic_Equal_Area':
            stand_lon = srs.GetNormProjParm('longitude_of_center')

        if proj in ['Lambert_Conformal_Conic_2SP', 'Mercator_2SP', 'Polar_Stereographic']:
            stand_lon = srs.GetNormProjParm('central_meridian')

        if proj == "Albers_Conic_Equal_Area":
            if datum != "North_American_Datum_1983":
                datum_mismatch = DatumMismatch(expected='NAD83', actual=datum)
            projection = 'albers_nad83'

        elif proj == "Lambert_Conformal_Conic_2SP":
            if not CRS.is_wrf_sphere_datum(srs):
                datum_mismatch = DatumMismatch(expected='WRF Sphere (6370km)', actual=datum)
            projection = 'lambert'

        elif proj == "Mercator_2SP":
            if not CRS.is_wrf_sphere_datum(srs):
                datum_mismatch = DatumMismatch(expected='WRF Sphere (6370km)', actual=datum)
            projection = 'mercator'

        # For polar stereographic we don't allow datum mismatch in non-strict mode
        # as it would be ambiguous which WPS projection ID to choose.
        elif proj == "Polar_Stereographic" and datum == 'WGS_1984':
            projection = 'polar_wgs84'

        elif proj == "Polar_Stereographic" and CRS.is_wrf_sphere_datum(srs):
            projection = 'polar'

        if projection is None or (datum_mismatch and strict_datum):
            raise ValueError("Unsupported projection/datum: {}; {}".format(proj, datum))
    else:
        raise ValueError("Unsupported SRS type, must be geographic or projected")

    if units is None and is_categorical:
        units = 'category'

    # gdal always uses system byte order when creating ENVI files
    is_little_endian = sys.byteorder == 'little'

    # WPS does not support the concept of negative dy and requires that
    # the highest y coordinate corresponds to the highest y index.
    # If row_order=top_bottom (which we use), then the highest y index corresponds to
    # the row that is stored first in the file.
    # If row_order=bottom_top, then the highest y index corresponds to
    # the row that is stored last in the file.
    # Index coordinates in WPS do not start from 0 but from 1 where (1,1)
    # corresponds to the center of the cell. GDAL (0,0) corresponds to the corner of the cell.
    # See also http://www2.mmm.ucar.edu/wrf/users/FAQ_files/FAQ_wps_intermediate_format.html.

    half_cell = 0.5

    # WPS index coordinates
    known_x = known_y = 1.0

    # GDAL index coordinates
    x_idx = known_x - half_cell
    if dy < 0:
        y_idx = ysize_pad - known_y + half_cell
    else:
        y_idx = known_y - half_cell

    known_lonlat = CRS(srs=srs).to_lonlat(get_crs_coordinates(dataset, x_idx, y_idx))

    metadata = {
        'type': 'categorical' if is_categorical else 'continuous',
        'endian': 'little' if is_little_endian else 'big',
        'signed': 'yes' if signed else 'no',
        'wordsize': wordsize,
        'row_order': 'top_bottom',
        'projection': projection,
        'dx': dx,
        'dy': abs(dy),
        'known_x': known_x,
        'known_y': known_y,
        'known_lat': known_lonlat.lat,
        'known_lon': known_lonlat.lon,
        'tile_x': tilesize_x,
        'tile_y': tilesize_y,
        'tile_z': 1,
        'tile_bdr': tile_bdr
    }

    if filename_digits > 5:
        metadata['filename_digits'] = filename_digits

    if scale_factor != 1:
        metadata['scale_factor'] = scale_factor

    if no_data_value is not None:
        metadata['missing_value'] = float(no_data_value)

    if is_categorical:
        # Note that ComputeRasterMinMax ignores pixels with no-data value.
        band_min, band_max = band.ComputeRasterMinMax()
        assert band_min == int(band_min)
        assert band_max == int(band_max)
        metadata['category_min'] = int(band_min)
        metadata['category_max'] = int(band_max)

    if truelat1 is not None:
        metadata['truelat1'] = truelat1

    if truelat2 is not None:
        metadata['truelat2'] = truelat2

    if stand_lon is not None:
        metadata['stdlon'] = stand_lon

    if units is not None:
        metadata['units'] = units

    if description is not None:
        metadata['description'] = description

    return metadata, datum_mismatch, inv_scale_factor, dtype, no_data_value

BandData = Union[Iterable[np.array],Iterable[ma.masked_array]]


def read_blocks(band: gdal.Band) -> BandData:
    # Reading the 'natural' blocks of the dataset is faster and should
    # help with not consuming too much memory, compared to
    # reading the whole band at once or reading parts not aligned to the blocks.
    dtype = gdal_array.GDALTypeCodeToNumericTypeCode(band.DataType)
    no_data = band.GetNoDataValue() # type: Union[float,None]
    block_size_x, block_size_y = band.GetBlockSize()
    # See GDALRasterBand::ReadBlock documentation.
    block_count_x = (band.XSize + block_size_x - 1) // block_size_x
    block_count_y = (band.YSize + block_size_y - 1) // block_size_y
    for y in range(block_count_y):
        for x in range(block_count_x):
            block = band.ReadBlock(x, y)
            data = np.frombuffer(block, dtype).reshape(block_size_y, block_size_x)
            w, h = band.GetActualBlockSize(x, y)
            data = data[:h,:w]
            if no_data is not None:
                data = ma.masked_equal(data, no_data)
            yield data

def order_of_magnitude(x):
    if x == 0:
        return 0
    return math.floor(math.log10(x))

def compute_inv_scale_factor(blocks: BandData) -> Tuple[int,Tuple[float,float]]:
    ''' Compute optimal (inverse) scale factor by estimating significant digits. '''

    # The maximum inverse scale factor across all data blocks.
    max_inv_scale_factor = 10000000000

    # After the first significant digit, how many extra digits at maximum should be preserved.
    # E.g. 0.039859812 would become 0.0398598, whereas 0.950000000001 would become 0.95.
    extra_precision = 1e-5

    # Maximum total decimals that can be preserved.
    # This also sets an upper limit to the possible inverse scale factor.
    # E.g. 0.0000000273926 will stop at factor 1e10 and hence become 0.0000000274.
    max_precision = 1/max_inv_scale_factor

    # The current maximum inverse scale factor across all data blocks. Default is minimum.
    inv_scale_factor = 1

    # Current maximum magnitude of the block data. Default is minimum.
    mag_max = -order_of_magnitude(max_inv_scale_factor)

    # Min/max values over all data blocks.
    all_min = math.inf
    all_max = -math.inf

    for data in blocks:
        min_ = np.min(data)
        if ma.is_masked(min_):
            # Ignore blocks where all values are masked.
            continue
        max_ = np.max(data)
        all_min = min(all_min, min_)
        all_max = max(all_max, max_)
        mag = order_of_magnitude(max(abs(min_), abs(max_)))
        if mag > mag_max:
            mag_max = mag
            inv_scale_factor = 1
        target_precision = max(pow(10, mag_max) * extra_precision, max_precision)
        # Initial factor. If the data is all integer, then this factor will be returned.
        block_inv_scale_factor = 1
        while True:
            max_diff = np.max(np.abs(data - np.round(data, order_of_magnitude(block_inv_scale_factor))))
            if max_diff > target_precision:
                block_inv_scale_factor *= 10
            else:
                break
        inv_scale_factor = max(inv_scale_factor, block_inv_scale_factor)
    return inv_scale_factor, (all_min, all_max)


def write_index_file(path: str, metadata: dict) -> None:
    content = ''
    for key in sorted(metadata):
        val = metadata[key]
        if key in INDEX_FIELDS_QUOTED:
            val = '"{}"'.format(val)
        content += '{} = {}\n'.format(key, val)

    with open(path, 'w') as f:
        f.write(content)


def get_crs_coordinates(dataset: gdal.Dataset, x_idx: float, y_idx: float) -> Coordinate2D:
    geotransform = dataset.GetGeoTransform()
    origin_x = geotransform[0]  # origin_x/y is the CRS coordinate at the top left corner of the (0,0) pixel
    origin_y = geotransform[3]
    dx = geotransform[1]
    dy = geotransform[5]
    x = x_idx * dx + origin_x
    y = y_idx * dy + origin_y
    return Coordinate2D(x=x, y=y)

def get_center_crs_coordinates(dataset: gdal.Dataset) -> Coordinate2D:
    return get_crs_coordinates(dataset, dataset.RasterXSize/2, dataset.RasterYSize/2)
