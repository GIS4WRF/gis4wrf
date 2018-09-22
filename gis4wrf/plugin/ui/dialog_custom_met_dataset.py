# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List, Set, Optional
import os
from pathlib import Path
from datetime import datetime

from PyQt5.QtCore import Qt, QDate, QTime, QDateTime

from PyQt5.QtGui import (
    QIntValidator, QGuiApplication
)
from PyQt5.QtWidgets import (
    QPushButton, QVBoxLayout, QDialog, QGridLayout,
    QHBoxLayout, QFileDialog, QDialogButtonBox, QListWidget, QListWidgetItem,
    QAbstractItemView, QDateTimeEdit, QLabel
)

from gis4wrf.core import UserError, UnsupportedError
from gis4wrf.plugin.ui.helpers import add_grid_lineedit, add_grid_combobox, add_grid_labeled_widget, create_file_input


class CustomMetDatasetDialog(QDialog):
    def __init__(self, vtable_dir: str, spec: Optional[dict]=None) -> None:
        super().__init__()

        self.vtable_dir = vtable_dir
        self.paths = set() # type: Set[Path]

        geom = QGuiApplication.primaryScreen().geometry()
        w, h = geom.width(), geom.height()
        self.setWindowTitle("Custom Meteorological Dataset")
        self.setMinimumSize(w * 0.25, h * 0.35)

        layout = QVBoxLayout()

        # button to open folder/files dialog
        hbox = QHBoxLayout()
        layout.addLayout(hbox)
        add_folder_btn = QPushButton('Add folder')
        add_files_btn = QPushButton('Add files')
        remove_selected_btn = QPushButton('Remove selected')
        hbox.addWidget(add_folder_btn)
        hbox.addWidget(add_files_btn)
        hbox.addWidget(remove_selected_btn)
        add_folder_btn.clicked.connect(self.on_add_folder_btn_clicked)
        add_files_btn.clicked.connect(self.on_add_files_btn_clicked)
        remove_selected_btn.clicked.connect(self.on_remove_selected_btn_clicked)

        # show added files in a list
        self.paths_list = QListWidget()
        self.paths_list.setSelectionMode(QAbstractItemView.ContiguousSelection)
        layout.addWidget(self.paths_list)

        grid = QGridLayout()
        layout.addLayout(grid)

        # date/time start/end
        self.start_date_input = QDateTimeEdit()
        self.start_date_input.setCalendarPopup(True)

        self.end_date_input = QDateTimeEdit()
        self.end_date_input.setCalendarPopup(True)
        
        add_grid_labeled_widget(grid, 0, 'Start Date/Time', self.start_date_input)
        add_grid_labeled_widget(grid, 1, 'End Date/Time', self.end_date_input)

        # interval in seconds
        interval_validator = QIntValidator()
        interval_validator.setBottom(1)
        self.interval_input = add_grid_lineedit(grid, 2, 'Interval in seconds', interval_validator, required=True)   

        # vtable file input
        self.vtable_input, vtable_hbox = create_file_input(dialog_caption='Select VTable file',
            is_folder=False, start_folder=vtable_dir)
        add_grid_labeled_widget(grid, 3, 'VTable', vtable_hbox)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.on_ok_clicked)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
        self.setLayout(layout)

        if spec:
            self.paths = set(map(Path, spec['paths']))
            self.base_folder = spec['base_folder']
            self.update_file_list()

            start_date, end_date = spec['time_range']
            for date_input, date in [(self.start_date_input, start_date), (self.end_date_input, end_date)]:
                date_input.setDateTime(QDateTime(QDate(date.year, date.month, date.day), QTime(date.hour, date.minute)))

            self.interval_input.set_value(spec['interval_seconds'])

            self.vtable_input.setText(spec['vtable'])

    @property
    def start_date(self) -> datetime:
        return self.start_date_input.dateTime().toPyDateTime()

    @property
    def end_date(self) -> datetime:
        return self.end_date_input.dateTime().toPyDateTime()

    @property
    def interval_seconds(self) -> int:
        return self.interval_input.value()

    @property
    def vtable_path(self) -> str:
        return self.vtable_input.text()

    def on_ok_clicked(self) -> None:
        if not self.paths:
            raise UserError('No GRIB files were added')
        if not self.interval_input.is_valid():
            raise UserError('Interval must be an integer above 0')
        if self.start_date == self.end_date:
            raise UserError('Start date cannot be the same as end date')
        if self.start_date > self.end_date:
            raise UserError('Start date cannot be after the end date')
        if not self.vtable_path:
            raise UserError('No VTable file selected')
        if not os.path.exists(os.path.join(self.vtable_dir, self.vtable_path)):
            raise UserError('VTable file does not exist')
        self.accept()

    def on_add_folder_btn_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(caption='Select folder')
        if not folder:
            return
        paths = [] # type: List[Path]
        for root, _, filenames in os.walk(folder):
            paths.extend(Path(root) / filename for filename in filenames)
        self.update_paths(self.paths.union(paths))
        self.update_file_list()
    
    def on_add_files_btn_clicked(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(caption='Select files')
        if not paths:
            return

        self.update_paths(self.paths.union(map(Path, paths)))
        self.update_file_list()

    def on_remove_selected_btn_clicked(self) -> None:
        paths = [item.data(Qt.UserRole) for item in self.paths_list.selectedItems()]
        self.update_paths(self.paths.difference(paths))
        self.update_file_list()

    def update_paths(self, paths: Set[Path]) -> None:
        if len(paths) == 1:
            # special case as os.path.commonpath() would return '.'
            base_folder = os.path.dirname(list(paths)[0])
        elif paths:
            try:
                base_folder = os.path.commonpath(paths)
            except ValueError:
                raise UnsupportedError('Only datasets with files located on the same drive are supported')
        else:
            base_folder = None

        self.base_folder = base_folder
        self.paths = paths

    def update_file_list(self) -> None:
        self.paths_list.clear()
        for path in sorted(self.paths):
            item = QListWidgetItem(str(path))
            item.setData(Qt.UserRole, path)
            self.paths_list.addItem(item)

