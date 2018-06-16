# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Tuple, List, Optional
import os
import glob
import shutil
import json
from json import JSONEncoder
from math import ceil
from datetime import datetime
import string
import itertools

from gis4wrf.core.util import export, gdal, get_temp_vsi_path, link_or_copy, ogr, read_vsi_string
from gis4wrf.core.constants import PROJECT_JSON_VERSION
from gis4wrf.core.crs import CRS, LonLat, BoundingBox2D, Coordinate2D
from gis4wrf.core.readers.geogrid_tbl import read_geogrid_tbl, GeogridTbl
from gis4wrf.core.writers.geogrid_tbl import write_geogrid_tbl
from gis4wrf.core.writers.namelist import patch_namelist, write_namelist
from gis4wrf.core.downloaders.datasets import met_datasets_vtables

PROJECT_FILENAME = 'project.json'

class ProjectJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, BoundingBox2D):
            return [o.minx, o.miny, o.maxx, o.maxy]
        JSONEncoder.default(self, o)

def ProjectJSONDecoder(json_obj):
    if 'bbox' in json_obj:
        bbox = json_obj['bbox']
        json_obj['bbox'] = BoundingBox2D(minx=bbox[0], miny=bbox[1], maxx=bbox[2], maxy=bbox[3])
    return json_obj

