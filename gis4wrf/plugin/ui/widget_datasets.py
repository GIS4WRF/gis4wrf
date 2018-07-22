# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from operator import xor
import os
from pathlib import Path
import re

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLayout, QVBoxLayout, QDialog, QGridLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QComboBox, QScrollArea, QFileDialog, QRadioButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QAbstractItemView,
    QSizePolicy
)

from qgis.gui import QgisInterface

from gis4wrf.core import (
    read_geogrid_tbl, add_derived_metadata_to_geogrid_tbl,
    read_grib_folder_metadata, read_grib_files_metadata,
    read_wps_binary_index_file,
    GeogridTblKeys, GeogridTbl, Project, met_datasets
)
from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.geo import load_wps_binary_layer
from gis4wrf.plugin.ui.helpers import add_grid_lineedit, add_grid_combobox, clear_layout, create_lineedit, StringValidator
from gis4wrf.plugin.ui.dialog_custom_met_dataset import CustomMetDatasetDialog
from gis4wrf.plugin.constants import PLUGIN_NAME
from gis4wrf.plugin.broadcast import Broadcast

class DatasetsWidget(QWidget):
    tab_active = pyqtSignal()
    go_to_run_tab = pyqtSignal()

    def __init__(self, iface: QgisInterface) -> None:
        super().__init__()
        self.iface = iface

        self.options = get_options()

        self.tab_active.connect(self.on_tab_active)

        self.create_geographical_data_box()
        self.create_meteorological_data_box()

        go_to_run_tab_btn = QPushButton('Continue to Run')
        go_to_run_tab_btn.clicked.connect(self.go_to_run_tab)

        vbox = QVBoxLayout()
        vbox.addWidget(self.gbox_geodata)
        vbox.addWidget(self.gbox_metdata)
        vbox.addWidget(go_to_run_tab_btn)
        self.setLayout(vbox)

        Broadcast.geo_datasets_updated.connect(self.populate_geog_data_tree)
        Broadcast.met_datasets_updated.connect(self.populate_met_data_tree)
        Broadcast.project_updated.connect(self.populate_geog_data_tree)

    @property
    def project(self) -> Project:
        return self._project

    @project.setter
    def project(self, val: Project) -> None:
        ''' Sets the currently active project. See tab_simulation. '''
        self._project = val
        
        self.populate_geog_data_tree()
        self.populate_met_data_tree()

    def on_tab_active(self):
        self.update_geo_datasets_spec_fields()
        self.set_met_data_current_config_label()

    #region Geographical Data

    def create_geographical_data_box(self) -> None:
        self.gbox_geodata = QGroupBox('Geographical Data')
        vbox_geodata = QVBoxLayout()
        self.gbox_geodata.setLayout(vbox_geodata)

        gbox_avail_datasets = QGroupBox('Available Datasets')
        vbox_geodata.addWidget(gbox_avail_datasets)

        vbox_avail_dataset = QVBoxLayout()
        gbox_avail_datasets.setLayout(vbox_avail_dataset)

        self.tree_geog_data = QTreeWidget()
        self.tree_geog_data.setMinimumHeight(200)
        vbox_avail_dataset.addWidget(self.tree_geog_data)
        self.tree_geog_data.itemDoubleClicked.connect(self.on_geog_data_tree_doubleclick)       
        self.tree_geog_data.setHeaderItem(QTreeWidgetItem([
            'Group / Variable', 'Resolution', 'Interpolation Method']))

        self.tree_geog_data.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_geog_data.customContextMenuRequested.connect(self.on_tree_geog_data_open_context_menu)

        self.add_geog_dataset_button = QPushButton('Add Dataset to List')
        self.add_geog_dataset_button.clicked.connect(self.on_add_geog_dataset_button_clicked)
        vbox_avail_dataset.addWidget(self.add_geog_dataset_button)

        self.create_geog_form()
        vbox_avail_dataset.addWidget(self.geog_dataset_form)

        gbox_datasets_spec = QGroupBox('Selection')
        vbox_geodata.addWidget(gbox_datasets_spec)
        self.vbox_geo_datasets_spec = QVBoxLayout()
        gbox_datasets_spec.setLayout(self.vbox_geo_datasets_spec)

        # selection fields get created in the on_tab_active handler
        self.geo_dataset_spec_inputs = []

    def update_geo_datasets_spec_fields(self) -> None:
        msg_bar = self.iface.messageBar() # type: QgsMessageBar
        specs = self.project.geo_dataset_specs
        domain_cnt = self.project.domain_count
        field_cnt = self.vbox_geo_datasets_spec.count()

        while field_cnt > domain_cnt:
            layout = self.vbox_geo_datasets_spec.takeAt(field_cnt - 1)
            clear_layout(layout)
            del self.geo_dataset_spec_inputs[-1]
            self.update_project_geo_dataset_specs()
            field_cnt -= 1
        
        while field_cnt < domain_cnt:
            def create_on_plus_clicked_callback():
                # This code is in this inner function to have a copy of field_cnt,
                # otherwise all on_clicked handlers would refer to field_cnt of the
                # last loop iteration.
                domain_index = field_cnt
                def on_clicked():
                    spec_input = self.geo_dataset_spec_inputs[domain_index]
                    item = self.tree_geog_data.currentItem()
                    if item is None:
                        msg_bar.pushInfo(PLUGIN_NAME, 'Select a group in the dataset tree before clicking the + button.')
                        return
                    if item.childCount() == 0:
                        msg_bar.pushWarning(PLUGIN_NAME, 'Select a group in the dataset tree, not a variable.')
                        return
                    new_group_name = item.data(0, Qt.UserRole)
                    val = spec_input.value()
                    if val:
                        existing_group_names = val.split('+')
                        if new_group_name in existing_group_names:
                            msg_bar.pushWarning(PLUGIN_NAME, 'The group you selected is already added for this domain.')
                            return
                        val += '+'
                    val += new_group_name
                    spec_input.set_value(val)
                return on_clicked

            def create_on_info_clicked_callback():
                # This code is in this inner function to have a copy of field_cnt,
                # otherwise all on_clicked handlers would refer to field_cnt of the
                # last loop iteration.
                domain_index = field_cnt
                def on_clicked():
                    spec_input = self.geo_dataset_spec_inputs[domain_index]
                    group_names = spec_input.value().split('+')

                    # determine resolved datasets for each variable
                    tbl = self.geogrid_tbl
                    resolved_groups = dict() # var name -> (group name or None)
                    for variable in sorted(tbl.variables.values(), key=lambda v: v.name):
                        var_group_names = variable.group_options.keys()
                        found_group_name = None
                        for group_name in group_names:
                            if group_name in var_group_names:
                                found_group_name = group_name
                                break
                        resolved_groups[variable.name] = found_group_name
                    
                    # show in message box
                    title = 'Domain {}'.format(domain_index + 1)
                    text = '<table><tr><td><b>Variable</b></td><td><b>Group</b></td></tr>'
                    for var_name, group_name in resolved_groups.items():
                        if group_name is None:
                            group_name = '<b><i>N/A</i></b>'
                        text += '<tr><td>{}</td><td>{}</td></tr>'.format(var_name, group_name)
                    text += '</table>'
                    QMessageBox.information(self.iface.mainWindow(), title, text)
                return on_clicked
                                                             
            hbox_datasets_spec = QHBoxLayout()
            hbox_datasets_spec.addWidget(QLabel('Domain: {}'.format(field_cnt + 1)))
            dataset_spec_input = create_lineedit(StringValidator(self.is_valid_geo_dataset_spec),
                                                 required=True)
            try:
                dataset_spec_input.set_value(specs[field_cnt])
            except IndexError:
                pass
            dataset_spec_input.textChanged.connect(self.update_project_geo_dataset_specs)
            self.geo_dataset_spec_inputs.append(dataset_spec_input)
            hbox_datasets_spec.addWidget(dataset_spec_input)
            plus_btn = QPushButton('+', clicked=create_on_plus_clicked_callback())
            info_btn = QPushButton('?', clicked=create_on_info_clicked_callback())
            # TODO make this dynamic, using size policies didn't work
            info_btn.setMaximumWidth(50)
            plus_btn.setMaximumWidth(50)
            hbox_datasets_spec.addWidget(plus_btn)
            hbox_datasets_spec.addWidget(info_btn)
            self.vbox_geo_datasets_spec.addLayout(hbox_datasets_spec)
            field_cnt += 1

    def is_valid_geo_dataset_spec(self, spec: str) -> bool:
        # must only contain geographical dataset group names separated by pluses without duplicates
        tbl = self.geogrid_tbl
        if not tbl:
            return False
        spec_group_names = spec.split('+')
        if len(set(spec_group_names)) != len(spec_group_names):
            return False
        if any(group_name not in tbl.group_names for group_name in spec_group_names):
            return False
        return True

    def update_project_geo_dataset_specs(self) -> None:
        self.project.geo_dataset_specs = [inp.value() if inp.is_valid() else ''
                                          for inp in self.geo_dataset_spec_inputs]

    def create_geog_form(self):
        grid = QGridLayout()
        self.geog_dataset_form = QGroupBox('Add Dataset')
        self.geog_dataset_form.setLayout(grid)
        self.geog_dataset_form.hide()

        group_name_validator = StringValidator(lambda s: s and re.fullmatch(r'[a-zA-Z0-9_]+', s))
        # TODO fix validator if empty
        interp_validator = StringValidator(lambda s: ' ' not in s)

        self.geog_dataset_form_group_name = add_grid_lineedit(grid, 0, 'Group Name',
                                                              validator=group_name_validator, required=True)
        self.geog_dataset_form_dataset = add_grid_combobox(grid, 1, 'Dataset')
        self.geog_dataset_form_variable = add_grid_combobox(grid, 2, 'Variable')
        self.geog_dataset_form_interp = add_grid_combobox(grid, 3, 'Interpolation')
        self.geog_dataset_form_custom_interp = add_grid_lineedit(grid, 4, 'Custom Interpolation',
                                                                 validator=interp_validator, required=False)
        
        self.geog_dataset_form_variable.currentIndexChanged.connect(self.geog_dataset_form_variable_changed)

        btn_add = QPushButton('Add')
        btn_cancel = QPushButton('Cancel')
        btn_add.clicked.connect(self.on_add_geog_dataset_form_button_clicked)
        btn_cancel.clicked.connect(self.on_cancel_geog_dataset_form_button_clicked)

        grid.addWidget(btn_cancel, 5, 0)
        grid.addWidget(btn_add, 5, 1)

    def populate_geog_data_tree(self) -> None:
        tree = self.tree_geog_data
        tree.clear()

        try:
            tbl = self.geogrid_tbl = self.project.read_geogrid_tbl()
        except FileNotFoundError:
            return
        if tbl is None:
            return
        add_derived_metadata_to_geogrid_tbl(tbl, self.options.geog_dir)

        for group_name in sorted(tbl.group_names):
            all_missing = not any(group_name in var.group_options and 
                                  not var.group_options[group_name][GeogridTblKeys.MISSING]
                                  for var in tbl.variables.values())
            group_item = QTreeWidgetItem(self.tree_geog_data)
            group_item.setText(0, group_name)
            group_item.setData(0, Qt.UserRole, group_name)
            if all_missing:
                group_item.setDisabled(True)
                for i in [0, 1, 2]:
                    group_item.setToolTip(i, 'No dataset available in this group')

            for var_name in sorted(tbl.variables.keys()):
                group_options_all = tbl.variables[var_name].group_options
                if group_name not in group_options_all:
                    continue
                group_options = group_options_all[group_name]
                interp = group_options[GeogridTblKeys.INTERP_OPTION]
                
                # not available when missing on disk
                resolution = group_options.get(GeogridTblKeys.RESOLUTION, '')

                var_item = QTreeWidgetItem(group_item)
                var_item.setText(0, var_name)
                var_item.setText(1, resolution)
                var_item.setText(2, interp)
                var_item.setToolTip(2, interp)
                var_item.setData(0, Qt.UserRole, group_options[GeogridTblKeys.ABS_PATH])
                if group_options[GeogridTblKeys.MISSING]:
                    var_item.setDisabled(True)
                    for i in [0, 1, 2]:
                        var_item.setToolTip(i, 'Dataset not available')

    def on_geog_data_tree_doubleclick(self, item: QTreeWidgetItem, column: int) -> None:
        if item.childCount() > 0:
            # clicked on a group
            return
        abs_path = item.data(0, Qt.UserRole)
        if not os.path.exists(abs_path):
            # dataset doesn't exist
            return
        load_wps_binary_layer(abs_path)

    def on_tree_geog_data_open_context_menu(self, position) -> None:
        item = self.tree_geog_data.currentItem()
        if item is None:
            return

        menu = QMenu()

        if item.parent() is None:
            remove_group_action = menu.addAction('Remove Group')
            remove_group_action.triggered.connect(self.on_tree_geog_data_remove_group_clicked)
        else:
            view_dataset_action = menu.addAction('View Dataset')
            view_dataset_action.triggered.connect(lambda: self.on_geog_data_tree_doubleclick(item, 0))

        menu.exec_(self.tree_geog_data.viewport().mapToGlobal(position))

    def on_tree_geog_data_remove_group_clicked(self):
        item = self.tree_geog_data.currentItem()
        group_name = item.data(0, Qt.UserRole)

        reply = QMessageBox.question(self.iface.mainWindow(), 'Remove Group',
            'Are you sure you want to remove the group "{}"?'.format(group_name),
            QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        self.geogrid_tbl.remove(group_name)
        self.project.write_geogrid_tbl(self.geogrid_tbl)

        self.populate_geog_data_tree()

    def on_add_geog_dataset_button_clicked(self):
        self.add_geog_dataset_button.hide()
        self.geog_dataset_form.show()

        self.geog_dataset_form_dataset.clear()
        self.geog_dataset_form_dataset.addItem('-')
        for root, subdirs, _ in os.walk(self.options.geog_dir):
            for subdir in subdirs:
                path = os.path.join(root, subdir)
                rel_path = os.path.relpath(path, self.options.geog_dir)
                self.geog_dataset_form_dataset.addItem(rel_path, path)

        var_names = sorted(self.geogrid_tbl.variables.keys())
        self.geog_dataset_form_variable.clear()
        self.geog_dataset_form_variable.addItem('-')
        for var_name in var_names:
            self.geog_dataset_form_variable.addItem(var_name, var_name)

        # interpolation method dropdown is populated in change callback of variable dropdown
        self.geog_dataset_form_interp.clear()
        self.geog_dataset_form_interp.addItem('-')

    def geog_dataset_form_variable_changed(self, index: int):
        var_name = self.geog_dataset_form_variable.currentData()
        if var_name is None:
            return
        
        interp_options = set(group_options[GeogridTblKeys.INTERP_OPTION]
                             for group_options
                             in self.geogrid_tbl.variables[var_name].group_options.values())

        self.geog_dataset_form_interp.clear()
        self.geog_dataset_form_interp.addItem('-')
        for interp in sorted(interp_options):
            self.geog_dataset_form_interp.addItem(interp, interp)

    def on_add_geog_dataset_form_button_clicked(self):
        dataset_path = self.geog_dataset_form_dataset.currentData()
        var_name = self.geog_dataset_form_variable.currentData()
        existing_interp = self.geog_dataset_form_interp.currentData()
        group_name = self.geog_dataset_form_group_name
        custom_interp = self.geog_dataset_form_custom_interp

        msg_bar = self.iface.messageBar() # type: QgsMessageBar

        if not dataset_path:
            msg_bar.pushCritical(PLUGIN_NAME, 'Dataset not selected.')
            return

        if not var_name:
            msg_bar.pushCritical(PLUGIN_NAME, 'Variable not selected.')
            return

        if not group_name.is_valid():
            msg_bar.pushCritical(PLUGIN_NAME, 'Invalid group name.')
            return

        if not custom_interp.is_valid():
            msg_bar.pushCritical(PLUGIN_NAME, 'Invalid custom interpolation.')
            return

        if not xor(bool(custom_interp.value()), bool(existing_interp)):
            msg_bar.pushCritical(PLUGIN_NAME, 'Must have either interpolation or custom interpolation.')
            return

        interp = custom_interp.value()
        if not interp:
            interp = existing_interp

        if var_name == 'LANDUSEF':
            landmask_water = read_wps_binary_index_file(dataset_path).landmask_water
        else:
            landmask_water = None

        self.geogrid_tbl.add(group_name.value(), var_name, dataset_path,
                             self.options.geog_dir, interp, landmask_water)
        self.project.write_geogrid_tbl(self.geogrid_tbl)

        self.populate_geog_data_tree()

        self.add_geog_dataset_button.show()
        self.geog_dataset_form.hide()

    def on_cancel_geog_dataset_form_button_clicked(self) -> None:
        self.add_geog_dataset_button.show()
        self.geog_dataset_form.hide()

    #endregion Geographical Data

    #region Meteorological Data

    def create_meteorological_data_box(self) -> None:
        self.gbox_metdata = QGroupBox('Meteorological Data')
        vbox_metdata = QVBoxLayout()
        self.gbox_metdata.setLayout(vbox_metdata)

        gbox_avail_metdata = QGroupBox('Available Datasets')
        vbox_metdata.addWidget(gbox_avail_metdata)

        vbox_avail_metdata = QVBoxLayout()
        gbox_avail_metdata.setLayout(vbox_avail_metdata)

        self.tree_met_data = QTreeWidget()
        self.tree_met_data.setMinimumHeight(200)
        vbox_avail_metdata.addWidget(self.tree_met_data)
        self.tree_met_data.setHeaderItem(QTreeWidgetItem(['Product / Time Range']))
        self.tree_met_data.setSelectionMode(QAbstractItemView.ContiguousSelection)

        self.tree_met_data.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_met_data.customContextMenuRequested.connect(self.on_tree_met_data_open_context_menu)

        gbox_datasets_spec = QGroupBox('Selection')
        vbox_metdata.addWidget(gbox_datasets_spec)

        vbox_datasets_spec = QVBoxLayout()
        gbox_datasets_spec.setLayout(vbox_datasets_spec)

        selection_button = QPushButton('Use Dataset Selection from List')
        selection_button.clicked.connect(self.on_met_data_selection_button_clicked)
        vbox_datasets_spec.addWidget(selection_button)

        custom_button = QPushButton('Use Custom Dataset')
        custom_button.clicked.connect(self.on_met_data_custom_button_clicked)
        vbox_datasets_spec.addWidget(custom_button)

        hbox_current_config = QHBoxLayout()
        vbox_datasets_spec.addLayout(hbox_current_config)
        hbox_current_config.addWidget(QLabel('Current Configuration: '))
        self.met_data_current_config_label = QLabel()
        hbox_current_config.addWidget(self.met_data_current_config_label)
        self.set_met_data_current_config_label()
        hbox_current_config.insertStretch(-1)
        
    def set_met_data_current_config_label(self) -> None:
        try:
            spec = self.project.met_dataset_spec
        except (KeyError, AttributeError):
            config = None
        else:
            time_range = [d.strftime('%Y-%m-%d %H:%M') for d in spec['time_range']]
            dataset = spec['dataset']
            product = spec['product']
            if dataset:
                config = '{} / {}\n{} -\n{}'.format(spec['dataset'], spec['product'], *time_range)
            else:
                config = 'Custom dataset / {} GRIB files\n{} -\n{}'.format(len(spec['paths']), *time_range)

        lbl = self.met_data_current_config_label
        if not config:
            lbl.setText('Undefined')
            lbl.setStyleSheet(self.undef_label_style)
        else:
            lbl.setText(config)
            lbl.setStyleSheet('')

    def on_met_data_selection_button_clicked(self) -> None:
        msg_bar = self.iface.messageBar() # type: QgsMessageBar

        items = self.tree_met_data.selectedItems()

        if not items:
            msg_bar.pushInfo(PLUGIN_NAME, 'Select a time range or a sequence of time steps in the dataset tree before clicking this button.')
            return

        datas = [item.data(0, Qt.UserRole) for item in items]
        if any(data is None for data in datas):
            msg_bar.pushWarning(PLUGIN_NAME, 'Do not select dataset or product entries, only time ranges.')
            return
        
        is_file = [os.path.isfile(data) for data in datas]
        is_dir = [not f for f in is_file]
        if not all(is_file) and not all(is_dir):
            msg_bar.pushWarning(PLUGIN_NAME, 'Select either a time range or a sequence of time steps.')
            return

        if is_file[0]:
            if len(datas) == 1:
                msg_bar.pushWarning(PLUGIN_NAME, 'Select at least two time steps.')
                return
            file_paths = datas
            time_range_folder = os.path.dirname(file_paths[0])
            meta_all, meta_files = read_grib_files_metadata(file_paths)
        else:
            assert len(datas) == 1
            time_range_folder = datas[0]
            meta_all, meta_files = read_grib_folder_metadata(time_range_folder)
            
        product_folder = os.path.dirname(time_range_folder)
        dataset_folder = os.path.dirname(product_folder)
        
        self.project.met_dataset_spec = {
            'paths': [meta.path for meta in meta_files],
            'dataset': os.path.basename(dataset_folder),
            'product': os.path.basename(product_folder),
            'time_range': meta_all.time_range,
            'interval_seconds': meta_all.interval_seconds
        }
        self.set_met_data_current_config_label()

    def on_met_data_custom_button_clicked(self) -> None:
        try:
            spec = self.project.met_dataset_spec
            if spec['dataset']:
                spec = None # not a custom dataset
        except KeyError:
            # met data not configured yet
            spec = None

        dialog = CustomMetDatasetDialog(self.options.ungrib_vtable_dir, spec)
        if not dialog.exec_():
            return

        vtable_path = dialog.vtable_path
        # only store absolute path if not a standard WPS vtable
        if Path(vtable_path).parent == Path(self.options.ungrib_vtable_dir):
            vtable_path = Path(vtable_path).name

        self.project.met_dataset_spec = {
            'paths': dialog.paths,
            'base_folder': dialog.base_folder,
            'vtable': vtable_path,
            'time_range': [dialog.start_date, dialog.end_date],
            'interval_seconds': dialog.interval_seconds
        }
        self.set_met_data_current_config_label()

    def on_tree_met_data_open_context_menu(self, position) -> None:
        item = self.tree_met_data.currentItem()
        if item is None:
            return
        data = item.data(0, Qt.UserRole)
        if data is None or not os.path.isdir(data):
            return

        menu = QMenu()
        
        view_vars_action = menu.addAction('View Variables')
        view_vars_action.triggered.connect(self.on_tree_met_data_view_variables_clicked)

        menu.exec_(self.tree_met_data.viewport().mapToGlobal(position))

    def on_tree_met_data_view_variables_clicked(self) -> None:
        item = self.tree_met_data.currentItem()
        dataset_folder = item.data(0, Qt.UserRole)

        meta, _ = read_grib_folder_metadata(dataset_folder)

        title = 'Variables for {} ({})'.format(item.parent().text(0), item.text(0))
        text = '<table>'
        for var_name, var_label in sorted(meta.variables.items()):
            text += '<tr><td>{}</td><td>{}</td></tr>'.format(var_name, var_label)
        text += '</table>'
        QMessageBox.information(self.iface.mainWindow(), title, text)

    def populate_met_data_tree(self) -> None:
        tree = self.tree_met_data
        tree.clear()

        root_dir = self.options.met_dir
        # TODO is this the right place to check?
        if not os.path.exists(root_dir):
            return
        for dataset_name in os.listdir(root_dir):
            dataset_path = os.path.join(root_dir, dataset_name)
            if not os.path.isdir(dataset_path):
                continue

            long_name = met_datasets.get(dataset_name)
            if long_name:
                label = '{}: {}'.format(dataset_name, long_name)
            else:
                label = dataset_name

            dataset_item = QTreeWidgetItem(tree)
            dataset_item.setText(0, label)
            if long_name:
                dataset_item.setToolTip(0, 'Dataset: ' + long_name)
            dataset_item.setExpanded(True)

            for product_name in os.listdir(dataset_path):
                product_folder = os.path.join(dataset_path, product_name)
                if not os.path.isdir(product_folder):
                    continue

                product_item = QTreeWidgetItem(dataset_item)
                product_item.setText(0, product_name)
                product_item.setToolTip(0, 'Product: ' + product_name)
                product_item.setExpanded(True)

                for time_range_name in os.listdir(product_folder):
                    time_range_folder = os.path.join(product_folder, time_range_name)
                    if not os.path.isdir(time_range_folder):
                        continue

                    folder_meta, file_metas = read_grib_folder_metadata(time_range_folder)
                    if not file_metas:
                        continue

                    # TODO disable item and subitems if bbox does not fully cover the outer-most domain

                    time_range = '{} - {}'.format(*map(lambda d: d.strftime('%Y-%m-%d %H:%M'), folder_meta.time_range))
                
                    time_range_item = QTreeWidgetItem(product_item)
                    time_range_item.setText(0, time_range)
                    time_range_item.setToolTip(0, time_range_folder)
                    time_range_item.setData(0, Qt.UserRole, time_range_folder)

                    for file_meta in file_metas:
                        if file_meta.time_range[0] == file_meta.time_range[1]:
                            time = file_meta.time_range[0].strftime('%Y-%m-%d %H:%M')
                        else:
                            time = '{} - {}'.format(*map(lambda d: d.strftime('%Y-%m-%d %H:%M'), file_meta.time_range))

                        file_item = QTreeWidgetItem(time_range_item)
                        file_item.setText(0, time)
                        file_item.setToolTip(0, file_meta.path)
                        file_item.setData(0, Qt.UserRole, file_meta.path)


    #endregion Meteorological Data

    undef_label_style = ("""
        QLabel {
            font-weight: bold;
            color: #ff0000;
        }
    """)

