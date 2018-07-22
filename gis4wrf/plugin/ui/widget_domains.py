# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from math import ceil

from PyQt5.QtCore import QMetaObject, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLayout, QVBoxLayout, QDialog, QGridLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QComboBox, QScrollArea, QFileDialog, QRadioButton, QLineEdit
)

from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsRectangle
from qgis.gui import QgisInterface

from gis4wrf.core import (
    LonLat, Coordinate2D, CRS, Project, read_namelist, write_namelist,
    convert_wps_nml_to_project, convert_project_to_wps_namelist
)
from gis4wrf.plugin.geo import update_domain_outline_layers, update_domain_grid_layers, get_qgis_crs, rect_to_bbox
from gis4wrf.plugin.ui.helpers import (
    MyLineEdit, add_grid_lineedit, update_input_validation_style, create_lineedit,
    create_two_radio_group_box, WhiteScroll, RATIO_VALIDATOR, DIM_VALIDATOR
)

MAX_PARENTS = 22
DECIMALS = 50
LON_VALIDATOR = QDoubleValidator(-180.0, 180.0, DECIMALS)
LAT_VALIDATOR = QDoubleValidator(-90.0, 90.0, DECIMALS)
RESOLUTION_VALIDATOR = QDoubleValidator(0.00000000000000000001, float('+inf'), DECIMALS)
DIM_VALIDATOR = QIntValidator()
DIM_VALIDATOR.setBottom(0)

HORIZONTAL_RESOLUTION_LABEL = 'Horizontal Resolution: {resolution} {unit}'

