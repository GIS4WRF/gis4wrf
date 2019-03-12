# Development notes

- [Overview](#overview)
  - [Package structure](#package-structure)
  - [External packages](#external-packages)
    - [A note on GDAL](#a-note-on-gdal)
  - [Useful websites](#useful-websites)
  - [License header](#license-header)
- [Development](#qgis-version)
  - [QGIS Version](#qgis-version)
  - [Local setup (Windows)](#local-setup-windows)
    - [Unit testing](#unit-testing)
    - [Visual Studio Code](#visual-studio-code)
  - [Local setup (macOS)](#local-setup-macos)
- [Release](#release)
  - [ZIP packaging](#zip-packaging)
  - [Prepare a new release](#prepare-a-new-release)

# Overview

## Package structure

- `gis4wrf.core` contains all non-QGIS-dependent code
- `gis4wrf.qgis` is the QGIS plugin and uses `gis4wrf.core`

## External packages

gis4wrf uses several external Python packages to read, write, and visualize data.
Some are available with every QGIS installation, like GDAL, while others are installed
separately, like wrf-python and netCDF4. See `gis4wrf/bootstrap.py` for more details
on handling external packages.

### A note on GDAL

QGIS comes with GDAL's Python bindings which are very close to its C interface and hard to use.
Ideally we'd like to use the [rasterio](https://mapbox.github.io/rasterio) library
which is a more pythonic wrapper for GDAL, however this library [cannot be used](https://rasterio.readthedocs.io/en/latest/topics/switch.html#mutual-incompatibilities) together with
GDAL's Python bindings in the same program, here QGIS. 

## Useful websites

- [Python GDAL/OGR Cookbook](https://pcjericks.github.io/py-gdalogr-cookbook/)

## License header

The following header shall be appended at the top of every source file.

```
# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.
```

# Development

## QGIS Version

GIS4WRF requires the latest version of QGIS 3 which can be found at https://qgis.org/en/site/forusers/download.html.

## Local setup (Windows)

Some files have to be generated. Run the following from the repository root to (re-)generate the PyQT resources file:

```
> "C:\Program Files\QGIS <VERSION_NUMBER>\bin\python-qgis.bat" build.py
```

For fast iteration, the following two steps are recommended:

1. Install the [QGIS Plugin Reloader](https://plugins.qgis.org/plugins/plugin_reloader/) plugin.
   For QGIS 3, this plugin is experimental. You need to enable the `Show also experimental plugins` checkbox in `Settings` in the plugin manager.

2. Symlink the `gis4wrf` subfolder of the git repository into the QGIS plugins folder to avoid having to work directly in the latter or having to constantly copy folders around. The symlink is automatically created when running `build.py` above.

To be able to run unit tests and enable refactoring support and type-based linting in IDEs like Visual Studio Code, start an administrator command prompt and run:

```
> "C:\Program Files\QGIS <VERSION_NUMBER>\bin\python-qgis.bat" -m pip install pytest mypy rope
```

### Unit testing

Tests are written and run using [pytest](https://docs.pytest.org/en/latest/) and are located in the `tests/` folder.

To run tests, navigate to the root folder and run:
```
> "C:\Program Files\QGIS <VERSION_NUMBER>\bin\python-qgis.bat" -m pytest -v -s
```

### Visual Studio Code

If you use VS Code, add the following to the workspace configuration to enable linting and (some) auto-completion:

```json
{
    "python.pythonPath": "C:\\Program Files\\QGIS <VERSION_NUMBER>\\bin\\python-qgis.bat",
    "python.linting.mypyEnabled": true
}
```

You may have to restart VS Code after that.

## Local setup (macOS)

Install the latest version of QGIS 3 using [these](https://gis4wrf.github.io/installation/#macos) instructions.

QGIS 3 on macOS uses Python installed in `/usr/local`. Python packages can be installed using pip by invoking the Python 3 interpreter on the system: `python3 -m pip install 'package-name'`.


# Release

## ZIP packaging

To create the plugin archive simply run `python build.py`.

## Prepare a new release

Before creating a new release, make sure to complete the following checklist:

```
- [ ] Create a new issue named `Prepare for GIS4WRF <VERSION_NUMBER> release`, copy and paste this check-list, and tick what is appropriate.
- [ ] Create a milestone for the version to release if not done already.
- [ ] Check that all issues and PRs targeting the new release have been addded to the milestone.
- [ ] Check that the [documentation](https://gis4wrf.github.io/) repository is up to date.
- [ ] Check that the [README](https://github.com/GIS4WRF/gis4wrf/blob/master/README.md) file is up-to-date.
- [ ] Add and reference issues and PRs mentioned in the milestone to [`CHANGELOG.txt`](https://github.com/GIS4WRF/gis4wrf/blob/master/CHANGELOG.txt).
- [ ] Bump the version in the [metadata.txt](https://github.com/GIS4WRF/gis4wrf/blob/master/gis4wrf/metadata.txt) file.
- [ ] Check that all issues and PRs for the version number to release have been closed.
- [ ] [Create the zip package](https://github.com/GIS4WRF/gis4wrf/blob/master/DEVELOP.md#zip-packaging).
- [ ] Upload the zip package to the [QGIS Python Plugins Repository](https://plugins.qgis.org).
- [ ] Tag a new release.
- [ ] Close the issue named `Prepare for GIS4WRF <VERSION_NUMBER> release`.
```