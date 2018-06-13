# Development notes

## QGIS Version

GIS4WRF requires QGIS 3 which can found at https://qgis.org/en/site/forusers/download.html.

## Local setup (Windows)

If you use VS Code, add the following to the workspace config to get linting and (some) auto-completion:

```json
{
    "python.pythonPath": "C:\\Program Files\\QGIS 3.0\\bin\\python-qgis.bat"
}
```

For linting, unit testing and pep8 to work, you need to install `pylint`, `pytest`, `autopep8`, `mypy`, `rope` into the QGIS Python installation.
Start an administrator command prompt and run:

```
> "C:\Program Files\QGIS 3.0\bin\python-qgis.bat" -m pip install pylint pytest autopep8 mypy rope
```

If you use VS Code, add the following to the workspace config:

``` json
{
    "python.formatting.autopep8Path":  "C:\\Program Files\\QGIS 3.0\\apps\\Python36\\Scripts\\autopep8.exe"
}
```

If you use VS Code and you prefer to use `mypy`, add the following to the workspace config:

``` json
{
    "python.linting.mypyEnabled": true,
    "python.linting.pylintEnabled": false
}
```

You may have to restart VS Code after that.

Some files have to be generated. Run the following from the repository root to (re-)generate the PyQT resources file:

```
> "C:\Program Files\QGIS 3.0\bin\python-qgis.bat" build.py
```

For fast iteration, the following two steps are recommended:

1. Install the [QGIS Plugin Reloader](https://plugins.qgis.org/plugins/plugin_reloader/) plugin.
   For QGIS 3, this plugin is not available yet in the plugin manager within QGIS,
   so download it manually and point use the "Install from ZIP" option within the plugin manager.

2. Symlink the `gis4wrf` subfolder of the git repository into the QGIS plugins folder to avoid having to work directly in the latter or having to constantly copy folders around. This happens when running `build.py` above.

## Unit testing

Tests are written and run using [pytest](https://docs.pytest.org/en/latest/) and are located in the `tests/` folder.

To run tests, navigate to the root folder and run:
```
> "C:\Program Files\QGIS 3.0\bin\python-qgis.bat" -m pytest -v -s
```

## Local setup (macOS)

Install qgis3-dev from homebrew:

```
brew install qgis3-dev
```

QGIS 3 on macOS uses python installed in `/usr/local`. Python packages can be installed using pip invoking the python 3 interpreter on the system. I.e. (`python3 -m pip install 'package-name'`).

As for Windows, for fast iteration it is recommended to run the build script to symlink the current `gis4wrf` plugin to the `plugin` folder of QGIS.

```
python3 build.py
```

## Dependencies

FIXME outdated
We use `wrf-python`
For installing wrf-python on Windows, we need to use mingw-64 as it requires gfortran.

First, open the MSYS2 MSYS temrinal and install python3 and the depenedcies to be able to install numpy (a wrf-python dependency). To understand why this is required see [here](https://github.com/numpy/numpy/issues/8362#issuecomment-281939221)

```
pacman -S mingw-w64-x86_64-{openblas,lapack,python3,python3-pip}
```

Now open the MSYS2 MinGW-64 bit command prompt and install numpy and wrf-python through pip
```
pip install numpy wrf-python
```


## ZIP packaging

Simply run `build.py` and a `gis4wrf.zip` file will be created.
FIXME: the scripts for automatically download and build docs with mkdocs has been added. Remove comments once repos become public.

## Package structure

- `gis4wrf.core` contains all non-QGIS-dependent code
- `gis4wrf.qgis` is the QGIS plugin and uses `gis4wrf.core`

## HTML Widgets and Documentation

Documentation, tutorials, and info pages are created using MkDOcs and a [simple modified bootstrap template](https://github.com/gis4wrf/mkdocs-bootstrap).
First install MkDocs using `pip`:
```
pip install mkdocs
```

The download and generation of docs is done automatically by the `build.py` script (part of code currently commented out) however as the repositories are currently private the download and docs generation has to be done manually.
Download the following two repositories and unzip them in `gis4wrf/plugin/resources/meta/docs`.
```
https://github.com/gis4wrf/gis4wrf-tutorials/archive/master.zip --> gis4wrf/plugin/resources/meta/docs/gis4wrf-tutorials-master
https://github.com/gis4wrf/gis4wrf-docs/archive/master.zip --> gis4wrf/plugin/resources/meta/docs/gis4wrf-docs-master

```

The modified template needs to be added manually -- download it from https://github.com/dmey/mkdocs-bootstrap/archive/dmey/simplify.zip, unzip it and copy the folder `mkdocs_bootstrap` into `gis4wrf/plugin/resources/meta/`.

To create the html files, go into  `gis4wrf/plugin/resources/meta` and run the following command:
```
mkdocs build
```
This will create a folder called `site` with the generated html files.

## Useful libraries

QGIS comes with GDAL's Python bindings which are very close to the C library and hard to use.
Ideally we'd like to use the [rasterio](https://mapbox.github.io/rasterio) library
which is a more pythonic wrapper for GDAL, however this library [cannot be used](https://mapbox.github.io/rasterio/switch.html#mutual-incompatibilities) together with
GDAL's Python bindings. The following are alternatives to rasterio that we can use.

The following packages use GDAL's Python bindings:

- [greenwich](https://github.com/bkg/greenwich)

The following packages do not use GDAL and may be helpful in addition to GDAL:

- [xarray](http://xarray.pydata.org/en/stable/io.html), mainly for netCDF
- [PyNIO](https://www.pyngl.ucar.edu/Nio.shtml), for netCDF, HDF, GRIB (also usable via xarray)
- [wrfxpy](http://wrfxpy.readthedocs.io/):
    - heavily UNIX-dependent, more or less a set of shell scripts augmented by Python
    - not installable as Python package
    - has WRF/WPS JSON config, see http://wrfxpy.readthedocs.io/en/latest/quickstart.html
      -> adopt structure?
    - "manipulate wps/input/fire namelists; place and setup domains dynamically;  download GRIB files from various GRIB sources; execute geogrid, ungrib, metgrid, real, WRF; monitor WRF execution; postprocess netCDF files to generate raster images or KMZ raster files; arrange simulation results into catalogs for display wrfxweb"


NB: GeoTIFF files can only be read with GDAL.

## Useful websites

- [Python GDAL/OGR Cookbook](https://pcjericks.github.io/py-gdalogr-cookbook/)

## License header

The following header shall be appended at the top of every source file.

```
# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.
```
