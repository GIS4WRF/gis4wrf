# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Dict, Any, Union, Optional
import os
from io import StringIO
import re
import json

import f90nml

from gis4wrf.core.util import export
from gis4wrf.core.errors import UserError

SCHEMA_DIR = os.path.join(os.path.dirname(__file__),  'nml_schemas')

SCHEMA_VAR_TYPES = {
    'str': str,
    'int': int,
    'real': float,
    'bool': bool,
    'list': list
}

SCHEMA_CACHE = {} # type: Dict[str,Any]

@export
def read_namelist(path: Union[str, StringIO], schema_name: Optional[str]=None) -> dict:
    if isinstance(path, str) and not os.path.exists(path):
        raise UserError(f'Namelist file {path} does not exist')
    try:
        nml = f90nml.read(path)
    except:
        # f90nml does not raise useful exceptions, so we can't include details here
        raise UserError(f'Namelist file {path} could not be parsed')
    
    # If a schema is specified, use it to fix single-element lists which are parsed as
    # primitive value since there is nothing to distinguish them from each other in the namelist format.
    if schema_name:
        schema = get_namelist_schema(schema_name)
        for group_name, group in nml.items():
            schema_group = schema[group_name]
            for var_name, var_val in group.items():
                schema_var = schema_group[var_name]
                schema_type = SCHEMA_VAR_TYPES[schema_var['type']]
                if schema_type is list and not isinstance(var_val, list):
                    group[var_name] = [var_val]
    return nml

@export
def get_namelist_schema(name: str) -> dict:
    if name not in SCHEMA_CACHE:
        schema_path = os.path.join(SCHEMA_DIR, name + '.json')
        with open(schema_path, encoding='utf-8') as f:
            schema = json.load(f)
        # Enforce lower-case keys to ease processing.
        # Note that Fortran is case-insensitive.
        schema = {
            group_name.lower(): {
                var_name.lower(): var_val
                for var_name, var_val in group.items()
            }
            for group_name, group in schema.items()
        }
        SCHEMA_CACHE[name] = schema
    return SCHEMA_CACHE[name]

def is_compatible_type(val, schema_type):
    if schema_type is float:
        types = (int, float)
    else:
        types = schema_type
    return isinstance(val, types)

def verify_namelist_var(var_name: str, var_val: Union[str,int,float,bool,list],
                        schema_var: dict) -> None:
    schema_type = SCHEMA_VAR_TYPES[schema_var['type']]
    if schema_type is list:
        # A single-item list always gets parsed as primitive value since there is nothing
        # to distinguish them from each other in the namelist format.
        if not isinstance(var_val, list):
            var_val = [var_val]
    if not is_compatible_type(var_val, schema_type):
        raise TypeError('Variable "{}" must be of type "{}" but is "{}"'.format(
            var_name, schema_type.__name__, type(var_val).__name__))
    options = schema_var.get('options')
    if not isinstance(var_val, list):
        if isinstance(options, dict):
            options = list(map(schema_type, options.keys()))
        if options and var_val not in options:
            raise ValueError('Variable "{}" has the value "{}" but must be one of {}'.format(
                var_name, var_val, options))
    else:
        item_type = SCHEMA_VAR_TYPES[schema_var['itemtype']]
        if isinstance(options, dict):
            options = list(map(item_type, options.keys()))
        # Currently, min/max/regex is only used for list variables in the schema.
        val_min = schema_var.get('min') # type: Optional[int]
        val_max = schema_var.get('max') # type: Optional[int]
        val_regex = schema_var.get('regex') # type: Optional[str]
        for list_val in var_val:
            if not is_compatible_type(list_val, item_type):
                raise TypeError('Variable "{}" must only have items of type "{}" but contains "{}"'.format(
                    var_name, item_type.__name__, type(list_val).__name__))
            if options and list_val not in options:
                raise ValueError('Variable "{}" has an item with value "{}" but must be one of {}'.format(
                    var_name, list_val, options))
            if val_min is not None:
                assert isinstance(list_val, (int, float))
                if list_val < val_min:
                    raise ValueError('Variable "{}" must only have values >= {} but contains {}'.format(
                        var_name, val_min, list_val))
            if val_max is not None:
                assert isinstance(list_val, (int, float))
                if list_val > val_max:
                    raise ValueError('Variable "{}" must only have values <= {} but contains {}'.format(
                        var_name, val_max, list_val))
            if val_regex:
                assert isinstance(list_val, str)
                if not re.fullmatch(val_regex, list_val):
                    raise ValueError('Variable "{}" must only have values matching {} but contains {}'.format(
                        var_name, val_regex, list_val))

@export
def verify_namelist(namelist: dict, schema_or_name: Union[dict,str]) -> None:
    # TODO collect and return all validation errors
    if isinstance(schema_or_name, str):
        schema = get_namelist_schema(schema_or_name)
    else:
        schema = schema_or_name
    if not isinstance(namelist, dict):
        raise TypeError('namelist object must be a dictionary')
    for group_name, group in namelist.items():
        if not isinstance(group, dict):
            raise TypeError('namelist group "{}" must be a dictionary'.format(group_name))
        if group_name not in schema:
            raise ValueError('"{}" is an unknown group name'.format(group_name))
        schema_group = schema[group_name]
        for var_name, var_val in group.items():
            if var_name not in schema_group:
                raise ValueError('"{}" is an unknown variable name in group "{}"'.format(var_name, group_name))
            schema_var = schema_group[var_name]
            verify_namelist_var(var_name, var_val, schema_var)
