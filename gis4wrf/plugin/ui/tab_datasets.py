# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from PyQt5.QtWidgets import QTabWidget, QWidget

from qgis.gui import QgisInterface

from gis4wrf.plugin.ui.helpers import WhiteScroll
from gis4wrf.plugin.ui.widget_geo import GeoToolsDownloadManager
from gis4wrf.plugin.ui.widget_met import MetToolsDownloadManager
from gis4wrf.plugin.ui.widget_process import Process


class DatasetsTab(QTabWidget):
    def __init__(self, iface) -> None:
        super().__init__()

        geo = WhiteScroll(GeoToolsDownloadManager(iface))
        met = WhiteScroll(MetToolsDownloadManager(iface))
        process = WhiteScroll(Process(iface))

        self.addTab(geo, 'Geo')
        self.addTab(met, 'Met')
        self.addTab(process, 'Process')