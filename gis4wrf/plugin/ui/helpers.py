# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Union, Optional, Tuple, List, Callable
import os
import signal
import sys
import platform
import shutil
from pathlib import Path

from PyQt5.QtCore import QLocale, QObject, QThread, QUrl, Qt, pyqtSignal
from PyQt5.QtGui import (
    QGuiApplication, QPalette, QDoubleValidator, QValidator, QIntValidator,
    QDesktopServices
)

from PyQt5.QtWidgets import (
    QWidget, QLabel, QLayout, QHBoxLayout, QVBoxLayout, QGridLayout, QComboBox, QMessageBox,
    QScrollArea, QLineEdit, QPushButton, QGroupBox, QRadioButton, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QSizePolicy, QDialog, QProgressBar, QToolButton, QAction
)

from qgis.gui import QgisInterface
from qgis.core import QgsApplication, QgsMapLayer

# NOTE: Do not import anything from gis4wrf.core or other gis4wrf.plugin module depending on core here.
#       The helpers module is used in the bootstrapping UI.

from gis4wrf.plugin.constants import PLUGIN_NAME


DIM_VALIDATOR = QIntValidator()
DIM_VALIDATOR.setBottom(0)
RATIO_VALIDATOR = QIntValidator()
RATIO_VALIDATOR.setBottom(1)
THIS_DIR = Path(__file__)

class StringValidator(QValidator):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def validate(self, s, pos):
        if self.callback(s):
            return QValidator.Acceptable, s, pos
        else:
            return QValidator.Intermediate, s, pos 

class MyLineEdit(QLineEdit):
    def __init__(self, required=False) -> None:
        super().__init__()
        self.required = required

    def value(self) -> Union[int,float,str]:
        if isinstance(self.validator(), QDoubleValidator):
            return QLocale().toDouble(self.text())[0]
        elif isinstance(self.validator(), QIntValidator):
            return QLocale().toInt(self.text())[0]
        elif isinstance(self.validator(), StringValidator):
            return self.text()
        else:
            raise NotImplementedError

    def set_value(self, value: Union[int,float,str]) -> None:
        if isinstance(value, str):
            self.setText(value)
        else:
            # QLocale to handle dot vs comma
            self.setText(QLocale().toString(value))

    def is_valid(self) -> bool:
        state = self.validator().validate(self.text(), 0)[0]
        return state == QValidator.Acceptable

class WhiteScroll(QScrollArea):
    def __init__(self, widget: QWidget) -> None:
        super().__init__()
        self.setBackgroundRole(QPalette.Light)
        self.setWidgetResizable(True)
        self.setWidget(widget)


class MessageBar(object):
    def __init__(self, iface: QgisInterface) -> None:
        self.msg_bar = iface.messageBar() # type: QgsMessageBar

    def info(self, msg: str) -> None:
        self.msg_bar.pushInfo(PLUGIN_NAME, msg)

    def success(self, msg: str) -> None:
        self.msg_bar.pushSuccess(PLUGIN_NAME, msg)

    def warning(self, msg: str) -> None:
        self.msg_bar.pushWarning(PLUGIN_NAME, msg)

    def error(self, msg: str) -> None:
        self.msg_bar.pushCritical(PLUGIN_NAME, msg)
    

def update_input_validation_style(widget: MyLineEdit) -> None:
    """Updates the background color of a line edit.
    Source: https://snorfalorpagus.net/blog/2014/08/09/validating-user-input-in-pyqt4-using-qvalidator/
    """
    green = '#c4df9b'
    yellow = '#fff79a'
    red = '#f6989d'

    required = widget.required

    if widget.is_valid():
        color = green
    elif not widget.text():
        if required:
            color = yellow
        else:
            color = ''
    else:
        color = red
    widget.setStyleSheet('QLineEdit { background-color: %s }' % color)

def create_lineedit(validator: QValidator, required: bool=False) -> MyLineEdit:
    """Helper to return a 'validator-ready' line edit."""
    lineedit = MyLineEdit(required)
    lineedit.setValidator(validator)
    lineedit.textChanged.connect(lambda _: update_input_validation_style(lineedit))
    lineedit.textChanged.emit(lineedit.text())
    return lineedit

def add_grid_lineedit(grid: QGridLayout, row: int, label_name: str, validator: Optional[QValidator],
                      unit: Optional[str]=None, required: bool=False) -> QLineEdit:
    """Helper to return a 'validator-ready' grid layout
    composed of a name label, line edit and optional unit.
    """
    lineedit = create_lineedit(validator, required)
    add_grid_labeled_widget(grid, row, label_name, lineedit)
    if unit:
        grid.addWidget(QLabel(unit), row, 2)
    return lineedit

def add_grid_combobox(grid: QGridLayout, row: int, label_name: str) -> QComboBox:
    """Helper to return a 'validator-ready' grid layout
    composed of a name label, line edit and optional unit.
    """
    combo = QComboBox()
    add_grid_labeled_widget(grid, row, label_name, combo)
    return combo

def add_grid_labeled_widget(grid: QGridLayout, row: int, label_name: str, widget: Union[QWidget,QLayout]) -> None:
    grid.addWidget(QLabel(label_name + ':'), row, 0)
    if isinstance(widget, QWidget):
        grid.addWidget(widget, row, 1)
    else:
        grid.addLayout(widget, row, 1)