@export
class Project(object):
    def __init__(self, data: dict, path: Optional[str]=None) -> None:
        self.data = data
        self.path = path

    @staticmethod
    def create(path: Optional[str]=None):
        data = {
            "version": PROJECT_JSON_VERSION
        }
        return Project(data, path)

    @staticmethod
    def load(path: str):
        with open(os.path.join(path, PROJECT_FILENAME)) as fp:
            data = json.load(fp, object_hook=ProjectJSONDecoder)
        if data['version'] < PROJECT_JSON_VERSION:
            # upgrade to new version
            pass
        elif data['version'] > PROJECT_JSON_VERSION:
            raise ValueError('Plugin too old to read project file of version {}'.format(data['version']))
        return Project(data, path)

    def save(self) -> None:
        if not self.path:
            return
        with open((os.path.join(self.path, PROJECT_FILENAME)), 'w') as fp:
            json.dump(self.data, fp, indent=4, cls=ProjectJSONEncoder)

    @property
    def run_wps_folder(self):
        return os.path.join(self.path, 'run_wps')

    @property
    def run_wrf_folder(self):
        return os.path.join(self.path, 'run_wrf')

    @property
    def geog_data_path(self):
        return self._geog_data_path
    
    @geog_data_path.setter
    def geog_data_path(self, path: str) -> None:
        self._geog_data_path = path

    @property
    def met_data_path(self):
        return self._met_data_path
    
    @met_data_path.setter
    def met_data_path(self, path: str) -> None:
        self._met_data_path = path

    def init_config_files_if_needed(self, geogrid_tbl_path: str, wrf_namelist_path: str) -> None:
        if not self.path:
            return
        files = [
            (geogrid_tbl_path, self.geogrid_tbl_path),
            (wrf_namelist_path, self.wrf_namelist_path)
        ]
        for src_path, dst_path in files:
            if not os.path.exists(dst_path):
                shutil.copyfile(src_path, dst_path)

    @property
    def wps_namelist_path(self) -> str:
        assert self.path
        return os.path.join(self.path, 'namelist.wps')
    
    @property
    def wrf_namelist_path(self) -> str:
        assert self.path
        return os.path.join(self.path, 'namelist.input')

    @property
    def geogrid_tbl_path(self) -> str:
        assert self.path
        return os.path.join(self.path, 'GEOGRID.TBL')

    def read_geogrid_tbl(self) -> Optional[GeogridTbl]:
        if not self.path:
            return None
        return read_geogrid_tbl(self.geogrid_tbl_path)

    def write_geogrid_tbl(self, tbl: GeogridTbl) -> None:
        write_geogrid_tbl(tbl, self.geogrid_tbl_path)

    @property
    def geo_dataset_specs(self) -> List[str]:
        specs = self.data.get('geo_dataset_specs')
        if specs is None:
            specs = [''] * self.domain_count
        return specs

    @geo_dataset_specs.setter
    def geo_dataset_specs(self, specs: List[str]) -> None:
        assert len(specs) == self.domain_count
        self.data['geo_dataset_specs'] = specs
        self.save()

    @property
    def met_dataset_spec(self) -> dict:
        spec = self.data['met_dataset_spec']
        paths = [os.path.join(self.met_data_path, rel_path) for rel_path in spec['rel_paths']]
        if not os.path.exists(paths[0]):
            # This would happen if a dataset was manually deleted from disk
            # or the project was copied to another machine which doesn't have
            # the dataset yet.
            # TODO use as trigger to offer download of missing data
            paths = None
        return {
            'dataset': spec['dataset'],
            'product': spec['product'],
            'time_range': [datetime.strptime(d, '%Y-%m-%d %H:%M') for d in spec['time_range']],
            'interval_seconds': spec['interval_seconds'],
            'paths': paths
        }

    @met_dataset_spec.setter
    def met_dataset_spec(self, spec: dict) -> None:
        rel_paths = [os.path.relpath(path, self.met_data_path) for path in spec['paths']]
        time_range = [d.strftime('%Y-%m-%d %H:%M') for d in spec['time_range']]
        self.data['met_dataset_spec'] = {
            'dataset': spec['dataset'],
            'product': spec['product'],
            'time_range': time_range,
            'interval_seconds': spec['interval_seconds'],
            'rel_paths': rel_paths
        }
        self.save()

    def set_domains(self, map_proj: str,
                    cell_size: Tuple[float,float], domain_size: Tuple[int,int],
                    center_lonlat: LonLat, truelat1: float=None, truelat2: float=None,
                    parent_domains: List[dict]=[]) -> None:
        self.data['domains'] = [{
            "map_proj": map_proj,
            "center_lonlat" : [center_lonlat.lon, center_lonlat.lat],
            "cell_size": [cell_size[0], cell_size[1]],
            "domain_size": [domain_size[0], domain_size[1]]
        }] + parent_domains

        main_domain = self.data['domains'][0]
        if map_proj == 'lat-lon':
            # hard-coded as we don't support rotation
            main_domain['stand_lon'] = 0.0

        if map_proj in ['lambert', 'mercator', 'polar']:
            main_domain['truelat1'] = truelat1

        if map_proj == 'lambert':
            main_domain['truelat2'] = truelat2

        self.fill_domains()

        self.save()

    @property
    def projection(self) -> CRS:
        domain = self.data['domains'][0]
        map_proj = domain['map_proj']
        if map_proj == 'lambert':
            return CRS.create_lambert(
                domain['truelat1'], domain['truelat2'], LonLat(*domain['center_lonlat']))
        elif map_proj == 'mercator':
            return CRS.create_mercator(
                domain['truelat1'], domain['center_lonlat'][0])
        elif map_proj == 'polar':
            return CRS.create_polar(
                domain['truelat1'], domain['center_lonlat'][0])
        elif map_proj == 'lat-lon':
            return CRS.create_lonlat()
        else:
            raise ValueError('Unknown projection: ' + map_proj)

    @property
    def domain_count(self) -> int:
        return len(self.data.get('domains', [{}]))

    @property
    def bboxes(self) -> List[BoundingBox2D]:
        self.fill_domains()
        return [domain['bbox'] for domain in self.data['domains']]

    def fill_domains(self):
        ''' Updated computed fields in each domain object like cell size. '''
        domains = self.data['domains']

        innermost_domain = domains[0]
        outermost_domain = domains[-1]
        innermost_domain['padding_left'] = 0
        innermost_domain['padding_right'] = 0
        innermost_domain['padding_bottom'] = 0
        innermost_domain['padding_top'] = 0
        outermost_domain['parent_start'] = [1, 1]

        # compute and adjust domain sizes
        for idx, domain in enumerate(domains):
            if idx == 0:
                continue
            child_domain = domains[idx-1]

            # We need to make sure that the number of columns in the child domain is an integer multiple
            # of the nest's parent domain. As we calculate the inner most domain before calculating the outermost one,
            # we need to amend the value for the number of columns or rows for the inner most domain in the case the
            # dividend obtained by dividing the number of inner domain's columns by the user's inner-to-outer resolution ratio
            # in the case where is not an integer value.
            
            child_domain_size_padded = (
                child_domain['domain_size'][0] + child_domain['padding_left'] + child_domain['padding_right'],
                child_domain['domain_size'][1] + child_domain['padding_bottom'] + child_domain['padding_top'],
            )
            if (child_domain_size_padded[0] % domain['parent_cell_size_ratio']) != 0:
                new_cols = int(ceil(child_domain_size_padded[0] / domain['parent_cell_size_ratio']))
                new_child_domain_padded_x = new_cols * domain['parent_cell_size_ratio']
            else:
                new_child_domain_padded_x = child_domain_size_padded[0]

            if (child_domain_size_padded[1] % domain['parent_cell_size_ratio']) != 0:
                new_rows = int(ceil(child_domain_size_padded[1] / domain['parent_cell_size_ratio']))
                new_child_domain_padded_y = new_rows * domain['parent_cell_size_ratio']
            else:
                new_child_domain_padded_y = child_domain_size_padded[1]

            if idx == 1:
                child_domain['domain_size'] = [new_child_domain_padded_x, new_child_domain_padded_y]
            else:
                child_domain['padding_right'] += new_child_domain_padded_x - child_domain_size_padded[0]
                child_domain['padding_top'] += new_child_domain_padded_y - child_domain_size_padded[1]

            assert new_child_domain_padded_x % domain['parent_cell_size_ratio'] == 0
            assert new_child_domain_padded_y % domain['parent_cell_size_ratio'] == 0

            domain['domain_size'] = [
                new_child_domain_padded_x // domain['parent_cell_size_ratio'],
                new_child_domain_padded_y // domain['parent_cell_size_ratio']]

        # compute bounding boxes, cell sizes, center lonlat, parent start
        for idx, domain in enumerate(domains):
            size_x, size_y = domain['domain_size']
            padded_size_x = size_x + domain['padding_left'] + domain['padding_right']
            padded_size_y = size_y + domain['padding_bottom'] + domain['padding_top']
            domain['domain_size_padded'] = [padded_size_x, padded_size_y]

            if idx == 0:
                center_lon, center_lat = domain['center_lonlat']
                center_xy = self.projection.to_xy(LonLat(lon=center_lon, lat=center_lat))

                domain['bbox'] = get_bbox_from_grid_spec(center_xy.x, center_xy.y, domain['cell_size'], size_x, size_y)
            else:
                child_domain = domains[idx-1]

                domain['cell_size'] = [child_domain['cell_size'][0] * domain['parent_cell_size_ratio'],
                                       child_domain['cell_size'][1] * domain['parent_cell_size_ratio']]

                child_center_x, child_center_y = get_bbox_center(child_domain['bbox'])

                domain['bbox'] = get_parent_bbox_from_child_grid_spec(
                    child_center_x=child_center_x, child_center_y=child_center_y,
                    child_cell_size=child_domain['cell_size'],
                    child_cols=child_domain['domain_size'][0] + child_domain['padding_left'] + child_domain['padding_right'],
                    child_rows=child_domain['domain_size'][1] + child_domain['padding_top'] + child_domain['padding_bottom'],
                    child_parent_res_ratio=domain['parent_cell_size_ratio'],
                    parent_left_padding=domain['padding_left'], parent_right_padding=domain['padding_right'],
                    parent_bottom_padding=domain['padding_bottom'], parent_top_padding=domain['padding_top'])
                
                center_x, center_y = get_bbox_center(domain['bbox'])
                center_lonlat = self.projection.to_lonlat(Coordinate2D(x=center_x, y=center_y))
                domain['center_lonlat'] = [center_lonlat.lon, center_lonlat.lat]

            if idx < len(domains) - 1:
                parent_domain = domains[idx + 1]
                domain['parent_start'] = [parent_domain['padding_left'] + 1, 
                                          parent_domain['padding_bottom'] + 1]

    def update_wps_namelist(self):
        # deferred import to resolve circular dependency on Project type
        from gis4wrf.core.transforms.project_to_wps_namelist import convert_project_to_wps_namelist

        self.fill_domains()
        wps = convert_project_to_wps_namelist(self)

        if not os.path.exists(self.wps_namelist_path):
            write_namelist(wps, self.wps_namelist_path)
        else:
            patch_namelist(self.wps_namelist_path, wps)

    def update_wrf_namelist(self):
        from gis4wrf.core.transforms.project_to_wrf_namelist import convert_project_to_wrf_namelist

        self.fill_domains()
        wrf = convert_project_to_wrf_namelist(self)

        # We use the end_* variables instead.
        delete_from_wrf_namelist = ['run_days', 'run_hours', 'run_minutes', 'run_seconds']

        patch_namelist(self.wrf_namelist_path, wrf, delete_from_wrf_namelist)

    # TODO move prepare functions into separate module together with functions for running
    def prepare_wps_run(self, wps_folder: str) -> None:
        # TODO create separate functions that clean outputs from previous runs, selectively for geogrid etc.
        self.update_wps_namelist()
        os.makedirs(self.run_wps_folder, exist_ok=True)
        # We use the default relative folder locations (./geogrid, ./metgrid)
        # to avoid having to hard-code custom folders in the namelist files.
        geogrid_folder = os.path.join(self.run_wps_folder, 'geogrid')
        os.makedirs(geogrid_folder, exist_ok=True)
        shutil.copy(self.geogrid_tbl_path, geogrid_folder)

        metgrid_folder = os.path.join(self.run_wps_folder, 'metgrid')
        os.makedirs(metgrid_folder, exist_ok=True)
        metgrid_tbl_src_path = os.path.join(wps_folder, 'metgrid', 'METGRID.TBL.ARW')
        if not os.path.exists(metgrid_tbl_src_path):
            raise RuntimeError('File missing in WPS distribution: ' + metgrid_tbl_src_path)
        shutil.copy(metgrid_tbl_src_path,
                    os.path.join(metgrid_folder, 'METGRID.TBL'))

        shutil.copy(self.wps_namelist_path, self.run_wps_folder)
        
        try:
            paths = self.met_dataset_spec['paths']
        except KeyError:
            # met data not configured yet
            pass
        else:
            vtable_filename = met_datasets_vtables[self.met_dataset_spec['dataset']]
            shutil.copy(os.path.join(wps_folder, 'ungrib', 'Variable_Tables', vtable_filename),
                        os.path.join(self.run_wps_folder, 'Vtable'))
            
            if paths is None:
                # met data configured but grib files missing
                # TODO notify user that met data is missing
                pass
            else:
                for path in glob.glob(os.path.join(self.run_wps_folder, 'GRIBFILE.*')):
                    os.remove(path)

                for path, ext in zip(paths, generate_gribfile_extensions()):
                    link_path = os.path.join(self.run_wps_folder, 'GRIBFILE.' + ext)
                    link_or_copy(path, link_path)

    def prepare_wrf_run(self, wrf_folder: str) -> None:
        self.update_wrf_namelist()
        os.makedirs(self.run_wrf_folder, exist_ok=True)

        # Remove everything except real.exe output files to ensure
        # that no old files are reused by wrf.exe.
        clean_exclude = ['wrfinput_', 'wrfbdy_']
        for filename in os.listdir(self.run_wrf_folder):
            if any(filename.startswith(exclude) for exclude in clean_exclude):
                continue
            path = os.path.join(self.run_wrf_folder, filename)
            if os.path.isdir(path):
                continue
            os.remove(path)

        static_data_exclude = ['README', 'example', 'namelist.input.', '.exe', '.tar', '.gitignore']

        static_data_dir = os.path.join(wrf_folder, 'test', 'em_real')
        if not os.path.exists(static_data_dir):
            raise RuntimeError('Folder missing in WRF distribution: ' + static_data_dir)
        for filename in os.listdir(static_data_dir):
            if any(pattern in filename for pattern in static_data_exclude):
                continue
            link_path = os.path.join(self.run_wrf_folder, filename)
            link_or_copy(os.path.join(static_data_dir, filename), link_path)

        for path in glob.glob(os.path.join(self.run_wps_folder, 'met_em.*')):
            link_path = os.path.join(self.run_wrf_folder, os.path.basename(path))
            link_or_copy(path, link_path)
        
        shutil.copy(self.wrf_namelist_path, self.run_wrf_folder)

def generate_gribfile_extensions():
    letters = list(string.ascii_uppercase)
    for a, b, c in itertools.product(letters, repeat=3):
        yield a + b + c


def get_bbox_from_grid_spec(center_x: float, center_y: float, cell_size: Tuple[float, float],
                            cols: int, rows: int) -> BoundingBox2D:
    """Returns a tuple of 4 coordinates for the edges of the domain
    given the center point of the domain, grid-cell resolution,
    and the number of domain columns and rows.
    """
    half_width = cell_size[0] * cols / 2
    half_height = cell_size[1] * rows / 2

    return BoundingBox2D(minx=center_x - half_width,
                       maxx=center_x + half_width,
                       miny=center_y - half_height,
                       maxy=center_y + half_height)

def get_parent_bbox_from_child_grid_spec(
    child_center_x: float, child_center_y: float, child_cell_size: Tuple[float,float],
    child_cols: int, child_rows: int, child_parent_res_ratio: int,
    parent_left_padding: int, parent_right_padding: int,
    parent_bottom_padding: int, parent_top_padding: int) -> BoundingBox2D:
    """Returns a tuple of 4 coordinates for the edges of the parent domain."""
    child_bbox = get_bbox_from_grid_spec(child_center_x, child_center_y,
                                         child_cell_size, child_cols, child_rows)

    parent_cell_size_x = child_cell_size[0] * child_parent_res_ratio
    parent_cell_size_y = child_cell_size[1] * child_parent_res_ratio
    parent_min_x = child_bbox.minx - parent_cell_size_x * parent_left_padding
    parent_min_y = child_bbox.miny - parent_cell_size_y * parent_bottom_padding
    parent_max_x = child_bbox.maxx + parent_cell_size_x * parent_right_padding
    parent_max_y = child_bbox.maxy + parent_cell_size_y * parent_top_padding

    return BoundingBox2D(minx=parent_min_x, maxx=parent_max_x, miny=parent_min_y, maxy=parent_max_y)

def get_bbox_center(bbox: BoundingBox2D) -> Tuple[float,float]:
    center_x = (bbox.minx + bbox.maxx) / 2
    center_y = (bbox.miny + bbox.maxy) / 2
    return center_x, center_y


def get_bbox_ogr_polygon(bbox: BoundingBox2D) -> ogr.Geometry:
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(bbox.minx, bbox.miny)
    ring.AddPoint(bbox.maxx, bbox.miny)
    ring.AddPoint(bbox.maxx, bbox.maxy)
    ring.AddPoint(bbox.minx, bbox.maxy)
    ring.AddPoint(bbox.minx, bbox.miny)

    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly

def add_domains_to_ogr_datasource(ds: ogr.DataSource, project: Project) -> None:
    layer = ds.CreateLayer('domains', srs=project.projection.srs, geom_type=ogr.wkbPolygon) # type: ogr.Layer

    bboxes = project.bboxes

    feature_defn = layer.GetLayerDefn()
    for bbox in bboxes:
        geom = get_bbox_ogr_polygon(bbox)
        feature = ogr.Feature(feature_defn)
        feature.SetGeometry(geom)
        layer.CreateFeature(feature)

# TODO move to writers
@export
def write_shapefile_from_domains(path: str, project: Project) -> None:
    drv = ogr.GetDriverByName('ESRI Shapefile') # type: ogr.Driver
    ds = drv.CreateDataSource(path) # type: ogr.DataSource
    add_domains_to_ogr_datasource(ds, project)

# TODO move to transforms
@export
def get_gdal_from_domains(project: Project) -> ogr.DataSource:
    drv = ogr.GetDriverByName('Memory') # type: ogr.Driver
    ds = drv.CreateDataSource('') # type: ogr.DataSource
    add_domains_to_ogr_datasource(ds, project)
    return ds

# TODO move to transforms
@export
def get_gdal_grid_vrt_from_domains(project: Project) -> List[str]:
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
        vrt_ds.SetProjection(project.projection.proj4)
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

def fix_pixelfunction_vrt(vrt: str) -> str:
    ''' Work-around for https://github.com/OSGeo/gdal/issues/501. '''
    import xml.etree.ElementTree as ET
    root = ET.fromstring(vrt)
    bands = root.findall("./VRTRasterBand[@subClass='VRTDerivedRasterBand']")
    for band in bands:
        if band.find('PixelFunctionLanguage') is None:
            lang = ET.SubElement(band, 'PixelFunctionLanguage')
            lang.text = 'Python'
    return ET.tostring(root, encoding='unicode')

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

