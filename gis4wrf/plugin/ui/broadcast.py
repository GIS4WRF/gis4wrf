# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from PyQt5.QtCore import QObject, pyqtSignal

class BroadcastSignals(QObject):
    geo_datasets_updated = pyqtSignal()
    met_datasets_updated = pyqtSignal()

Broadcast = BroadcastSignals()
