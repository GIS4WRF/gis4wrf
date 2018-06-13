# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

import os
import numpy as np
import gis4wrf.core
from gis4wrf.core.writers.wps_binary import compute_inv_scale_factor


def test_compute_scale_factor():
    def factor(blocks):
        return compute_inv_scale_factor(blocks)[0]

    for s in [1, -1]: # sign
        data = np.array([s*0.002])
        inv = factor([data])
        assert inv == 1000

        data = np.array([s*0.0027392])
        inv = factor([data])
        assert inv == 1e7

        data = np.array([s*0.002739267585799789879876])
        inv = factor([data])
        assert inv == 1e8

        data = np.array([s*0.0000000273926])
        inv = factor([data])
        assert inv == 1e10 # max

        data = np.array([s*1002.1])
        inv = factor([data])
        assert inv == 10

        data = np.array([s*1002.100000078])
        inv = factor([data])
        assert inv == 10

        data = np.array([s*1002.0000000045])
        inv = factor([data])
        assert inv == 1

        data = np.array([s*123456789012.5])
        inv = factor([data])
        assert inv == 1

        data = np.array([s*12300.0])
        inv = factor([data])
        # min inverse factor is 1, even though 0.01 would be better here
        assert inv == 1

    data = np.array([0.002, -0.002])
    inv = factor([data])
    assert inv == 1000

    data = np.array([10000.2, 0.002])
    inv = factor([data])
    assert inv == 10

    data = [np.array([10000.2]), np.array([0.002])]
    inv = factor(data)
    assert inv == 10

    data = [np.array([0.002]), np.array([10000.2])]
    inv = factor(data)
    assert inv == 10

    data = [np.array([0.5]), np.array([0.9]), np.array([0.95])]
    inv = factor(data)
    assert inv == 100

def test_convert_to_wps_binary(landcover_dataset_path, tmpdir):
    result = gis4wrf.core.convert_to_wps_binary(landcover_dataset_path, output_folder=str(tmpdir), is_categorical=True)
    # TODO test that conversion is correct
    assert os.path.exists(result.index_path)
