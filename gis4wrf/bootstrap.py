# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List, Tuple, Iterable, Any
from collections import namedtuple
import os
import sys
import platform
from pathlib import Path
import shutil
import subprocess
import sysconfig
import site
import pkg_resources
import random

DID_BOOTSTRAP = False

# Python x.y version tuple, e.g. ('3', '6').
PY_MAJORMINOR = platform.python_version_tuple()[:2]

# name: distribution name, min: minimum version we require, install: version to be installed
Dependency = namedtuple('Dep', ['name', 'min', 'install'])

# All extra packages we need that are generally not part of
# QGIS's Python (on Windows) or the system Python (on Linux/macOS).
# Given that we use a custom site-packages folder (in ~/.gis4wrf) there are some limitations on
# what we can do since Python does not allow multiple versions of a package to be used.
# If a package is already installed, it is only updated if we had installed
# it ourselves, in which case it would be in our custom site-packages folder.
# If an installed package has a version lower than the 'min' key but we did not install it ourselves,
# then we can't do anything and have to notify the user to update the package manually
# (this would typically happen on Linux/macOS where QGIS uses the system Python installation).
# If a package is not installed, then it is installed with the exact version given in
# the 'install' key. Exact versions are used to avoid surprises when new versions are released.
# Note that if it is determined that we can install or update a given package, then all other packages
# that we installed ourselves, even if they don't need to be updated, are re-installed as well.
# This works around some limitations of 'pip install --prefix' and cannot be prevented currently.
# See the end of this script for more details on this.
DEPS = [
    # Direct dependencies.

    Dependency('f90nml', install='1.0.2', min=None),

    # Indirect dependencies.
    # Indirect dependencies are dependencies that we don't import directly in our code but
    # that are required by one or more of the main dependencies above and that require a special version
    # to be installed. Normally they would be automatically installed by one of the direct
    # dependencies above, but this would nearly always install the latest version of that
    # indirect dependency. The reason why we sometimes don't want that is mostly due to packaging
    # bugs where the latest version is binary incompatible with older versions of numpy.
    # And since we can't update numpy ourselves, we need to use older versions of those indirect
    # dependencies which are built against older versions of numpy.
]
# For some packages we need to use different versions depending on the Python version used.
if PY_MAJORMINOR == ('3', '6'):
    DEPS += [
        # NetCDF4 >= 1.3.0 is built against too recent numpy version.
        Dependency('netCDF4',
            install='1.2.9',
            min='None'),
        # dependency of netCDF4
        Dependency('cftime',
            install='1.5.1',
            min='None'),
    ]
elif PY_MAJORMINOR == ('3', '7'):
    DEPS += [
        Dependency('netCDF4',
            install='1.4.2',
            min='None'),
        # dependency of netCDF4
        Dependency('cftime',
            install='1.5.1',
            min='None'),
    ]
elif PY_MAJORMINOR == ('3', '9'):
    DEPS += [
        Dependency('netCDF4',
            install='1.5.7',
            min='None'),
        # dependency of netCDF4
        Dependency('cftime',
            install='1.5.1',
            min='None'),
    ]
# best effort
else:
    DEPS += [
        Dependency('netCDF4',
            install='1.*',
            min='None'),
        # dependency of netCDF4
        Dependency('cftime',
            install='1.*',
            min='None'),
    ]

# Use a custom folder for the packages to avoid polluting the per-user site-packages.
# This also avoids any permission issues.
# Windows: ~\AppData\Local\gis4wrf\python<xy>
# macOS: ~/Library/Application Support/gis4wrf/python<xy>
# Linux: ~/.local/share/gis4wrf/python<xy>
if platform.system() == 'Windows':
    DATA_HOME = os.getenv('LOCALAPPDATA')
    assert DATA_HOME, '%LOCALAPPDATA% not found'
elif platform.system() == 'Darwin':
    DATA_HOME = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
else:
    DATA_HOME = os.getenv('XDG_DATA_HOME')
    if not DATA_HOME:
        DATA_HOME = os.path.join(os.path.expanduser('~'), '.local', 'share')
INSTALL_PREFIX = os.path.join(DATA_HOME, 'gis4wrf', 'python' + ''.join(PY_MAJORMINOR))
LOG_PATH = os.path.join(INSTALL_PREFIX, 'pip.log')

