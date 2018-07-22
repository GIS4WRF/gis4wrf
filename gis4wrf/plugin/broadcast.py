# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from PyQt5.QtCore import QObject, pyqtSignal

from gis4wrf.core import Project

class BroadcastSignals(QObject):
    geo_datasets_updated = pyqtSignal()
    met_datasets_updated = pyqtSignal()
    options_updated = pyqtSignal()
    project_updated = pyqtSignal()
    open_project_from_object = pyqtSignal(Project)

Broadcast = BroadcastSignals()
