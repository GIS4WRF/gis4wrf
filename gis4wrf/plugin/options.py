# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Optional, List
import os
import platform
import multiprocessing

from qgis.core import QgsSettings

from gis4wrf.core import find_mpiexec
from gis4wrf.core.util import export
from gis4wrf.plugin.broadcast import Broadcast

WORKING_DIR_DEFAULT_NAME = 'gis4wrf'

SETTINGS_NAMESPACE = 'gis4wrf/'
class Keys(object):
    WORKING_DIR = SETTINGS_NAMESPACE + 'working_dir'
    WRF_DIR = SETTINGS_NAMESPACE + 'wrf_dir'
    WPS_DIR = SETTINGS_NAMESPACE + 'wps_dir'
    MPI_ENABLED = SETTINGS_NAMESPACE + 'mpi_enabled'
    MPI_PROCESSES = SETTINGS_NAMESPACE + 'mpi_processes'
    RDA_USERNAME = SETTINGS_NAMESPACE + 'rda_username'
    RDA_PASSWORD = SETTINGS_NAMESPACE + 'rda_password'

class Options(object):
    def __init__(self) -> None:
        self.load()

    def load(self) -> None:
        settings = QgsSettings()

        # Working directory
        # Default on Windows: ~/My Documents/gis4wrf
        # Default on macOS: ~/Documents/gis4wrf
        # Default on Linux: ~/gis4wrf
        home = os.path.expanduser('~')
        if platform.system() == 'Windows':
            # https://stackoverflow.com/a/30924555
            import ctypes.wintypes
            CSIDL_PERSONAL = 5 # My Documents
            SHGFP_TYPE_CURRENT = 0 # Get current, not default value

            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)

            default_working_dir = os.path.join(buf.value, WORKING_DIR_DEFAULT_NAME)
        elif platform.system() == 'Darwin':
            default_working_dir = os.path.join(home, 'Documents', WORKING_DIR_DEFAULT_NAME)
        else:
            default_working_dir = os.path.join(home, WORKING_DIR_DEFAULT_NAME)

        self._working_dir = settings.value(Keys.WORKING_DIR, default_working_dir)

        self._wrf_dir = settings.value(Keys.WRF_DIR, None)
        self._wps_dir = settings.value(Keys.WPS_DIR, None)

        self._mpi_enabled = settings.value(Keys.MPI_ENABLED, False, type=bool)
        self._mpi_processes = settings.value(Keys.MPI_PROCESSES, multiprocessing.cpu_count(), type=int)

        self._rda_username = settings.value(Keys.RDA_USERNAME)
        self._rda_password = settings.value(Keys.RDA_PASSWORD)

        # Proactively enable MPI if available and if no WRF/WPS distributions are set yet.
        # This will lead more people to download the pre-built MPI-enabled distributions.
        if not self._mpi_enabled and not self._wrf_dir and not self._wps_dir:
            try:
                find_mpiexec()
            except:
                pass
            else:
                self.mpi_enabled = True
                self.save()

        self.after_load_save()

    def save(self) -> None:
        settings = QgsSettings()
        settings.setValue(Keys.WORKING_DIR, self._working_dir)
        settings.setValue(Keys.MPI_ENABLED, self._mpi_enabled)
        settings.setValue(Keys.MPI_PROCESSES, self._mpi_processes)
        settings.setValue(Keys.WRF_DIR, self._wrf_dir)
        settings.setValue(Keys.WPS_DIR, self._wps_dir)
        settings.setValue(Keys.RDA_USERNAME, self._rda_username)
        settings.setValue(Keys.RDA_PASSWORD, self._rda_password)
        self.after_load_save()
        Broadcast.options_updated.emit()

    def after_load_save(self) -> None:
        for path in [self.working_dir, self.datasets_dir, self.geog_dir, self.projects_dir, self.distributions_dir]:
            os.makedirs(path, exist_ok=True)
    
    @property
    def working_dir(self) -> str:
        return self._working_dir

    @working_dir.setter
    def working_dir(self, path) -> None:
        self._working_dir = path

    @property
    def mpi_enabled(self) -> bool:
        return self._mpi_enabled

    @mpi_enabled.setter
    def mpi_enabled(self, enabled: bool) -> None:
        self._mpi_enabled = enabled

    @property
    def mpi_processes(self) -> int:
        return self._mpi_processes

    @mpi_processes.setter
    def mpi_processes(self, count: int) -> None:
        self._mpi_processes = count

    @property
    def wrf_dir(self) -> Optional[str]:
        return self._wrf_dir

    @wrf_dir.setter
    def wrf_dir(self, path: str) -> None:
        if not path:
            path = None
        self._wrf_dir = path

    @property
    def wps_dir(self) -> Optional[str]:
        return self._wps_dir

    @wps_dir.setter
    def wps_dir(self, path: str) -> None:
        if not path:
            path = None
        self._wps_dir = path

    @property
    def geogrid_exe(self) -> Optional[str]:
        if not self.wps_dir:
            return None
        return os.path.join(self.wps_dir, 'geogrid.exe')

    @property
    def geogrid_tbl_path(self) -> Optional[str]:
        if not self.wps_dir:
            return None
        return os.path.join(self.wps_dir, 'geogrid', 'GEOGRID.TBL.ARW')

    @property
    def ungrib_exe(self) -> Optional[str]:
        if not self.wps_dir:
            return None
        return os.path.join(self.wps_dir, 'ungrib.exe')

    @property
    def ungrib_vtable_dir(self) -> Optional[str]:
        if not self.wps_dir:
            return None
        return os.path.join(self.wps_dir, 'ungrib', 'Variable_Tables')

    @property
    def metgrid_exe(self) -> Optional[str]:
        if not self.wps_dir:
            return None
        return os.path.join(self.wps_dir, 'metgrid.exe')

    @property
    def wrf_bin_dir(self) -> Optional[str]:
        if not self.wrf_dir:
            return None
        bin_dir = os.path.join(self.wrf_dir, 'main')
        if not os.path.exists(bin_dir):
            # fall-back for older gis4wrf WRF Windows distributions
            bin_dir = os.path.join(self.wrf_dir, 'run')
        return bin_dir

    @property
    def real_exe(self) -> Optional[str]:
        if not self.wrf_dir:
            return None
        return os.path.join(self.wrf_bin_dir, 'real.exe')

    @property
    def wrf_exe(self) -> Optional[str]:
        if not self.wrf_dir:
            return None
        return os.path.join(self.wrf_bin_dir, 'wrf.exe')

    @property
    def wrf_namelist_path(self) -> Optional[str]:
        if not self.wrf_dir:
            return None
        return os.path.join(self.wrf_dir, 'test', 'em_real', 'namelist.input')

    @property
    def rda_username(self) -> str:
        return self._rda_username

    @rda_username.setter
    def rda_username(self, username: str) -> None:
        self._rda_username = username

    @property
    def rda_password(self) -> str:
        return self._rda_password

    @rda_password.setter
    def rda_password(self, password: str) -> None:
        self._rda_password = password

    @property
    def projects_dir(self) -> str:
        return os.path.join(self.working_dir, 'projects')

    @property
    def datasets_dir(self) -> str:
        return os.path.join(self.working_dir, 'datasets')

    @property
    def distributions_dir(self) -> str:
        return os.path.join(self.working_dir, 'dist')

    @property
    def geog_dir(self) -> str:
        return os.path.join(self.datasets_dir, 'geog')

    @property
    def met_dir(self) -> str:
        return os.path.join(self.datasets_dir, 'met')

OPTIONS = Options()

@export
def get_options() -> Options:
    return OPTIONS
