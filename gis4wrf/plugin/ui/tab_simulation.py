# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.


from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtCore import pyqtSignal

from qgis.gui import QgisInterface

from gis4wrf.core import Project

from gis4wrf.plugin.constants import PLUGIN_NAME
from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.broadcast import Broadcast
from gis4wrf.plugin.ui.helpers import WhiteScroll, ensure_folder_empty
from gis4wrf.plugin.ui.widget_general import GeneralWidget
from gis4wrf.plugin.ui.widget_domains import DomainWidget
from gis4wrf.plugin.ui.widget_datasets import DatasetsWidget
from gis4wrf.plugin.ui.widget_run import RunWidget

class SimulationTab(QTabWidget):
    view_wrf_nc_file = pyqtSignal(str)

    def __init__(self, iface: QgisInterface) -> None:
        super().__init__()

        self.iface = iface

        self.options = get_options()

        self.general_tab = GeneralWidget()
        self.general_tab.open_project.connect(self.on_open_project)
        self.general_tab.create_project.connect(self.on_create_project)
        self.general_tab.close_project.connect(self.on_close_project)
        self.domain_tab = DomainWidget(iface)
        self.datasets_tab = DatasetsWidget(iface)
        self.run_tab = RunWidget(iface)

        self.domain_tab.go_to_data_tab.connect(self.open_data_tab)
        self.datasets_tab.go_to_run_tab.connect(self.open_run_tab)
        self.run_tab.view_wrf_nc_file.connect(self.view_wrf_nc_file)

        self.addTab(WhiteScroll(self.general_tab), 'General')
        self.addTab(WhiteScroll(self.domain_tab), 'Domain')
        self.addTab(WhiteScroll(self.datasets_tab), 'Data')
        self.addTab(WhiteScroll(self.run_tab), 'Run')

        self.tabs = [self.general_tab, self.domain_tab, self.datasets_tab, self.run_tab]

        self.disable_project_dependent_tabs()

        self.project = Project.create()
        self.set_project_in_tabs()

        self.currentChanged.connect(self.on_tab_changed)
        Broadcast.options_updated.connect(self.update_project)
        Broadcast.open_project_from_object.connect(self.open_project_from_object)

    def open_data_tab(self):
        self.setCurrentIndex(2)

    def open_run_tab(self):
        self.setCurrentIndex(3)

    def set_project_in_tabs(self) -> None:
        project = self.project
        if project.path:
            if not self.options.wps_dir or not self.options.wrf_dir:
                msg_bar = self.iface.messageBar() # type: QgsMessageBar
                msg_bar.pushWarning(PLUGIN_NAME, 'Path to WPS/WRF not set, functionality will be reduced. You can set the path under Settings > Options... > GIS4WRF')
            self.update_project()
        self.general_tab.project = project
        self.domain_tab.project = project
        self.datasets_tab.project = project
        self.run_tab.project = project

    def update_project(self) -> None:
        if not self.project:
            return
        
        self.project.geog_data_path = self.options.geog_dir
        self.project.met_data_path = self.options.met_dir

        try:
            self.project.init_config_files_if_needed(
                self.options.geogrid_tbl_path, self.options.wrf_namelist_path)
        except FileNotFoundError:
            pass
        
        Broadcast.project_updated.emit()

    def on_create_project(self, path: str) -> None:
        if not ensure_folder_empty(path, self.iface):
            return
        if self.project.path is None:
            # TODO notify user that Domain tab inputs are kept
            self.project.path = path
        else:
            self.project = Project.create(path)
        self.project.save()
        self.set_project_in_tabs()
        self.enable_project_dependent_tabs()

    def open_project_from_object(self, project: Project) -> None:
        self.project = project
        self.set_project_in_tabs()
        if project.path:
            self.enable_project_dependent_tabs()
            self.project.save()
        else:
            self.disable_project_dependent_tabs()

    def on_open_project(self, path: str) -> None:
        self.project = Project.load(path)
        self.set_project_in_tabs()
        self.enable_project_dependent_tabs()

    def on_close_project(self) -> None:
        self.project = Project.create()
        self.set_project_in_tabs()
        self.disable_project_dependent_tabs()

    def on_tab_changed(self, index: int) -> None:
        self.tabs[index].tab_active.emit()

    def enable_project_dependent_tabs(self) -> None:
        self.datasets_tab.setEnabled(True)
        self.run_tab.setEnabled(True)

    def disable_project_dependent_tabs(self) -> None:
        self.datasets_tab.setEnabled(False)
        self.run_tab.setEnabled(False)