class DomainWidget(QWidget):
    tab_active = pyqtSignal()
    go_to_data_tab = pyqtSignal()

    def __init__(self, iface: QgisInterface) -> None:
        super().__init__()
        self.iface = iface

        # Import/Export
        ## Import from 'namelist.wps'
        import_from_namelist_button = QPushButton("Import from namelist")
        import_from_namelist_button.setObjectName('import_from_namelist')

        ## Export to namelist
        export_geogrid_namelist_button = QPushButton("Export to namelist")
        export_geogrid_namelist_button.setObjectName('export_geogrid_namelist_button')

        vbox_import_export = QVBoxLayout()
        vbox_import_export.addWidget(import_from_namelist_button)
        vbox_import_export.addWidget(export_geogrid_namelist_button)

        self.gbox_import_export = QGroupBox("Import/Export")
        self.gbox_import_export.setLayout(vbox_import_export)

        # Group: Map Type
        self.group_box_map_type = QGroupBox("Map Type")
        vbox_map_type = QVBoxLayout()
        hbox_map_type = QHBoxLayout()

        self.projection = QComboBox()
        self.projection.setObjectName('projection')
        projs = {
            'undefined' : '-', # do not use a default projection - let the user pick the projection.
            'lat-lon'   : 'Latitude/Longitude',
            'lambert'   : 'Lambert'
        }
        for proj_id, proj_label in projs.items():
            self.projection.addItem(proj_label, proj_id)

        hbox_map_type.addWidget(QLabel('GCS/Projection:'))
        # TODO: when the user select the type of GCS/Projection
        # we should automatically change the GCS/Projection for the whole
        # project. This will do an on-the-fly remapping of any of the other CRS
        # which are different from the one supported by our tool/WRF.
        # The Project CRS can be accessed in QGIS under the menu `Project` > `Project Properties` > `CRS.`
        # -> This is only really possible for Lat/Lon as this one is a CRS, where the others are projections
        #    that only become a full CRS with the additional parameters like truelat1.
        # TODO: fields should be cleared when the user changes the CRS/Projection.
        hbox_map_type.addWidget(self.projection)
        vbox_map_type.addLayout(hbox_map_type)

        ## Lambert only: show 'True Latitudes' field
        truelat_grid = QGridLayout()
        self.truelat1 = add_grid_lineedit(truelat_grid, 0, 'True Latitude 1',
                                          LAT_VALIDATOR, unit='°', required=True)
        self.truelat2 = add_grid_lineedit(truelat_grid, 1, 'True Latitude 2',
                                          LAT_VALIDATOR, unit='°', required=True)
        self.widget_true_lats = QWidget()
        self.widget_true_lats.setLayout(truelat_grid)
        vbox_map_type.addWidget(self.widget_true_lats)

        self.domain_pb_set_projection = QPushButton("Set Map CRS")
        self.domain_pb_set_projection.setObjectName('set_projection_button')
        vbox_map_type.addWidget(self.domain_pb_set_projection)
        self.group_box_map_type.setLayout(vbox_map_type)

        # Group: Horizontal Resolution
        self.group_box_resol = QGroupBox("Horizontal Grid Spacing")
        hbox_resol = QHBoxLayout()
        self.resolution = MyLineEdit(required=True)
        self.resolution.setValidator(RESOLUTION_VALIDATOR)
        self.resolution.textChanged.connect(lambda _: update_input_validation_style(self.resolution))
        self.resolution.textChanged.emit(self.resolution.text())
        hbox_resol.addWidget(self.resolution)
        self.resolution_label = QLabel()
        hbox_resol.addWidget(self.resolution_label)

        self.group_box_resol.setLayout(hbox_resol)


        # Group: Automatic Domain Generator
        self.group_box_auto_domain = QGroupBox("Grid Extent Calculator")
        vbox_auto_domain = QVBoxLayout()
        hbox_auto_domain = QHBoxLayout()
        domain_pb_set_canvas_extent = QPushButton("Set to Canvas Extent")
        domain_pb_set_canvas_extent.setObjectName('set_canvas_extent_button')
        domain_pb_set_layer_extent = QPushButton("Set to Active Layer Extent")
        domain_pb_set_layer_extent.setObjectName('set_layer_extent_button')
        vbox_auto_domain.addLayout(hbox_auto_domain)
        vbox_auto_domain.addWidget(domain_pb_set_canvas_extent)
        vbox_auto_domain.addWidget(domain_pb_set_layer_extent)
        self.group_box_auto_domain.setLayout(vbox_auto_domain)


        # Group: Manual Domain Configuration

        ## Subgroup: Centre Point
        grid_center_point = QGridLayout()
        self.center_lon = add_grid_lineedit(grid_center_point, 0, 'Longitude',
                                            LON_VALIDATOR, '°', required=True)
        self.center_lat = add_grid_lineedit(grid_center_point, 1, 'Latitude',
                                            LAT_VALIDATOR, '°', required=True)
        group_box_centre_point = QGroupBox("Center Point")
        group_box_centre_point.setLayout(grid_center_point)

        ## Subgroup: Advanced configuration
        grid_dims = QGridLayout()
        self.cols = add_grid_lineedit(grid_dims, 0, 'Horizontal',
                                      DIM_VALIDATOR, required=True)
        self.rows = add_grid_lineedit(grid_dims, 1, 'Vertical',
                                      DIM_VALIDATOR, required=True)
        group_box_dims = QGroupBox("Grid Extent")
        group_box_dims.setLayout(grid_dims)

        vbox_manual_domain = QVBoxLayout()
        vbox_manual_domain.addWidget(group_box_centre_point)
        vbox_manual_domain.addWidget(group_box_dims)

        self.group_box_manual_domain = QGroupBox("Advanced Configuration")
        # TODO: make this section collapsable (default state collapsed)
        # and change the checkbox to arrows like `setArrowType(Qt.RightArrow)`
        # TODO: the style should be disabled when the 'advanced configuration' box is disabled (default).
        self.group_box_manual_domain.setCheckable(True)
        self.group_box_manual_domain.setChecked(False)
        self.group_box_manual_domain.setLayout(vbox_manual_domain)

        for field in [self.resolution, self.center_lat, self.center_lon, self.rows, self.cols,
                      self.truelat1, self.truelat2]:
          # editingFinished is only emitted on user input, not via programmatic changes.
          # This is important as we want to avoid re-drawing the bbox many times when several
          # fields get changed while using the automatic domain generator.
          field.editingFinished.connect(self.on_change_any_field)

        # Group Box: Parent Domain
        self.group_box_parent_domain = QGroupBox("Enable Parenting")
        self.group_box_parent_domain.setObjectName('group_box_parent_domain')
        self.group_box_parent_domain.setCheckable(True)
        self.group_box_parent_domain.setChecked(False)

        # TODO: As it is for the single domain case the generation of the domain should be automatic.
        # For now leave placeholder values of '3' for Child to Parent Ratio and '2' for padding.
        # use `calc_parent_lonlat_from_child` in `routines.py` to calculate the coordinate of the domain given the child domain coordinate,
        # grid_ratio and padding.
        hbox_parent_num = QHBoxLayout()
        hbox_parent_num.addWidget(QLabel('Number of Parent Domains:'))
        self.parent_spin = QSpinBox()
        self.parent_spin.setObjectName('parent_spin')
        self.parent_spin.setRange(1, MAX_PARENTS)
        hbox_parent_num.addWidget(self.parent_spin)

        self.group_box_parent_domain.setLayout(hbox_parent_num)

        self.parent_domains = [] # type: list
        self.parent_vbox = QVBoxLayout()
        self.parent_vbox.setSizeConstraint(QLayout.SetMinimumSize)

        go_to_data_tab_btn = QPushButton('Continue to Datasets')
        go_to_data_tab_btn.clicked.connect(self.go_to_data_tab)

        # Tabs
        dom_mgr_layout = QVBoxLayout()
        dom_mgr_layout.addWidget(self.gbox_import_export)
        dom_mgr_layout.addWidget(self.group_box_map_type)
        dom_mgr_layout.addWidget(self.group_box_resol)
        dom_mgr_layout.addWidget(self.group_box_auto_domain)
        dom_mgr_layout.addWidget(self.group_box_manual_domain)
        dom_mgr_layout.addWidget(self.group_box_parent_domain)
        dom_mgr_layout.addLayout(self.parent_vbox)
        dom_mgr_layout.addWidget(go_to_data_tab_btn)
        self.setLayout(dom_mgr_layout)

        QMetaObject.connectSlotsByName(self)

        # trigger event for initial layout
        self.projection.currentIndexChanged.emit(self.projection.currentIndex())

    @property
    def project(self) -> Project:
        return self._project

    @project.setter
    def project(self, val: Project) -> None:
        ''' Sets the currently active project. See tab_simulation. '''
        self._project = val
        self.populate_ui_from_project()

    def populate_ui_from_project(self) -> None:
        project = self.project
        try:
            domains = project.data['domains']
        except KeyError:
            return
        
        main_domain = domains[0]

        idx = self.projection.findData(main_domain['map_proj'])
        self.projection.setCurrentIndex(idx)
        try:
            truelat1 = main_domain['truelat1']
            self.truelat1.set_value(truelat1)

            truelat2 = main_domain['truelat2']
            self.truelat2.set_value(truelat2)
        except KeyError:
            pass

        self.resolution.set_value(main_domain['cell_size'][0])

        lon, lat = main_domain['center_lonlat']
        self.center_lat.set_value(lat)
        self.center_lon.set_value(lon)

        cols, rows = main_domain['domain_size']
        self.rows.set_value(rows)
        self.cols.set_value(cols)

        if len(domains) > 1:
            self.group_box_parent_domain.setChecked(True)
            self.parent_spin.setValue(len(domains) - 1)
            # We call the signal handler explicitly as we need the widgets ready immediately
            # and otherwise this is delayed until the signals are processed (queueing etc.).
            self.on_parent_spin_valueChanged(len(domains) - 1)

            for idx, parent_domain in enumerate(domains[1:]):
                fields, _ = self.parent_domains[idx]
                fields = fields['inputs']
                
                field_to_key = {
                    'ratio': 'parent_cell_size_ratio',
                    'top': 'padding_top',
                    'left': 'padding_left',
                    'right': 'padding_right',
                    'bottom': 'padding_bottom'
                }

                for field_name, key in field_to_key.items():
                    field = fields[field_name]
                    val = parent_domain[key]
                    field.set_value(val)
        
        self.draw_bbox_and_grids(zoom_out=True)

    @pyqtSlot()
    def on_import_from_namelist_button_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(caption='Open wps namelist')
        if not file_path:
            return
        nml = read_namelist(file_path)
        project = convert_wps_nml_to_project(nml, self.project)
        # TODO load new project

    @pyqtSlot()
    def on_export_geogrid_namelist_button_clicked(self):
        if not self.update_project():
            raise ValueError('Input invalid, check fields')
        file_path, _ = QFileDialog.getSaveFileName(caption='Save wps namelist as', \
                                                   directory='namelist.wps')
        if not file_path:
            return
        wps_namelist = convert_project_to_wps_namelist(self.project)
        write_namelist(wps_namelist, file_path)

    @pyqtSlot()
    def on_set_projection_button_clicked(self):
        crs = self.create_domain_crs()

        qgsProject = QgsProject.instance() # type: QgsProject
        qgsProject.setCrs(get_qgis_crs(crs.proj4))

    def create_domain_crs(self) -> CRS:
        proj = self.get_proj_kwargs()
        if proj is None:
            raise ValueError('Incomplete projection definition')

        origin_valid = all(map(lambda w: w.is_valid(), [self.center_lat, self.center_lon]))
        if origin_valid:
            origin = LonLat(self.center_lon.value(), self.center_lat.value())
        else:
            origin = LonLat(0, 0)

        if proj['map_proj'] == 'lambert':
            crs = CRS.create_lambert(proj['truelat1'], proj['truelat2'], origin)
        elif proj['map_proj'] == 'lat-lon':
            crs = CRS.create_lonlat()
        else:
            raise NotImplementedError('unknown proj: ' + proj['map_proj'])
        return crs

    @pyqtSlot()
    def on_set_canvas_extent_button_clicked(self):
        if not self.resolution.is_valid():
            return
        canvas = self.iface.mapCanvas() # type: QgsMapCanvas

        settings = canvas.mapSettings() # type: QgsMapSettings
        map_crs = settings.destinationCrs() # type: QgsCoordinateReferenceSystem

        extent = canvas.extent() # type: QgsRectangle
        self.set_domain_to_extent(map_crs, extent)

    @pyqtSlot()
    def on_set_layer_extent_button_clicked(self):
        if not self.resolution.is_valid():
            return
        layer = self.iface.activeLayer() # type: QgsMapLayer

        layer_crs = layer.crs() # type: QgsCoordinateReferenceSystem

        extent = layer.extent() # type: QgsRectangle
        self.set_domain_to_extent(layer_crs, extent)

    def set_domain_to_extent(self, crs: QgsCoordinateReferenceSystem, extent: QgsRectangle) -> None:
        resolution = self.resolution.value()

        bbox = rect_to_bbox(extent)
        
        extent_crs = CRS(crs.toProj4())
        domain_crs = self.create_domain_crs()
        domain_srs = domain_crs.srs

        domain_bbox = domain_crs.transform_bbox(bbox, domain_srs)

        # TODO disallow creation of bounding box outside projection range (e.g. for lat-lon 360-180)

        xmin, xmax, ymin, ymax = domain_bbox.minx, domain_bbox.maxx, domain_bbox.miny, domain_bbox.maxy

        center_x = xmin + (xmax - xmin)/2
        center_y = ymin + (ymax - ymin)/2
        center_lonlat = domain_crs.to_lonlat(Coordinate2D(center_x, center_y))
        self.center_lat.set_value(center_lonlat.lat)
        self.center_lon.set_value(center_lonlat.lon)
        self.resolution.set_value(resolution)
        cols = ceil((xmax - xmin)/resolution)
        rows = ceil((ymax - ymin)/resolution)
        self.cols.set_value(cols)
        self.rows.set_value(rows)

        self.on_change_any_field(zoom_out=True)

    @pyqtSlot()
    def on_group_box_parent_domain_clicked(self):
        if self.group_box_parent_domain.isChecked():
            self.add_parent_domain()
        else:
            self.parent_spin.setValue(1)
            while self.parent_domains:
                self.remove_last_parent_domain()

    def add_parent_domain(self):
        idx = len(self.parent_domains) + 1
        fields, group_box_parent = create_parent_group_box('Parent ' + str(idx), '?', self.proj_res_unit, required=True)
        self.parent_vbox.addWidget(group_box_parent)
        # "If you add a child widget to an already visible widget you must
        #  explicitly show the child to make it visible."
        # (http://doc.qt.io/qt-5/qwidget.html#QWidget)
        group_box_parent.show()
        self.parent_domains.append((fields, group_box_parent))
        # After adding/removing widgets, we need to tell Qt to recompute the sizes.
        # This always has to be done on the widget where the child widgets have been changed,
        # here self.subtab_parenting (which contains self.parent_vbox).
        self.adjustSize()

        for field in fields['inputs'].values():
            field.editingFinished.connect(self.on_change_any_field)

    def remove_last_parent_domain(self):
        _, group_box_parent = self.parent_domains.pop()
        group_box_parent.deleteLater()
        self.parent_vbox.removeWidget(group_box_parent)
        self.on_change_any_field()

    @pyqtSlot(int)
    def on_parent_spin_valueChanged(self, value: int) -> None:
        count = len(self.parent_domains)
        for _ in range(value, count):
            self.remove_last_parent_domain()
        for _ in range(count, value):
            self.add_parent_domain()

    @pyqtSlot(int)
    def on_projection_currentIndexChanged(self, index: int) -> None:
        proj_id = self.projection.currentData()
        is_lambert = proj_id == 'lambert'
        is_undefined = proj_id == 'undefined'
        is_lat_lon = proj_id == 'lat-lon'

        self.group_box_resol.setDisabled(is_undefined)
        self.group_box_auto_domain.setDisabled(is_undefined)
        self.group_box_manual_domain.setDisabled(is_undefined)
        self.group_box_parent_domain.setDisabled(is_undefined)

        self.widget_true_lats.setVisible(is_lambert)

        if is_undefined:
            self.proj_res_unit = ''
        elif is_lat_lon:
            self.proj_res_unit = '°'
        elif is_lambert:
            self.proj_res_unit = 'm'
        self.resolution_label.setText(self.proj_res_unit)

        # If the projection is changed the parent domains are removed
        self.group_box_parent_domain.setChecked(False)
        for _ in self.parent_domains:
            self.remove_last_parent_domain()

        self.adjustSize()

    def get_proj_kwargs(self) -> dict:
        proj_id = self.projection.currentData()
        kwargs = {
            'map_proj': proj_id
        }
        if proj_id == 'lambert':
            valid = all(map(lambda w: w.is_valid(), [self.truelat1, self.truelat2]))
            if not valid:
                return None
            kwargs = {
                'map_proj' : proj_id,
                'truelat1' : self.truelat1.value(),
                'truelat2' : self.truelat2.value(),
            }
        return kwargs

    def update_project(self) -> bool:
        proj_kwargs = self.get_proj_kwargs()
        if proj_kwargs is None:
            return False

        valid = all(map(lambda w: w.is_valid(), [self.center_lat, self.center_lon, self.resolution, self.cols, self.rows]))
        if not valid:
            return False
        center_lonlat = LonLat(lon=self.center_lon.value(), lat=self.center_lat.value())
        resolution = self.resolution.value()
        domain_size = (self.cols.value(), self.rows.value())

        parent_domains = []

        for parent_domain in self.parent_domains:
            fields, _ = parent_domain
            inputs = fields['inputs']
            valid = all(map(lambda w: w.is_valid(), inputs.values()))
            if not valid:
                return False
            ratio, top, left, right, bottom = [
                inputs[name].value()
                for name in ['ratio', 'top', 'left', 'right', 'bottom']]

            parent_domains.append({
                'parent_cell_size_ratio': ratio,
                'padding_left': left,
                'padding_right': right,
                'padding_bottom': bottom,
                'padding_top': top
            })

        self.project.set_domains(
            cell_size=(resolution, resolution), domain_size=domain_size,
            center_lonlat=center_lonlat, parent_domains=parent_domains, **proj_kwargs)
        return True

    def on_change_any_field(self, zoom_out=False):
        if not self.update_project():
            return

        domains = self.project.data['domains']

        # update main domain size as it may have been adjusted
        main_domain_size = domains[0]['domain_size']
        self.cols.set_value(main_domain_size[0])
        self.rows.set_value(main_domain_size[1])

        for (fields, _), domain in zip(self.parent_domains, domains[1:]):
            # update the parent resolutions
            res_label = fields['other']['resolution']
            res_label.setText(HORIZONTAL_RESOLUTION_LABEL.format(
                resolution=domain['cell_size'][0], unit=self.proj_res_unit))

            # update any padding as it may have been adjusted
            for name in ['left', 'right', 'top', 'bottom']:
                field = fields['inputs'][name]
                field.set_value(domain['padding_' + name])

        self.draw_bbox_and_grids(zoom_out)

    def draw_bbox_and_grids(self, zoom_out: bool) -> None:
        project = self.project
        
        update_domain_grid_layers(project)
        update_domain_outline_layers(self.iface.mapCanvas(), project, zoom_out=zoom_out)

