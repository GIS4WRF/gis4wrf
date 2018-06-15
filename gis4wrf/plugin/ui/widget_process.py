# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

import os

from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QFileDialog, QTableWidget, QMessageBox
from qgis.gui import QgsMessageBar

from gis4wrf.plugin.constants import *
from gis4wrf.plugin.ui.helpers import ensure_folder_empty
from gis4wrf.core import convert_to_wps_binary


class Process(QWidget):
    def __init__(self, iface) -> None:
        super().__init__()

        self.iface = iface

        vbox = QVBoxLayout()
        btn_convert_to_wps = QPushButton('Convert active layer to WPS binary')
        btn_convert_to_wps.clicked.connect(self.run_convert_to_wps_binary)
        vbox.addWidget(btn_convert_to_wps)
        vbox.addStretch()

        self.setLayout(vbox)


    def run_convert_to_wps_binary(self) -> None:
        msg_bar = self.iface.messageBar() # type: QgsMessageBar
        layer = self.iface.activeLayer() # type: QgsMapLayer
        source = layer.source()
        if not os.path.exists(source):
            # Currently in-memory layers are not supported, but QGIS in most cases saves
            # layers to temporary files on disk during processing operations, so this is not a big issue.
            msg_bar.pushCritical(PLUGIN_NAME, 'Layer must exist on the filesystem')
            return
        reply = QMessageBox.question(self.iface.mainWindow(), 'Layer type',
                 "Is this layer's data categorical?", QMessageBox.Yes, QMessageBox.No)
        is_categorical = reply == QMessageBox.Yes
        out_dir = QFileDialog.getExistingDirectory(caption='Select WPS Binary File Output Folder')
        if not out_dir:
            return
        if not ensure_folder_empty(out_dir, self.iface):
            return
        output = convert_to_wps_binary(source, out_dir, is_categorical, strict_datum=False)
        msg_bar.pushInfo(PLUGIN_NAME, 'WPS Binary Format files created in {}'.format(out_dir))
        if output.datum_mismatch:
            msg_bar.pushWarning(PLUGIN_NAME,
                'Input layer had an unexpected datum, no datum shift was performed. Expected: {}, Actual: {}'.format(
                    output.datum_mismatch.expected, output.datum_mismatch.actual))