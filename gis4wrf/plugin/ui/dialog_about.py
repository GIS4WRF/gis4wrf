# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from pathlib import Path

from PyQt5.QtGui import (
    QDoubleValidator, QIntValidator, QPalette, QGuiApplication, QTextOption, QSyntaxHighlighter,
    QTextCharFormat, QColor, QFont
)
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLayout, QVBoxLayout, QDialog, QGridLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QComboBox, QScrollArea, QFileDialog, QRadioButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView, QPlainTextEdit, QSizePolicy,
    QDialogButtonBox, QTextBrowser
)




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
        self.setMinimumSize(w // 2, h // 2)
        font = QFont('Monospace', 9)
        font.setStyleHint(QFont.TypeWriter)
        
        with open(CHANGELOG_PATH) as f:
            changelog = f.read()
        text_changelog = QTextBrowser()
        text_changelog.setFont(font)
        text_changelog.setPlainText(changelog)

        text_how_to_cite = QTextBrowser()
        text_how_to_cite.setOpenExternalLinks(True)
        how_to_cite = "Please see <a href='https://gis4wrf.github.io/cite'>How to reference GIS4WRF</a> \
                       for up-to-date referencing information."
        text_how_to_cite.setFont(font)
        text_how_to_cite.setText(how_to_cite)

        with open(CREDITS_PATH) as f:
            credits = f.read()
        text_credits = QTextBrowser()
        text_credits.setFont(font)
        text_credits.setPlainText(credits)

        with open(LICENSE_PATH) as f:
            license = f.read()
        text_license = QTextBrowser()
        text_license.setFont(font)
        text_license.setPlainText(license)

        tabs = QTabWidget()
        tabs.addTab(text_changelog,"What's new")
        tabs.addTab(text_how_to_cite, 'How to reference GIS4WRF')
        tabs.addTab(text_credits,'Credits')
        tabs.addTab(text_license, 'License')
        
        vbox = QVBoxLayout()
        vbox.addWidget(tabs)
        self.setLayout(vbox)