def bootstrap() -> Iterable[Tuple[str,Any]]:
    ''' Yields a stream of log information. '''
    global DID_BOOTSTRAP
    if DID_BOOTSTRAP:
        return
    DID_BOOTSTRAP = True

    # Add custom folder to search path.
    for path in site.getsitepackages(prefixes=[INSTALL_PREFIX]):
        if not path.startswith(INSTALL_PREFIX):
            # On macOS, some global paths are added as well which we don't want.
            continue
        
        # Distribution installs of Python in Ubuntu return "dist-packages"
        # instead of "site-packages". But 'pip install --prefix ..' always
        # uses "site-packages" as the install location.
        path = path.replace('dist-packages', 'site-packages')

        yield ('log', 'Added {} as module search path'.format(path))
        
        # Make sure directory exists as it may otherwise be ignored later on when we need it.
        # This is because Python seems to cache whether module search paths do not exist to avoid
        # redundant lookups.
        os.makedirs(path, exist_ok=True)

        site.addsitedir(path)
        # pkg_resources doesn't listen to changes on sys.path.
        pkg_resources.working_set.add_entry(path)

    # pip tries to install packages even if they are installed already in the
    # custom folder. To avoid that, we do the check ourselves.
    # However, if any package is missing, we re-install all packages.
    # See the comment below on why this is necessary.
    installed = []
    needs_install = []
    cannot_update = []
    for dep in DEPS:
        try:
            # Will raise DistributionNotFound if not found.
            location = pkg_resources.get_distribution(dep.name).location
            is_local = Path(INSTALL_PREFIX) in Path(location).parents

            if not dep.min:
                installed.append((dep, is_local))
            else:
                # There is a minimum version constraint, check that.
                try:
                    # Will raise VersionConflict on version mismatch.
                    pkg_resources.get_distribution('{}>={}'.format(dep.name, dep.min))
                    installed.append((dep, is_local))
                except pkg_resources.VersionConflict as exc:
                    # Re-install is only possible if the previous version was installed by us.
                    if is_local:
                        needs_install.append(dep)
                    else:
                        # Continue without re-installing this package and hope for the best.
                        # cannot_update is populated which can later be used to notify the user
                        # that a newer version is required and has to be manually updated.
                        cannot_update.append((dep, exc.dist.version))
                        installed.append((dep, False))

        except pkg_resources.DistributionNotFound as exc:
            needs_install.append(dep)

    if needs_install:
        yield ('needs_install', needs_install)
        yield ('log', 'Package directory: ' + INSTALL_PREFIX)
        # Remove everything as we can't upgrade packages when using --prefix
        # which may lead to multiple pkg-0.20.3.dist-info folders for different versions
        # and that would lead to false positives with pkg_resources.get_distribution().
        if os.path.exists(INSTALL_PREFIX):
            # Some randomness for the temp folder name, in case an old one is still lying around for some reason. 
            rnd = random.randint(10000, 99999)
            tmp_dir = INSTALL_PREFIX + '_tmp_{}'.format(rnd)
            # On Windows, rename + delete allows to re-create the folder immediately,
            # otherwise it may still be locked and we get "Permission denied" errors.
            os.rename(INSTALL_PREFIX, tmp_dir)
            shutil.rmtree(tmp_dir)
        os.makedirs(INSTALL_PREFIX, exist_ok=True)

        # Determine packages to install.
        # Since we just cleaned all packages installed by us, including those that didn't need
        # a re-install, re-install those as well.
        installed_local = [dep for dep, is_local in installed if is_local]
        req_specs = []
        for dep in needs_install + installed_local:
            if dep.install.startswith('http'):
                req_specs.append(dep.install)
            else:
                req_specs.append('{}=={}'.format(dep.name, dep.install))

        # Locate python in order to invoke pip.
        python = os.path.join(sysconfig.get_path('scripts'), 'python3')

        # Handle the special Python environment bundled with QGIS on Windows.
        try:
            import qgis
        except:
            qgis = None
        if os.name == 'nt' and qgis:
            # sys.executable will be one of two things:
            # within QGIS: C:\Program Files\QGIS 3.0\bin\qgis-bin-g7.4.0.exe
            # within python-qgis.bat: C:\PROGRA~1\QGIS 3.0\apps\Python36\python.exe
            exe_path = sys.executable
            exe_dir = os.path.dirname(exe_path)
            if os.path.basename(exe_path) == 'python.exe':
                python_qgis_dir = os.path.join(exe_dir, os.pardir, os.pardir, 'bin')
            else:
                python_qgis_dir = exe_dir
            python = os.path.abspath(os.path.join(python_qgis_dir, 'python-qgis.bat'))
            if not os.path.isfile(python):
                python = os.path.abspath(os.path.join(python_qgis_dir, 'python-qgis-ltr.bat'))

        # Must use a single pip install invocation, otherwise dependencies of newly
        # installed packages get re-installed and we couldn't pin versions.
        # E.g. 'pip install pandas==0.20.3' will install pandas, but doing
        #      'pip install xarray==0.10.0' after that would re-install pandas (latest version)
        #      as it's a dependency of xarray.
        # This is all necessary due to limitations of pip's --prefix option.
        args = [python, '-m', 'pip', 'install', '--prefix', INSTALL_PREFIX] + req_specs
        yield ('log', ' '.join(args))
        for line in run_subprocess(args, LOG_PATH):
            yield ('log', line)
        yield ('install_done', None)

    if cannot_update:
        for dep, _ in cannot_update:
            yield ('cannot_update', cannot_update)

def run_subprocess(args: List[str], log_path: str) -> Iterable[str]:
    startupinfo = None
    if os.name == 'nt':
         # hides the console window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    process = subprocess.Popen(args,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               bufsize=1, universal_newlines=True,
                               startupinfo=startupinfo)
    with open(log_path, 'w') as fp:
        while True:
            line = process.stdout.readline()
            if line != '':
                fp.write(line)
                yield line
            else:
                break
    process.wait()

    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, args)
