# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from gis4wrf.core.project import (
    get_bbox_from_grid_spec, get_parent_bbox_from_child_grid_spec,
    get_bbox_center, Project
)
from gis4wrf.core import BoundingBox2D

def test_innermost_domain_bbox():
    bbox = get_bbox_from_grid_spec(center_x=10, center_y=5, cell_size=(0.1, 0.1), cols=10, rows=5)
    assert bbox.minx == 9.5
    assert bbox.maxx == 10.5
    assert bbox.miny == 4.75
    assert bbox.maxy == 5.25

def test_parent_domain_bbox_from_child():
    bbox = get_parent_bbox_from_child_grid_spec(
        child_center_x=10, child_center_y=5, child_cell_size=(0.1, 0.1), child_cols=10, child_rows=5,
        child_parent_res_ratio=2, parent_left_padding=1, parent_right_padding=2, parent_bottom_padding=3,
        parent_top_padding=4)
    assert bbox.minx == 9.3
    assert bbox.maxx == 10.9
    assert bbox.miny == 4.15
    assert bbox.maxy == 6.05

def test_bbox_center():
    center_x, center_y = get_bbox_center(BoundingBox2D(minx=9.5, maxx=10.5, miny=4.75, maxy=5.25))
    assert center_x == 10
    assert center_y == 5

def test_bboxes_multiple_domains():
    project = Project({
        'version': 1,
        'domains': [{
            "map_proj": "lat-lon",
            "center_lonlat" : [2, 4],
            "domain_size": [4, 8],
            'cell_size': [2, 2]
        }, {
            'padding_left': 2,
            'padding_right': 2,
            'padding_top': 2,
            'padding_bottom': 2,
            'parent_cell_size_ratio': 2
        }, {
            'padding_left': 2,
            'padding_right': 2,
            'padding_top': 2,
            'padding_bottom': 2,
            'parent_cell_size_ratio': 2
        }]
    })

    project.fill_domains()
    bboxes = project.bboxes
    domains = project.data['domains']

    assert bboxes[0] == BoundingBox2D(minx=-2, miny=-4, maxx=6, maxy=12)
    assert domains[0]['cell_size'] == [2, 2]
    assert domains[0]['domain_size'] == [4, 8]

    assert bboxes[1] == BoundingBox2D(minx=-10, miny=-12, maxx=14, maxy=20)
    assert domains[1]['cell_size'] == [4, 4]
    assert domains[1]['domain_size'] == [2, 4]

    assert bboxes[2] == BoundingBox2D(minx=-26, miny=-28, maxx=30, maxy=36)
    assert domains[2]['cell_size'] == [8, 8]
    assert domains[2]['domain_size'] == [3, 4]
