# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

import os
import sys
import platform
import subprocess
import glob
from fnmatch import fnmatch
import zipfile
import requests
import zipfile
import io
from pathlib import Path
import subprocess
import shutil

import PyQt5.pyrcc_main as pyrcc

PKG_NAME = 'gis4wrf'

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
PKG_DIR = os.path.join(THIS_DIR, PKG_NAME)
ZIP_FILE = PKG_DIR + '.zip'

# All entries will be interpreted with wildcards around them
ZIP_EXCLUDES = [
    '__pycache__'
]

# Create QT resources file

QT_RESOURCES_DIR = os.path.join(PKG_DIR, 'plugin', 'resources')
QT_RESOURCES = glob.glob(os.path.join(QT_RESOURCES_DIR, '*.qrc'))
PYQT_RESOURCE_FILE = os.path.join(QT_RESOURCES_DIR, 'resources.py')

if not pyrcc.processResourceFile(QT_RESOURCES, PYQT_RESOURCE_FILE, listFiles=False):
    print('Error creating PyQT resources file', file=sys.stderr)
    sys.exit(1)

# Symlink plugin into QGIS plugins folder

if platform.system() == 'Windows' or platform.system() == 'Darwin':
    PLATFORM = platform.system()
    HOME = os.path.expanduser('~')
    if PLATFORM == 'Windows':
        QGIS_PLUGINS_DIR = os.path.join(HOME, 'AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins')
    elif PLATFORM == 'Darwin':
        QGIS_PLUGINS_DIR = os.path.join(HOME, 'Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins')
    QGIS_PLUGIN_DIR = os.path.join(QGIS_PLUGINS_DIR, PKG_NAME)

    if not os.path.exists(os.path.dirname(QGIS_PLUGINS_DIR)):
        print('Could not find QGIS3 user profile folder, not creating symlink for plugin', file=sys.stderr)
    elif os.path.exists(QGIS_PLUGIN_DIR):
        print('Folder {} exists, not creating symlink'.format(QGIS_PLUGIN_DIR))
    else:
        # QGIS only creates the /plugins folder after installing the first plugin
        if not os.path.exists(QGIS_PLUGINS_DIR):
            os.mkdir(QGIS_PLUGINS_DIR)
        try:
            if PLATFORM == 'Windows':
                subprocess.check_output(['mklink', '/j', QGIS_PLUGIN_DIR, PKG_DIR], shell=True)
            elif PLATFORM == 'Darwin':
                os.symlink(PKG_DIR, QGIS_PLUGIN_DIR)
        except subprocess.CalledProcessError as err:
            print('Error creating symlink for plugin:')
            print(err.output, file=sys.stderr)


# Download docs and tutorials and create html files
def download_and_unzip(url, path):
    response = requests.get(url, stream=True)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        zip_ref.extractall(path)

PATH_TO_THEME = Path.cwd().joinpath('gis4wrf', 'plugin','resources', 'meta')

## We use the modified gis4wrf modified bootstrap theme for MkDocs
print('Downloading gis4wrf bootstrap theme to: '+ str(PATH_TO_THEME))
download_and_unzip('https://github.com/GIS4WRF/mkdocs-bootstrap/archive/gis4wrf_theme.zip', PATH_TO_THEME)

PATH_TO_DOCS = PATH_TO_THEME.joinpath('docs')
print('Downloading docs to: '+ str(PATH_TO_DOCS))
download_and_unzip('https://github.com/GIS4WRF/gis4wrf-docs/archive/master.zip', PATH_TO_DOCS)
# TODO: enable this bit for automatically download and generate the documentation.
# download_and_unzip('https://github.com/dmey/gis4wrf-tutorials/archive/master.zip', PATH_TO_DOCS)

subprocess.run(["mkdocs", "build"], cwd=str(PATH_TO_DOCS.parent), check=True)

# Copy CHANGELOG.txt, ATTRIBUTION.txt, and LICENSE.txt into gis4wrf plugin directory
print('Copying CHANGELOG.txt to the package directory: '+ PKG_DIR)
shutil.copy(os.path.join(THIS_DIR,'CHANGELOG.txt' ), os.path.join(PKG_DIR,'CHANGELOG.txt'))
print('Copying ATTRIBUTION.txt to the package directory: '+ PKG_DIR)
shutil.copy(os.path.join(THIS_DIR,'ATTRIBUTION.txt' ), os.path.join(PKG_DIR,'ATTRIBUTION.txt'))
print('Copying LICENSE.txt to the package directory: '+ PKG_DIR)
shutil.copy(os.path.join(THIS_DIR,'LICENSE.txt' ), os.path.join(PKG_DIR,'LICENSE.txt'))

# Package into ZIP file
def create_zip(zip_path, folder_path, ignore_patterns):
    print('Creating ZIP archive ' + zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                path = os.path.join(root, file)
                archive_path = os.path.relpath(os.path.join(root, file), os.path.join(folder_path, os.pardir))
                if not any(fnmatch(path, '*' + ignore + '*') for ignore in ignore_patterns):
                    print('Adding ' + archive_path)
                    zipf.write(path, archive_path)
                else:
                    print('Ignoring ' + archive_path)
    print('Created ZIP archive ' + zip_path)

create_zip(ZIP_FILE, PKG_DIR, ZIP_EXCLUDES)