# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List, Dict, Iterable, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QProgressBar,
    QTreeWidget, QTreeWidgetItem, QHeaderView
)

from gis4wrf.core import (
    geo_datasets, geo_datasets_mandatory_hires, geo_datasets_mandatory_lores,
    download_and_extract_geo_dataset, is_geo_dataset_downloaded, get_geo_dataset_path,
    dd_to_dms, formatted_dd_to_dms, logger
)
from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.broadcast import Broadcast
from gis4wrf.plugin.ui.helpers import reraise, MessageBar
from gis4wrf.plugin.ui.thread import TaskThread

# higher resolution than default (100)
PROGRESS_BAR_MAX = 1000

class GeoToolsDownloadManager(QWidget):
    def __init__(self, iface) -> None:
        super().__init__()

        self.options = get_options()
        self.msg_bar = MessageBar(iface)

        self.tree_widget = QTreeWidget ()
        self.populate_tree()

        self.select_mandatory_hires_button = QPushButton('Select Mandatory Fields in Highest Resolution')
        self.select_mandatory_hires_button.clicked.connect(self.on_select_mandatory_hires_button_clicked)

        self.select_mandatory_lores_button = QPushButton('Select Mandatory Fields in Lowest Resolution')
        self.select_mandatory_lores_button.clicked.connect(self.on_select_mandatory_lores_button_clicked)

        self.download_button = QPushButton('Download Selected Datasets')
        self.download_button.clicked.connect(self.on_download_button_clicked)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, PROGRESS_BAR_MAX)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()

        vbox = QVBoxLayout()
        vbox.addWidget(self.tree_widget)
        vbox.addWidget(self.select_mandatory_hires_button)
        vbox.addWidget(self.select_mandatory_lores_button)
        vbox.addWidget(self.download_button)
        vbox.addWidget(self.progress_bar)
        self.setLayout(vbox)

    def populate_tree(self) -> None:
        self.tree_widget.setHeaderLabels(['ID', 'Resolution', 'Description'])
        self.tree_widget.setRootIsDecorated(False)
        self.tree_widget.setSortingEnabled(True)
        self.tree_widget.sortByColumn(0, Qt.AscendingOrder)
        header = self.tree_widget.header()
        header.setSectionsMovable(False)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        for dataset_id, (description, resolution) in geo_datasets.items():
            item = QTreeWidgetItem(self.tree_widget)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

            item.setText(0, dataset_id)
            item.setData(0, Qt.UserRole, dataset_id)
            item.setCheckState(0, Qt.Unchecked)
            if is_geo_dataset_downloaded(dataset_id, self.options.geog_dir):
                item.setFlags(Qt.NoItemFlags)
                item.setToolTip(0, 'Dataset downloaded in: {}'.format(
                    get_geo_dataset_path(dataset_id, self.options.geog_dir)))
            else:
                item.setToolTip(0, dataset_id)

            if isinstance(resolution, str):
                item.setText(1, resolution)
            else:
                item.setText(1, formatted_dd_to_dms(resolution))
                item.setToolTip(1, '{}°'.format(resolution))

            item.setText(2, description)
            item.setToolTip(2, description)

    def on_select_mandatory_lores_button_clicked(self):
        self.select_datasets(geo_datasets_mandatory_lores)

    def on_select_mandatory_hires_button_clicked(self):
        self.select_datasets(geo_datasets_mandatory_hires)

    def select_datasets(self, names: List[str]) -> None:
        items = self.get_items()
        for name, item in items.items():
            item.setCheckState(0, Qt.Checked if name in names else Qt.Unchecked)

    def get_items(self) -> Dict[str,QTreeWidgetItem]:
        items = {} # type: Dict[str,QTreeWidgetItem]
        for index in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(index)
            items[item.data(0, Qt.UserRole)] = item
        return items

    def on_download_button_clicked(self) -> None:
        datasets_to_download = []
        for name, item in self.get_items().items():
            if item.checkState(0) == Qt.Checked:
                datasets_to_download.append(name)

        thread = TaskThread(lambda: self.download_datasets(datasets_to_download), yields_progress=True)
        thread.started.connect(self.on_started_download)
        thread.progress.connect(self.on_progress_download)
        thread.finished.connect(self.on_finished_download)
        thread.succeeded.connect(self.on_successful_download)
        thread.failed.connect(reraise)
        thread.start()

    def on_started_download(self):
        self.download_button.hide()
        self.progress_bar.show()
        self.tree_widget.setEnabled(False)

    def on_progress_download(self, progress: float, status: str) -> None:
        bar_value = int(progress * PROGRESS_BAR_MAX)
        self.progress_bar.setValue(bar_value)
        self.progress_bar.repaint() # otherwise just updates in 1% steps
        logger.debug(f'Geo data download: {progress*100:.1f}% - {status}')

    def on_finished_download(self) -> None:
        self.download_button.show()
        self.progress_bar.hide()
        self.tree_widget.setEnabled(True)
        self.tree_widget.clear()
        self.populate_tree()
        Broadcast.geo_datasets_updated.emit()

    def on_successful_download(self) -> None:
        self.msg_bar.success('Geographical datasets downloaded successfully.')

    def download_datasets(self, dataset_names: List[str]) -> Iterable[Tuple[float,str]]:
        yield 0.0, 'selected: ' + ', '.join(dataset_names)
        for i, name in enumerate(dataset_names):
            for dataset_progress in download_and_extract_geo_dataset(name, self.options.geog_dir):
                total_progress = (i + dataset_progress) / len(dataset_names)
                yield total_progress, f'downloading {name} ({dataset_progress*100:.1f}%)'

