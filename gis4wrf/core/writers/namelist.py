# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List
import os

import f90nml

from gis4wrf.core.util import export
from gis4wrf.core.readers.namelist import read_namelist


@export
def write_namelist(namelist: dict, path: str) -> None:
    nml = f90nml.Namelist(namelist)
    nml.indent = 0
    nml.write(path, force=True)


def patch_namelist(path: str, patch: dict, delete_vars: List[str]=[]) -> None:
    nml = read_namelist(path)
    for group_name, group_patch in patch.items():
        if group_name not in nml:
            nml[group_name] = group_patch
            continue
        for var_name, val in group_patch.items():
            nml[group_name][var_name] = val
        for var_name in delete_vars:
            try:
                del nml[group_name][var_name]
            except KeyError:
                pass
    nml.indent = 0
    nml.write(path, force=True)

# The following alternative patch_namelist implemention uses the f90nml.patch function
# which preserves formatting and comments of the input namelist.
# Due to a bug we can't use it currently, see https://github.com/marshallward/f90nml/issues/80
def _patch_namelist(path: str, patch: dict, delete_vars: List[str]=None) -> None:
    ''' Patch an existing namelist file, retaining any formatting and comments. '''
    # f90nml does not create a patch file if the patch is empty
    if not patch:
        return
    assert os.path.exists(path), path
    patch_path = path + '.tmp'
    # TODO set indentation to 0 (patch APIs don't support it currently, see https://github.com/marshallward/f90nml/issues/79)
    f90nml.patch(path, patch, patch_path)
    assert os.path.exists(patch_path), patch_path
    if delete_vars:
        # work-around until f90nml.patch supports deletion, see https://github.com/marshallward/f90nml/issues/77
        with open(patch_path, 'r') as fp:
            lines = fp.readlines()
        with open(patch_path, 'w') as fp:
            for line in lines:
                if any(var_name in line for var_name in delete_vars):
                    continue
                fp.write(line)
    os.remove(path)
    os.rename(patch_path, path)