def create_file_input(start_folder: str, dialog_caption: Optional[str]=None, input_label: Optional[str]=None, is_folder=False, value: Optional[str]=None) -> Tuple[QLineEdit, QHBoxLayout]:
    hbox = QHBoxLayout()

    if value is None:
        value = ''
    field = QLineEdit(value)

    button = QToolButton()
    tooltip_suffix = 'Folder' if is_folder else 'File'
    action = QAction(QgsApplication.getThemeIcon('/mActionFileOpen.svg'), 'Choose ' + tooltip_suffix)
    button.setDefaultAction(action)

    if dialog_caption is None and input_label:
        dialog_caption = 'Select ' + input_label

    def on_button_triggered():
        if is_folder:
            path = QFileDialog.getExistingDirectory(caption=dialog_caption, directory=start_folder)
        else:
            path, _ = QFileDialog.getOpenFileName(caption=dialog_caption, directory=start_folder)
        if not path:
            return
        field.setText(path)

    button.triggered.connect(on_button_triggered)

    if input_label:
        hbox.addWidget(QLabel(input_label))
    hbox.addWidget(field)
    hbox.addWidget(button)

    return field, hbox

def create_two_radio_group_box(radio1_name: str, radio2_name: str,
                               gbox_name: str) -> QGroupBox:
    radio1 = QRadioButton(radio1_name)
    radio2 = QRadioButton(radio2_name)
    vbox = QVBoxLayout()
    vbox.addWidget(radio1)
    vbox.addWidget(radio2)
    group_box = QGroupBox(gbox_name)
    group_box.setLayout(vbox)
    return group_box

def ensure_folder_empty(folder: str, iface: QgisInterface) -> bool:
    existing_files = os.listdir(folder)
    if not existing_files:
        return True
    reply = QMessageBox.question(iface.mainWindow(), 'Existing files',
            'The folder {} is not empty and its contents will be removed.'.format(folder),
            QMessageBox.Ok, QMessageBox.Cancel)
    if reply == QMessageBox.Cancel:
        return False
    for filename in existing_files:
        path = os.path.join(folder, filename)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.unlink(path)
    return True

# https://stackoverflow.com/a/9383780
def clear_layout(layout: QLayout) -> None:
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        else:
            clear_layout(item.layout())

def dispose_after_delete(layer: QgsMapLayer, dispose: Callable[[],None]) -> None:
    # Lazy import to work around restriction explained at top of this file.
    from gis4wrf.plugin.ui.thread import TaskThread

    # There is no signal indicating that the layer has been fully removed.
    # Therefore in the willBeDeleted signal we need to give control back to
    # the main event loop and run the dispose operation asynchronously. Note that
    # the dispose function cleans temporary files and retries a few times if file locks are still in place.
    def on_delete():
        thread = TaskThread(dispose)
        thread.failed.connect(reraise)
        thread.start()
    layer.willBeDeleted.connect(on_delete)

class IgnoreKeyPressesDialog(QDialog):
    def keyPressEvent(self, e) -> None:
        # By default, pressing Escape "rejects" the dialog
        # and Enter "accepts" the dialog, closing it in both cases.
        # Overriding this method prevents this behaviour.
        pass

# higher resolution than default (100)
PROGRESS_BAR_MAX = 1000

class WaitDialog(IgnoreKeyPressesDialog):
    def __init__(self, parent, title, progress=False) -> None:
        super().__init__(parent, Qt.WindowTitleHint)
        vbox = QVBoxLayout()
        self.progress_bar = QProgressBar()
        max_val = PROGRESS_BAR_MAX if progress else 0
        self.progress_bar.setRange(0, max_val)
        self.progress_bar.setTextVisible(False)
        vbox.addWidget(self.progress_bar)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setLayout(vbox)
        self.setMaximumHeight(0)
        self.setFixedWidth(parent.width() // 2)
        self.show()
    
    def update_progress(self, progress: float) -> None:
        self.progress_bar.setValue(int(progress * PROGRESS_BAR_MAX))
        self.progress_bar.repaint() # otherwise just updates in 1% steps

def install_user_error_handler(iface: QgisInterface) -> None:
    # Lazy import to work around restriction explained at top of this file.
    from gis4wrf.core import UserError, UnsupportedError, DistributionError

    # The most-specific one is used when handling a user error.
    formatters = {
        UnsupportedError: lambda e: (
            f'<html>{e}. Interested in making GIS4WRF better? ' +
             'Consider <a href="https://github.com/GIS4WRF/gis4wrf#contributing">contributing</a> code ' +
             'or adding a <a href="https://github.com/GIS4WRF/gis4wrf/issues">feature request</a>.</html>',
            'Unsupported feature', QMessageBox.information),
        
        DistributionError: lambda e: (
            f'<html>There is a problem with your {e.dist_name} distribution: {e}. ' +
             'If you need help with the configuration, have a look at the ' +
             '<a href="https://gis4wrf.github.io/configuration/">online documentation</a>.</html>',
            'Error', QMessageBox.critical),

        UserError: lambda e: (
            f'{e}.',
            'Error', QMessageBox.critical)
    }

    old = sys.excepthook

    def handle_user_error(etype, value, traceback):
        if not isinstance(value, UserError):
            old(etype, value, traceback)
            return
        for clazz in etype.mro():
            if clazz in formatters:
                break
        msg, title, fn = formatters[clazz](value)
        fn(iface.mainWindow(), f'{PLUGIN_NAME} - {title}', msg)

    sys.excepthook = handle_user_error

def reraise(exc_info) -> None:
    raise exc_info[0].with_traceback(*exc_info[1:])
