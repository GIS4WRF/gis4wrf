# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from pathlib import Path


from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QPixmap
from gis4wrf.plugin.ui.helpers import FormattedLabel
from gis4wrf.plugin.constants import GIS4WRF_LOGO_PATH

class HomeTab(QWidget):
    """Class for creating the Home tab"""

    def __init__(self) -> None:
        super().__init__()
        vbox = QVBoxLayout()
        title = """
                    <html>
                        <h1>Welcome to GIS4WRF</h1>
                        <br>
                    </html>
                """
        text = """
                    <html>
                        <font size="4">
                        <br>
                        <p>The GIS4WRF documentation and tutorials have been moved online at: <a href="https://gis4wrf.github.io">https://gis4wrf.github.io</a></p>
                        <br>
                        <p>We are delighted to announce that we can now provide MPI-enabled WPS-V4 and WRF-V4 pre-built binaries for Windows, macOS and Linux through WRF-CMake. 😊</p>
                        <p>If you have not done so already, make sure to download the latest V4 releases for your system.
                            For more info see: <a href="https://gis4wrf.github.io/configuration">https://gis4wrf.github.io/configuration</a></p>
                        <br>
                        <p>Make sure to check out all the new features with this version under <code>GIS4WRF</code> > <code>About</code> > <code>What's new</code></p>
                        </font>
                  </html>
               """

        label_title = FormattedLabel(title, align=True)
        label = FormattedLabel(text, align=True)
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)
        label2 = QLabel()
        pixmap = QPixmap(GIS4WRF_LOGO_PATH)
        label2.setPixmap(pixmap)
        label2.setAlignment(Qt.AlignCenter)
        vbox.addWidget(label_title)
        vbox.addWidget(label2)
        vbox.addWidget(label)
        vbox.addStretch()
        self.setLayout(vbox)
