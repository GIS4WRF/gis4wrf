# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.


from PyQt5.QtCore import Qt, QDate, QTime, QDateTime
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QGridLayout, QGroupBox, QLabel, QHBoxLayout, 
    QComboBox, QRadioButton, QTreeWidget, QTreeWidgetItem, QDateTimeEdit, QTreeWidgetItemIterator,
    QListWidget, QListWidgetItem, QProgressBar, QMessageBox
)


from gis4wrf.core import (
    met_datasets, get_met_products, is_met_dataset_downloaded, get_met_dataset_path, download_met_dataset,
    CRS)
from gis4wrf.plugin.ui.helpers import add_grid_lineedit, TaskThread, MessageBar, reraise
from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.geo import rect_to_bbox
from .broadcast import Broadcast


DECIMALS = 50
LON_VALIDATOR = QDoubleValidator(-180.0, 180.0, DECIMALS)
LAT_VALIDATOR = QDoubleValidator(-90.0, 90.0, DECIMALS)

# TODO display bbox as vector layer if not global extent
# TODO update simulation-data subtab after downloading new data

class MetToolsDownloadManager(QWidget):
    def __init__(self, iface) -> None:
        super().__init__()

        self.iface = iface
        self.options = get_options()
        self.msg_bar = MessageBar(iface)

        vbox = QVBoxLayout()
        self.setLayout(vbox)
       
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)

        hbox.addWidget(QLabel('Dataset: '))
        self.cbox_dataset = QComboBox()
        self.cbox_dataset.addItem('-')
        for index, (dataset_name, dataset_label) in enumerate(met_datasets.items()):
            self.cbox_dataset.addItem(dataset_name, dataset_name)
            self.cbox_dataset.setItemData(index + 1, dataset_label, Qt.ToolTipRole)
        self.cbox_dataset.currentIndexChanged.connect(self.on_dataset_changed)
        hbox.addWidget(self.cbox_dataset)
        
        hbox_product_name = QHBoxLayout()
        vbox.addLayout(hbox_product_name)
        hbox_product_name.addWidget(QLabel('Product: '))
        self.cbox_product = QComboBox()
        self.cbox_product.currentIndexChanged.connect(self.on_product_changed)
        hbox_product_name.addWidget(self.cbox_product)

        hbox_start_datetime = QHBoxLayout()
        vbox.addLayout(hbox_start_datetime)
        self.dedit_start_date = QDateTimeEdit()
        self.dedit_start_date.setCalendarPopup(True)
        hbox_start_datetime.addWidget(QLabel('Start: '))
        hbox_start_datetime.addWidget(self.dedit_start_date)

        hbox_end_datetime = QHBoxLayout()
        vbox.addLayout(hbox_end_datetime)
        self.dedit_end_date = QDateTimeEdit()
        self.dedit_end_date.setCalendarPopup(True)
        hbox_end_datetime.addWidget(QLabel('End: '))
        hbox_end_datetime.addWidget(self.dedit_end_date)

        gbox_extent = QGroupBox('Extent')
        vbox.addWidget(gbox_extent)
        vbox_extent = QVBoxLayout()
        gbox_extent.setLayout(vbox_extent)

        hbox_extent = QHBoxLayout()
        vbox_extent.addLayout(hbox_extent)
        self.radio_global = QRadioButton('Global')
        self.radio_global.toggled.connect(self.on_extent_radio_button_clicked)
        hbox_extent.addWidget(self.radio_global)
        self.radio_subset = QRadioButton('Subset')
        self.radio_subset.toggled.connect(self.on_extent_radio_button_clicked)
        hbox_extent.addWidget(self.radio_subset)

        self.widget_extent = QWidget()
        vbox_extent.addWidget(self.widget_extent)
        grid_extent = QGridLayout()
        self.widget_extent.setLayout(grid_extent)
        self.widget_extent.hide()
        self.top = add_grid_lineedit(grid_extent, 0, 'North Latitude',
                                     LAT_VALIDATOR, '°', required=True)
        self.right = add_grid_lineedit(grid_extent, 1, 'East Longitude',
                                      LON_VALIDATOR, '°', required=True)
        self.left = add_grid_lineedit(grid_extent, 2, 'West Longitude',
                                       LON_VALIDATOR, '°', required=True)
        self.bottom = add_grid_lineedit(grid_extent, 3, 'South Latitude',
                                        LAT_VALIDATOR, '°', required=True)
        self.extent_from_active_layer = QPushButton('Set from Active Layer')
        grid_extent.addWidget(self.extent_from_active_layer, 4, 1)
        self.extent_from_active_layer.clicked.connect(self.on_extent_from_active_layer_button_clicked)
        self.radio_global.setChecked(True)

        self.tree = QListWidget()
        vbox_tree = QVBoxLayout()
        vbox.addLayout(vbox_tree)
        vbox_tree.addWidget(self.tree)

        self.btn_download = QPushButton('Download')
        self.btn_download.clicked.connect(self.on_download_button_clicked)
        vbox.addWidget(self.btn_download)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        vbox.addWidget(self.progress_bar)

    def on_dataset_changed(self, index: int):
        self.cbox_product.clear()
        dataset_name = self.cbox_dataset.currentData()
        if dataset_name is None:
            return
        auth = (self.options.rda_username, self.options.rda_password)
        self.products = get_met_products(dataset_name, auth)
        for product in self.products.keys():
            self.cbox_product.addItem(product, product)

    def on_product_changed(self, index: int):
        if index == -1:
            return
        
        self.tree.clear()
        product_name = self.cbox_product.currentData()
        current_avail_vars = self.products[product_name]
        dates = []
        for name in current_avail_vars.keys():
            item = QListWidgetItem(current_avail_vars[name]['label'])
            item.setData(Qt.UserRole, name)
            item.setCheckState(Qt.Checked)
            self.tree.addItem(item)
            dates.append(current_avail_vars[name]['start_date'])
            dates.append(current_avail_vars[name]['end_date'])
        date_min = min(dates)
        date_max = max(dates)

        for dt_input in [self.dedit_start_date, self.dedit_end_date]:
            dt_input.setDateTimeRange(
                QDateTime(QDate(date_min.year, date_min.month, date_min.day), QTime(date_min.hour, date_min.minute)),
                QDateTime(QDate(date_max.year, date_max.month, date_max.day), QTime(date_max.hour, date_max.minute)))

        min_dt = self.dedit_start_date.minimumDateTime()
        max_dt = self.dedit_start_date.maximumDateTime()
        self.dedit_start_date.setDateTime(min_dt)
        self.dedit_end_date.setDateTime(max_dt)

    def on_download_button_clicked(self):
        param_names = []
        for index in range(self.tree.count()):
            item = self.tree.item(index)
            if item.checkState() == Qt.Checked:
                param_name = item.data(Qt.UserRole)
                param_names.append(param_name)

        dataset_name = self.cbox_dataset.currentData()
        product_name = self.cbox_product.currentData()
        start_date = self.dedit_start_date.dateTime().toPyDateTime()
        end_date = self.dedit_end_date.dateTime().toPyDateTime()

        args = [self.options.met_dir, dataset_name, product_name, start_date, end_date]
        if is_met_dataset_downloaded(*args):
            reply = QMessageBox.question(self.iface.mainWindow(), 'Existing dataset',
                ('You already downloaded data with the selected dataset/product/date/time combination. '
                 'If you continue, this data will be removed.\n'
                 'Location: {}'.format(get_met_dataset_path(*args))),
                QMessageBox.Ok, QMessageBox.Cancel)
            if reply == QMessageBox.Cancel:
                return

        lat_north = self.top.value()
        lat_south = self.bottom.value()
        lon_west = self.left.value()
        lon_east = self.right.value()
        auth = (self.options.rda_username, self.options.rda_password)

        thread = TaskThread(
            lambda: download_met_dataset(self.options.met_dir, auth, 
                                         dataset_name, product_name, param_names,
                                         start_date, end_date,
                                         lat_south, lat_north, lon_west, lon_east),
            yields_progress=True)
        thread.started.connect(self.on_started_download)
        thread.progress.connect(self.on_progress_download)
        thread.finished.connect(self.on_finished_download)
        thread.succeeded.connect(self.on_successful_download)
        thread.failed.connect(reraise)
        thread.start()

    def on_started_download(self) -> None:
        self.btn_download.hide()
        self.progress_bar.show()
        
    def on_progress_download(self, percent: int, status: str) -> None:
        self.progress_bar.setValue(percent)
        if status == 'submitted':
            self.msg_bar.info('Met dataset download request submitted successfully, waiting until available for download...')
        elif status == 'ready':
            self.msg_bar.info('Met dataset download request is now ready, downloading...')
        else:
            print(status)
    
    def on_finished_download(self) -> None:
        self.btn_download.show()
        self.progress_bar.hide()
    
    def on_successful_download(self) -> None:
        self.msg_bar.success('Meteorological dataset downloaded successfully.')
        Broadcast.met_datasets_updated.emit()

    def on_extent_radio_button_clicked(self):
        if self.radio_global.isChecked():
            self.top.set_value(90)
            self.bottom.set_value(-90)
            self.left.set_value(-180)
            self.right.set_value(180)
            self.top.setDisabled(True)
            self.bottom.setDisabled(True)
            self.left.setDisabled(True)
            self.right.setDisabled(True)
            self.widget_extent.hide()

        elif self.radio_subset.isChecked():
            self.widget_extent.show()
            self.top.setDisabled(False)
            self.bottom.setDisabled(False)
            self.left.setDisabled(False)
            self.right.setDisabled(False)

    def on_extent_from_active_layer_button_clicked(self):
        layer = self.iface.activeLayer() # type: Optional[QgsMapLayer]
        if layer is None:
            return
        layer_crs = CRS(layer.crs().toProj4())
        target_crs = CRS('+proj=latlong +datum=WGS84')
        extent = layer.extent() # type: QgsRectangle
        bbox = rect_to_bbox(extent)
        bbox_geo = layer_crs.transform_bbox(bbox, target_crs.srs)
        padding = 5 # degrees
        lat_south = max(bbox_geo.miny - 5, -90)
        lat_north = min(bbox_geo.maxy + 5, 90)
        lon_west = max(bbox_geo.minx - 5, -180)
        lon_east = min(bbox_geo.maxx + 5, 180)
        self.bottom.set_value(lat_south)
        self.top.set_value(lat_north)
        self.left.set_value(lon_west)
        self.right.set_value(lon_east)
