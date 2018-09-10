# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List, Dict, Optional
from collections import namedtuple
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QPalette#, QHeaderView
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLayout, QVBoxLayout, QDialog, QGridLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QComboBox, QScrollArea, QFileDialog, QRadioButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QDockWidget, QSlider, QListWidget, QListWidgetItem,
    QAbstractItemView
)

import gis4wrf.core
from gis4wrf.core import WRFNetCDFVariable
import gis4wrf.plugin.geo
from gis4wrf.plugin.ui.helpers import add_grid_lineedit, add_grid_combobox, dispose_after_delete

Dataset = namedtuple('Dataset', [
    'name', # str
    'path', # str
    'variables', # Dict[str,WRFNetCDFVariable]
    'times', # List[str]
    'extra_dims' # Dict[str,WRFNetCDFExtraDim]
])

class ViewWidget(QWidget):
    tab_active = pyqtSignal()

    def __init__(self, iface, dock_widget: QDockWidget) -> None:
        super().__init__()
        self.iface = iface
        self.dock_widget = dock_widget
        
        self.vbox = QVBoxLayout()
        self.create_variable_selector()
        self.create_time_selector()
        self.create_extra_dim_selector()
        self.create_interp_input()
        self.create_dataset_selector()
        self.setLayout(self.vbox)

        self.datasets = {} # type: Dict[str, Dataset]
        self.selected_dataset = None # type: Optional[str]
        self.selected_variable = {} # type: Dict[str,str]
        self.selected_time = {} # type: Dict[str,int]
        self.selected_extra_dim = {} # type: Dict[Tuple[str,str],int]

        self.pause_replace_layer = False

    def create_variable_selector(self) -> None:
        self.variable_selector = QListWidget()
        self.variable_selector.currentItemChanged.connect(self.on_variable_selected)
        hbox = QHBoxLayout()
        hbox.addWidget(self.variable_selector)
        self.vbox.addLayout(hbox)

    def create_time_selector(self) -> None:
        self.time_label = QLabel('Time: N/A')
        self.time_selector = QSlider(Qt.Horizontal)
        self.time_selector.setSingleStep(1)
        self.time_selector.setPageStep(1)
        self.time_selector.setMinimum(0)
        self.time_selector.valueChanged.connect(self.on_time_selected)
        self.vbox.addWidget(self.time_label)
        self.vbox.addWidget(self.time_selector)

    def create_extra_dim_selector(self) -> None:
        self.extra_dim_label = QLabel('N/A:')
        self.extra_dim_selector = QComboBox()
        self.extra_dim_selector.currentIndexChanged.connect(self.on_extra_dim_selected)
        hbox = QHBoxLayout()
        hbox.addWidget(self.extra_dim_label)
        hbox.addWidget(self.extra_dim_selector)
        hbox.setContentsMargins(0, 0, 0, 0)
        self.extra_dim_container = QWidget()
        self.extra_dim_container.setLayout(hbox)
        self.extra_dim_container.setHidden(True)
        self.vbox.addWidget(self.extra_dim_container)

    def create_interp_input(self) -> None:
        grid = QGridLayout()

        self.interp_vert_selector = add_grid_combobox(grid, 0, 'Vertical Variable')
        self.interp_input = add_grid_lineedit(grid, 1, 'Desired Level', QDoubleValidator(0.0, 10000.0, 50), required=True)       
        self.interp_input.returnPressed.connect(self.on_interp_btn_clicked)

        btn = QPushButton('Interpolate')
        btn.clicked.connect(self.on_interp_btn_clicked)
        grid.addWidget(btn, 2, 1)

        self.interp_container = QGroupBox('Interpolate Vertical Level')
        self.interp_container.setCheckable(True)
        self.interp_container.setChecked(False)
        self.interp_container.toggled.connect(self.on_interp_toggled)
        self.interp_container.setLayout(grid)
        self.interp_container.setHidden(True)
        self.vbox.addWidget(self.interp_container)

    def create_dataset_selector(self) -> None:
        dataset_label = QLabel('Dataset:')
        self.dataset_selector = QComboBox()
        self.dataset_selector.currentIndexChanged.connect(self.on_dataset_selected)
        hbox = QHBoxLayout()
        hbox.addWidget(dataset_label)
        hbox.addWidget(self.dataset_selector)
        self.vbox.addLayout(hbox)

    def add_dataset(self, path: str) -> None:
        variables = gis4wrf.core.get_supported_wrf_nc_variables(path)
        times = gis4wrf.core.get_wrf_nc_time_steps(path)
        extra_dims = gis4wrf.core.get_wrf_nc_extra_dims(path)
        dataset_name = os.path.basename(path)
        is_new_dataset = dataset_name not in self.datasets
        self.datasets[dataset_name] = Dataset(dataset_name, path, variables, times, extra_dims)
        if is_new_dataset:
            self.dataset_selector.addItem(dataset_name, dataset_name)
        self.select_dataset(dataset_name)

    def select_dataset(self, dataset_name: str) -> None:
        index = self.dataset_selector.findData(dataset_name)
        self.dataset_selector.setCurrentIndex(index)

    def init_variable_selector(self) -> None:
        dataset = self.dataset
        selected = self.selected_variable.get(dataset.name)
        self.variable_selector.clear()
        for var_name, variable in sorted(dataset.variables.items(), key=lambda v: v[1].label):
            item = QListWidgetItem(variable.label)
            item.setData(Qt.UserRole, var_name)
            self.variable_selector.addItem(item)
            if var_name == selected:
                item.setSelected(True)
        if selected is None:
            self.extra_dim_container.hide()

    def init_time_selector(self) -> None:
        dataset = self.dataset
        self.time_selector.setMaximum(len(dataset.times) - 1)
        selected_time = self.selected_time.get(dataset.name, 0)
        self.select_time(selected_time)
        # force label update in case the index didn't change during dataset change
        self.on_time_selected(selected_time)

    def select_time(self, index: int) -> None:
        self.time_selector.setValue(index)

    def init_extra_dim_selector(self) -> None:
        dataset = self.dataset
        variable = self.variable
        extra_dim_name = variable.extra_dim_name
        if extra_dim_name is None:
            self.extra_dim_container.hide()
            return
        # prevent double layer replace, already happens in on_variable_selected()
        self.pause_replace_layer = True
        extra_dim = dataset.extra_dims[extra_dim_name]
        selected_extra_dim = self.selected_extra_dim.get((dataset.name, extra_dim_name), 0)
        self.extra_dim_label.setText(extra_dim.label + ':')
        self.extra_dim_selector.clear()
        for step in extra_dim.steps:
            self.extra_dim_selector.addItem(step)
        self.extra_dim_selector.setCurrentIndex(selected_extra_dim)
        self.extra_dim_container.show()
        self.pause_replace_layer = False

    def init_interp_input(self, dataset_init: bool) -> None:
        if dataset_init:
            self.interp_vert_selector.clear()
            has_vert = False
            sorted_variables = sorted(self.dataset.variables.values(), key=lambda v: v.label)
            for variable in sorted_variables:
                if variable.extra_dim_name != 'bottom_top':
                    continue
                has_vert = True
                if len(variable.label) > 30:
                    interp_vert_selector_label = variable.label[:27] + '...'
                else:
                    interp_vert_selector_label = variable.label
                self.interp_vert_selector.addItem(interp_vert_selector_label, variable.name)
            if not has_vert:
                self.extra_dim_container.setEnabled(True)
                self.interp_container.hide()
        else:
            variable = self.variable
            extra_dim_name = variable.extra_dim_name
            if extra_dim_name != 'bottom_top':
                self.interp_container.hide()
                return
            self.interp_container.show()
        
    def on_dataset_selected(self, index: int) -> None:
        self.init_variable_selector()
        self.init_time_selector()
        self.init_interp_input(True)
        
        previous_dataset = self.selected_dataset
        if previous_dataset is not None:
            gis4wrf.plugin.geo.remove_group(previous_dataset)
        self.selected_dataset = self.dataset_name

    def on_variable_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        if current is None:
            return
        dataset = self.dataset
        var_name = current.data(Qt.UserRole)
        assert var_name == self.var_name
        self.selected_variable[dataset.name] = var_name
        self.init_extra_dim_selector()
        self.init_interp_input(False)
        self.replace_variable_layer()
        self.select_time_band_in_variable_layers()
        
    def on_time_selected(self, index: int) -> None:
        dataset = self.dataset
        self.selected_time[dataset.name] = index
        self.time_label.setText('Time: ' + dataset.times[index])
        self.select_time_band_in_variable_layers()

    def on_extra_dim_selected(self, index: int) -> None:
        if index == -1:
            # happens when clearing the dropdown entries
            return
        variable = self.variable
        extra_dim_name = variable.extra_dim_name
        self.selected_extra_dim[(self.dataset_name, extra_dim_name)] = index
        self.replace_variable_layer()
        self.select_time_band_in_variable_layers()

    def on_interp_toggled(self, enabled: True) -> None:
        self.extra_dim_container.setEnabled(not enabled)
        self.replace_variable_layer()

    def on_interp_btn_clicked(self) -> None:
        self.replace_variable_layer()
        self.select_time_band_in_variable_layers()

    def replace_variable_layer(self) -> None:
        if self.pause_replace_layer:
            return
        if self.interp_enabled and self.interp_level is None:
            return
        dataset = self.dataset
        variable = self.variable
        extra_dim_index = self.extra_dim_index
        interp_level = self.interp_level
        interp_vert_name = self.interp_vert_name
        if interp_level is not None:
            extra_dim_index = None
        uri, dispose = gis4wrf.core.convert_wrf_nc_var_to_gdal_dataset(
            dataset.path, variable.name, extra_dim_index, interp_level, interp_vert_name)
        layer = gis4wrf.plugin.geo.load_layers([(uri, variable.label, variable.name)],
            group_name=dataset.name, visible=True)[0]
        dispose_after_delete(layer, dispose)

    def select_time_band_in_variable_layers(self) -> None:
        dataset = self.dataset
        time_idx = self.time_index
        layers = gis4wrf.plugin.geo.get_raster_layers_in_group(dataset.name)
        for layer in layers:
            var_name = layer.shortName()
            if var_name in dataset.variables:
                gis4wrf.plugin.geo.switch_band(layer, time_idx)
    
    @property
    def dataset_name(self) -> str:
        return self.dataset_selector.currentData()

    @property
    def var_name(self) -> str:
        return self.variable_selector.currentItem().data(Qt.UserRole)   

    @property
    def time_index(self) -> int:
        return self.time_selector.value()

    @property
    def extra_dim_index(self) -> Optional[int]:
        if self.variable.extra_dim_name is None:
            return None
        index = self.extra_dim_selector.currentIndex()
        assert index != -1
        return index

    @property
    def interp_enabled(self):
        return self.interp_container.isVisible() and self.interp_container.isChecked()

    @property
    def interp_vert_name(self):
        if not self.interp_enabled:
            return None
        return self.interp_vert_selector.currentData()

    @property
    def interp_level(self) -> Optional[float]:
        if not self.interp_enabled:
            return None
        if not self.interp_input.is_valid():
            return None
        return self.interp_input.value()

    @property
    def dataset(self) -> Dataset:
        return self.datasets[self.dataset_name]

    @property
    def variable(self) -> WRFNetCDFVariable:
        return self.dataset.variables[self.var_name]
