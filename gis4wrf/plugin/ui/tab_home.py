# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from PyQt5.QtWidgets import QWidget
from pathlib import Path

from gis4wrf.plugin.ui.helpers import create_browser_layout


class HomeTab(QWidget):
    """Class for creating the Home tab"""

    def __init__(self) -> None:
        super().__init__()
        page = Path('tab_home', 'index.html')
        self.setLayout(create_browser_layout(page))
