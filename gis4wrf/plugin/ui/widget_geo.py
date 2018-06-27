# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List, Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QListWidget, QListWidgetItem, QProgressBar

from gis4wrf.core import (
    geo_datasets, geo_datasets_mandatory_hires, geo_datasets_mandatory_lores,
    download_and_extract_geo_dataset, is_geo_dataset_downloaded, get_geo_dataset_path
)
from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.ui.helpers import reraise, MessageBar
from gis4wrf.plugin.ui.thread import TaskThread
from gis4wrf.plugin.ui.broadcast import Broadcast

class GeoToolsDownloadManager(QWidget):
    def __init__(self, iface) -> None:
        super().__init__()

        self.options = get_options()
        self.msg_bar = MessageBar(iface)

        vbox = QVBoxLayout()
        self.setLayout(vbox)
        
        self.list_widget = QListWidget()
        self.populate_tree()
        vbox.addWidget(self.list_widget)

        self.select_mandatory_hires_button = QPushButton('Select Mandatory Fields in Highest Resolution')
        self.select_mandatory_hires_button.clicked.connect(self.on_select_mandatory_hires_button_clicked)
        vbox.addWidget(self.select_mandatory_hires_button)

        self.select_mandatory_lores_button = QPushButton('Select Mandatory Fields in Lowest Resolution')
        self.select_mandatory_lores_button.clicked.connect(self.on_select_mandatory_lores_button_clicked)
        vbox.addWidget(self.select_mandatory_lores_button)

        self.download_button = QPushButton('Download Selected Datasets')
        self.download_button.clicked.connect(self.on_download_button_clicked)
        vbox.addWidget(self.download_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        vbox.addWidget(self.progress_bar)

    def populate_tree(self) -> None:
        for name, label in geo_datasets.items():
            item = QListWidgetItem('{}: {}'.format(label, name))
            item.setData(Qt.UserRole, name)
            if is_geo_dataset_downloaded(name, self.options.geog_dir):
                item.setFlags(Qt.NoItemFlags)
                item.setToolTip('Dataset downloaded in: {}'.format(
                    get_geo_dataset_path(name, self.options.geog_dir)))
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)

    def on_select_mandatory_lores_button_clicked(self):
        self.select_datasets(geo_datasets_mandatory_lores)

    def on_select_mandatory_hires_button_clicked(self):
        self.select_datasets(geo_datasets_mandatory_hires)

    def select_datasets(self, names: List[str]) -> None:
        items = self.get_items()
        for name, item in items.items():
            item.setCheckState(Qt.Checked if name in names else Qt.Unchecked)

    def get_items(self) -> Dict[str,QListWidgetItem]:
        items = {} # type: Dict[str,QListWidgetItem]
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            items[item.data(Qt.UserRole)] = item
        return items

    def on_download_button_clicked(self) -> None:
        datasets_to_download = []
        for name, item in self.get_items().items():
            if item.checkState() == Qt.Checked:
                datasets_to_download.append(name)

        # TODO report progress
        thread = TaskThread(lambda: self.download_datasets(datasets_to_download))
        thread.started.connect(self.on_started_download)
        thread.finished.connect(self.on_finished_download)
        thread.succeeded.connect(self.on_successful_download)
        thread.failed.connect(reraise)
        thread.start()

    def on_started_download(self):
        self.download_button.hide()
        self.progress_bar.show()
        self.list_widget.setEnabled(False)

    def on_finished_download(self) -> None:
        self.download_button.show()
        self.progress_bar.hide()
        self.list_widget.setEnabled(True)
        self.list_widget.clear()
        self.populate_tree()
        Broadcast.geo_datasets_updated.emit()

    def on_successful_download(self) -> None:
        self.msg_bar.success('Geographical datasets downloaded successfully.')

    def download_datasets(self, dataset_names: List[str]) -> None:
        for name in dataset_names:
            download_and_extract_geo_dataset(name, self.options.geog_dir)
