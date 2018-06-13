# GIS4WRF (https://doi.org/10.5281/zenodo.1288524)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Union, Optional, List, Callable
import os
import sys
import shutil
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl, QLocale, pyqtSlot, QThread, pyqtSignal
from PyQt5.QtGui import QPalette, QDoubleValidator, QValidator, QIntValidator
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLayout, QHBoxLayout, QVBoxLayout, QGridLayout, QComboBox, QMessageBox,
    QScrollArea, QLineEdit, QPushButton, QGroupBox, QRadioButton, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QSizePolicy, QDialog, QProgressBar
)

# TODO: QWebView is deprecated. We should use QWebEngineView instead.
#       Currently not possible due to a bug in QGIS (https://issues.qgis.org/issues/18155).
from PyQt5.QtWebKitWidgets import QWebView
# from PyQt5.QtWebEngineWidgets import QWebEngineView

from qgis.gui import QgsMessageBar, QgisInterface
from qgis.core import QgsMapLayer

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

class FormattedLabel(QLabel):
    def __init__(self, text: QLabel, align: bool=False) -> None:
        super().__init__()
        self.setText(text)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if align:
            self.setWordWrap(True)
            self.setAlignment(Qt.AlignJustify | Qt.AlignTop)

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
    grid.addWidget(QLabel(label_name + ':'), row, 0)
    lineedit = create_lineedit(validator, required)
    grid.addWidget(lineedit, row, 1)
    if unit:
        grid.addWidget(QLabel(unit), row, 2)
    return lineedit

def add_grid_combobox(grid: QGridLayout, row: int, label_name: str) -> QComboBox:
    """Helper to return a 'validator-ready' grid layout
    composed of a name label, line edit and optional unit.
    """
    grid.addWidget(QLabel(label_name + ':'), row, 0)
    combo = QComboBox()
    grid.addWidget(combo, row, 1)
    return combo

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

class RadioWithButtonWidget(QGroupBox):
    def __init__(self) -> None:
        super().__init__('Data Selector')

        self.radio_list = [] # type: list

    def add_radio(self, radio_button_name: str) -> list:
        self.radio_list.append(radio_button_name)
        return self.radio_list

    def create_layout(self):
        vbox = QVBoxLayout()
        for radio_button in self.radio_list:
            self.radio_button = QRadioButton(radio_button)
            self.radio_button.toggled.connect(lambda:self.radiostate(self.radio_button))
            vbox.addWidget(self.radio_button)
        self.setLayout(vbox)

    def radiostate(self,b):
        for radio_button in radio_list:
            print(self.radio_button.text())


# TODO: implement use remote url if internet connection is
# available, else default to the local page
def create_browser_layout(web_page: str) -> QVBoxLayout:
    path = THIS_DIR.parents[1] / 'resources' / 'meta' / 'site' / web_page
    url = QUrl(path.as_uri())
    vbox = QVBoxLayout()
    vbox.setContentsMargins(2,2,2,2)
    browser = QWebView()
    browser.load(url)
    browser.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
    vbox.addWidget(browser)
    return vbox


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

def wrap_error(parent, fn):
    try:
        return fn()
    except Exception as e:
        QMessageBox.critical(parent, PLUGIN_NAME, str(e))
        return

def dispose_after_delete(layer: QgsMapLayer, dispose: Callable[[],None]) -> None:
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

class WaitDialog(IgnoreKeyPressesDialog):
    def __init__(self, parent, title):
        super().__init__(parent, Qt.WindowTitleHint)
        vbox = QVBoxLayout()
        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setTextVisible(False)
        vbox.addWidget(bar)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setLayout(vbox)
        self.setMaximumHeight(0)
        self.setFixedWidth(parent.width() * 0.5)
        self.show()

_THREADS = [] # type: List[QThread]

class TaskThread(QThread):
    progress = pyqtSignal(int, str)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(tuple)

    def __init__(self, fn, yields_progress: bool=False) -> None:
        super().__init__()
        self.fn = fn
        self.yields_progress = yields_progress
        self.result = None
        self.exc_info = None

        # need to keep reference alive while thread is running
        _THREADS.append(self)

    def run(self):
        try:
            if self.yields_progress:
                for percent, status in self.fn():
                    self.progress.emit(percent, status)
            else:
                self.result = self.fn()
            self.succeeded.emit(self.result)
        except:
            self.exc_info = sys.exc_info()
            self.failed.emit(self.exc_info)

def reraise(exc_info) -> None:
    raise exc_info[0].with_traceback(*exc_info[1:])
