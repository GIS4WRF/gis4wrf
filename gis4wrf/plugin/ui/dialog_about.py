# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Optional, Tuple, List, Callable, Union, Iterable
from io import StringIO
import os
import sys
import glob
import subprocess
import threading
from pathlib import Path

from PyQt5.QtCore import QMetaObject, Qt, QLocale, pyqtSlot, pyqtSignal, QModelIndex, QThread
from PyQt5.QtGui import (
    QDoubleValidator, QIntValidator, QPalette, QGuiApplication, QTextOption, QSyntaxHighlighter,
    QTextCharFormat, QColor, QFont
)
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLayout, QVBoxLayout, QDialog, QGridLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QComboBox, QScrollArea, QFileDialog, QRadioButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView, QPlainTextEdit, QSizePolicy,
    QDialogButtonBox, QMessageBox, QTextBrowser
)

from qgis.gui import QgisInterface

from gis4wrf.core import Project, read_namelist, verify_namelist

from gis4wrf.plugin.constants import PLUGIN_NAME
from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.ui.helpers import MessageBar

ROOT_DIR = Path(__file__).parents[2]
CHANGELOG_PATH = ROOT_DIR.joinpath('CHANGELOG.txt')
CREDITS_PATH = ROOT_DIR.joinpath('ATTRIBUTION.txt')
LICENSE_PATH = ROOT_DIR.joinpath('LICENSE.txt')

class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()

        geom = QGuiApplication.primaryScreen().geometry()
        w, h = geom.width(), geom.height()
        self.setWindowTitle("About")
        self.setMinimumSize(w * 0.3, h * 0.5)
        
        with open(CHANGELOG_PATH) as f:
            changelog = f.read()
        text_changelog = QTextBrowser()
        text_changelog.setPlainText(changelog)

        with open(CREDITS_PATH) as f:
            credits = f.read()
        text_credits = QTextBrowser()
        text_credits.setPlainText(credits)

        with open(LICENSE_PATH) as f:
            credits = f.read()
        text_license = QTextBrowser()
        text_license.setPlainText(credits)

        text_how_to_cite = QTextBrowser()
        text_how_to_cite.setOpenExternalLinks(True)
        how_to_cite = "Please see <a href='https://zenodo.org/'>GIS4WRF on Zenodo</a> \
                       for up-to-date referencing information."
        text_how_to_cite.setText(how_to_cite)

        tabs = QTabWidget()
        tabs.addTab(text_changelog,"What's New")
        tabs.addTab(text_credits,'Credits')
        tabs.addTab(text_license, 'License')
        tabs.addTab(text_how_to_cite, 'How to Cite')
        
        vbox = QVBoxLayout()
        vbox.addWidget(tabs)
        self.setLayout(vbox)