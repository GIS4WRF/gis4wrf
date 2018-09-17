# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLayout, QVBoxLayout, QDialog, QGridLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QComboBox, QScrollArea, QFileDialog, QRadioButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtGui import QPixmap

from gis4wrf.core import Project
from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.constants import GIS4WRF_LOGO_PATH

class GeneralWidget(QWidget):
    create_project = pyqtSignal(str)
    open_project = pyqtSignal(str)
    close_project = pyqtSignal()
    tab_active = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self.options = get_options()

        btn_new = QPushButton("Create GIS4WRF Project",
            clicked=self.on_create_project_button_clicked)

        btn_existing = QPushButton("Open GIS4WRF Project",
            clicked=self.on_open_project_button_clicked)

        self.current_project_label = QLabel()

        vbox = QVBoxLayout()
        title = """
                    <html>
                        <h1>GIS4WRF simulation tools</h1>
                        <br>
                    </html>
                """
        text = """
                    <html>
                        <br>
                        <p>The <em>Simulation</em> tab contains tools to help you prepare your simulations.</p>
                        <p>Here, you will find four subtabs: <em>General</em>, <em>Domain</em>, <em>Data</em>, and <em>Run</em>. In the <em>General </em>subtab you can create or open GIS4WRF projects. The <em>Domain</em>, <em>Data </em>and <em>Run </em>subtabs contain tools to help you with the steps to define and run a WRF simulation such as defining datasets to use in your simulation, configure namelists and run WPS and WRF programs.</p>
                        <p>More details on how to use these tools and examples can be found online at <a title="GIS4WRF Website -- Documentation and Tutorials" href="https://gis4wrf.github.io" target="_blank" rel="noopener">https://gis4wrf.github.io</a>.</p>
                  </html>
               """

        label_title = QLabel(title)
        label_text = QLabel(text)
        label_text.setWordWrap(True)
        label_text.setOpenExternalLinks(True)
        label_pixmap = QLabel()
        pixmap = QPixmap(GIS4WRF_LOGO_PATH)
        label_pixmap.setPixmap(pixmap)
        label_pixmap.setAlignment(Qt.AlignCenter)
        vbox.addWidget(label_title)
        vbox.addWidget(label_pixmap)
        vbox.addWidget(label_text)
        vbox.addStretch()

        vbox.addWidget(btn_new)
        vbox.addWidget(btn_existing)
        vbox.addWidget(self.current_project_label)
        self.setLayout(vbox)

    @property
    def project(self) -> Project:
        return self._project

    @project.setter
    def project(self, val: Project) -> None:
        ''' Sets the currently active project. See tab_simulation. '''
        self._project = val
        self.update_project_path_label()

    def on_create_project_button_clicked(self):
        folder = QFileDialog.getExistingDirectory(
            caption='Select new project folder', directory=self.options.projects_dir)
        if not folder:
            return
        self.create_project.emit(folder)

    def on_open_project_button_clicked(self):
        folder = QFileDialog.getExistingDirectory(
            caption='Select existing project folder', directory=self.options.projects_dir)
        if not folder:
            return
        self.open_project.emit(folder)

    def update_project_path_label(self) -> None:
        path = self.project.path
        if path is None:
            path = 'N/A'
        self.current_project_label.setText('Project path: ' + path)