# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Optional
from math import ceil
from pathlib import Path

from PyQt5.QtCore import QMetaObject, Qt, QLocale, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QPalette
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLayout, QVBoxLayout, QDialog, QGridLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QComboBox, QScrollArea, QFileDialog, QRadioButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem
)

from gis4wrf.core import Project

from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.ui.helpers import FormattedLabel, create_browser_layout

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
        page = Path('tab_simulation_general', 'index.html')
        vbox.addLayout(create_browser_layout(page))
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