def create_parent_group_box(name: str, res: float, unit: str,
                            required: bool=False) -> QGroupBox:
    """Returns a 'validator-ready' group box to be used by the parent-domain tab."""
    parent_child_ratio_box = QGridLayout()
    # TODO: This should be a spinbox instead with range [1,5].
    parent_child_ratio = add_grid_lineedit(parent_child_ratio_box, 0,
        'Child-to-Parent Ratio', RATIO_VALIDATOR, required=required)

    res_label = QLabel(HORIZONTAL_RESOLUTION_LABEL.format(resolution=res, unit=unit))

    sub_group_box = QGroupBox("Padding")
    grid = QGridLayout()
    top_label = QLabel('Top')
    top_label.setAlignment(Qt.AlignCenter)
    grid.addWidget(top_label, 0, 1)
    left_label = QLabel('Left')
    left_label.setAlignment(Qt.AlignCenter)
    grid.addWidget(left_label, 2, 0)
    right_label = QLabel('Right')
    right_label.setAlignment(Qt.AlignCenter)
    grid.addWidget(right_label, 2, 2)
    bottom_label = QLabel('Bottom')
    bottom_label.setAlignment(Qt.AlignCenter)
    grid.addWidget(bottom_label, 4, 1)
    top = create_lineedit(DIM_VALIDATOR, required)
    left = create_lineedit(DIM_VALIDATOR, required)
    right = create_lineedit(DIM_VALIDATOR, required)
    bottom = create_lineedit(DIM_VALIDATOR, required)
    grid.addWidget(top, 1, 1)
    grid.addWidget(left, 3, 0)
    grid.addWidget(right, 3, 2)
    grid.addWidget(bottom, 5, 1)
    sub_group_box.setLayout(grid)

    vbox = QVBoxLayout()
    vbox.addLayout(parent_child_ratio_box)
    vbox.addWidget(res_label)
    vbox.addWidget(sub_group_box)
    group_box = QGroupBox(name)
    group_box.setLayout(vbox)
    return {
        'inputs': {
            'ratio': parent_child_ratio,
            'top': top,
            'left': left,
            'right': right,
            'bottom': bottom
        },
        'other': {
            'resolution': res_label
        }
    }, group_box
