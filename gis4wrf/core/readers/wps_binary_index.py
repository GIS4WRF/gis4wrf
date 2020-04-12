# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Mapping, Tuple, Set, List, Optional
import os
from configparser import ConfigParser

from gis4wrf.core.util import export
from gis4wrf.core.errors import UserError, UnsupportedError
from gis4wrf.core.crs import LonLat, Coordinate2D
from gis4wrf.core.readers.categories import LANDUSE, LANDUSE_FIELDS

class WPSBinaryIndexMetadata(object):
    # encoding
    little_endian: bool
    signed: bool
    top_bottom: bool
    word_size: int
    scale_factor: float
    missing_value: Optional[float]
    # tile dimensions
    tile_x: int
    tile_y: int
    tile_z_start: int
    tile_z_end: int
    tile_bdr: int # for x and y only
    # projection / geographic coordinate system
    proj_id: str
    stdlon: Optional[float]
    truelat1: Optional[float]
    truelat2: Optional[float]
    # grid georeferencing
    dx: float
    dy: float
    known_lonlat: LonLat
    known_idx: Coordinate2D
    # categories
    categorical: bool
    category_min: Optional[int]
    category_max: Optional[int]
    # landuse categories
    landuse_scheme: Optional[str]
    iswater: Optional[int]
    islake: Optional[int]
    isice: Optional[int]
    isurban: Optional[int]
    # other
    filename_digits: int
    units: Optional[str]
    description: Optional[str]
    
    @property
    def landuse_scheme_or_default(self) -> str:
        if self.landuse_scheme is None:
            return 'USGS'
        else:
            return self.landuse_scheme

    @property
    def is_landuse(self) -> bool:
        fields = [self.iswater, self.islake, self.isice, self.isurban]
        return self.landuse_scheme or any(field is not None for field in fields)

    @property
    def categories(self) -> Mapping[int,Tuple[str,str]]:
        assert self.categorical
        categories = {}
        if self.is_landuse:
            categories.update(LANDUSE.get(self.landuse_scheme_or_default, {}))

            for field, (label, color) in LANDUSE_FIELDS.items():
                val = getattr(self, field)
                if val is None:
                    continue
                if not self.category_min <= val <= self.category_max:
                    continue
                if val in categories:
                    continue
                categories[val] = (label, color)
        return categories

    @property
    def landmask_water(self) -> List[int]:
        assert self.is_landuse
        water = set() # type: Set[int]

        fields = [self.iswater, self.islake]
        for val in fields:
            if val is not None:
                water.add(val)

        scheme = self.landuse_scheme_or_default
        if scheme == 'USGS':
            water.add(16)
        elif scheme == 'MODIFIED_IGBP_MODIS_NOAH':
            water.add(17)
        else:
            raise UnsupportedError(f'Land use scheme {scheme} is not supported')

        return sorted(water)

    def validate(self) -> None:
        if self.categorical:
            assert self.category_min is not None
            assert self.category_max is not None

@export
def read_wps_binary_index_file(folder: str) -> WPSBinaryIndexMetadata:
    index_path = os.path.join(folder, 'index')
    if not os.path.exists(index_path):
        raise UserError(f'{index_path} is missing, this is not a valid WPS Binary dataset')
    with open(index_path) as f:
        index = '\n'.join(line.strip() for line in f.readlines())
    parser = ConfigParser(interpolation=None)
    parser.read_string('[root]\n' + index)
    meta = parser['root']

    def clean_str(s: Optional[str]) -> Optional[str]:
        if s is None:
            return
        else:
            return s.strip('"')

    m = WPSBinaryIndexMetadata()

    # encoding
    m.little_endian = meta.get('endian') == 'little'
    m.signed = meta.get('signed') == 'yes'
    m.top_bottom = meta.get('row_order') == 'top_bottom'
    m.word_size = int(meta['wordsize'])
    m.scale_factor = float(meta.get('scale_factor', '1'))
    m.missing_value = float(meta['missing_value']) if 'missing_value' in meta else None

    # tile dimensions
    m.tile_x = int(meta['tile_x'])
    m.tile_y = int(meta['tile_y'])
    if 'tile_z_start' in meta:
        m.tile_z_start = int(meta['tile_z_start'])
        m.tile_z_end = int(meta['tile_z_end'])
    else:
        m.tile_z_start = 1
        m.tile_z_end = int(meta['tile_z'])
    m.tile_bdr = int(meta.get('tile_bdr', '0'))

    # projection / geographic coordinate system
    m.proj_id = meta['projection']
    m.stdlon = float(meta['stdlon']) if 'stdlon' in meta else None
    m.truelat1 = float(meta['truelat1']) if 'truelat1' in meta else None
    m.truelat2 = float(meta['truelat2']) if 'truelat2' in meta else None

    # grid georeferencing
    m.dx = float(meta['dx'])
    m.dy = float(meta['dy'])
    m.known_lonlat = LonLat(lon=float(meta['known_lon']), lat=float(meta['known_lat']))
    known_x_idx = float(meta.get('known_x', '1'))
    known_y_idx = float(meta.get('known_y', '1'))
    m.known_idx = Coordinate2D(known_x_idx, known_y_idx)

    # categories
    m.categorical = meta['type'] == 'categorical'
    m.category_min = int(meta['category_min']) if 'category_min' in meta else None
    m.category_max = int(meta['category_max']) if 'category_max' in meta else None

    # landuse categories
    m.landuse_scheme = clean_str(meta.get('mminlu'))
    for field in LANDUSE_FIELDS:
        setattr(m, field, int(meta[field]) if field in meta else None)

    # other
    m.filename_digits = int(meta.get('filename_digits', '5'))
    m.units = clean_str(meta.get('units'))
    m.description = clean_str(meta.get('description'))

    m.validate()

    return m

