# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Tuple, Callable
import os
import platform
import multiprocessing
import subprocess
import webbrowser

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import ( 
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QGroupBox,
    QCheckBox, QPushButton, QSpinBox, QMessageBox, QSizePolicy
)

from qgis.gui import QgsOptionsWidgetFactory, QgsOptionsPageWidget

from gis4wrf.core import get_wps_dist_url, get_wrf_dist_url, download_and_extract_dist, WRF_WPS_DIST_VERSION
from gis4wrf.core.util import export
from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.constants import PLUGIN_NAME, GIS4WRF_LOGO_PATH, MSMPI_DOWNLOAD_PAGE
from gis4wrf.plugin.ui.helpers import WaitDialog, create_file_input, reraise, wrap_error
from gis4wrf.plugin.ui.thread import TaskThread

@export
class OptionsFactory(QgsOptionsWidgetFactory):
    def __init__(self):
        super().__init__()
        self.setTitle(PLUGIN_NAME)

    def icon(self):
        return QIcon(GIS4WRF_LOGO_PATH)

    def createWidget(self, parent):
        return ConfigOptionsPage(parent)

class ConfigOptionsPage(QgsOptionsPageWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.options = get_options()

        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.working_dir, layout = create_file_input(
            is_folder=True, input_label='Working directory',
            value=self.options.working_dir, start_folder=self.options.working_dir)
        self.vbox.addLayout(layout)

        self.mpi_enabled, self.mpi_processes, self.wps_dir, self.wrf_dir, gbox = \
            self.create_distribution_box()
        self.vbox.addWidget(gbox)

        self.rda_username, self.rda_password, gbox = self.create_rda_auth_input()
        self.vbox.addWidget(gbox)

        self.vbox.addStretch()

    def apply(self) -> None:
        ''' Called when the options dialog is accepted. '''
        self.options.working_dir = self.working_dir.text()
        self.options.mpi_enabled = self.mpi_enabled.isChecked()
        self.options.mpi_processes = self.mpi_processes.value()
        self.options.wrf_dir = self.wrf_dir.text()
        self.options.wps_dir = self.wps_dir.text()
        self.options.rda_username = self.rda_username.text()
        self.options.rda_password = self.rda_password.text()

    def create_distribution_box(self) -> Tuple[QCheckBox, QSpinBox, QLineEdit, QLineEdit, QGroupBox]:
        gbox = QGroupBox('WPS/WRF Distribution')
        vbox = QVBoxLayout()
        gbox.setLayout(vbox)

        text = """<html>GIS4WRF allows you to run WPS and WRF on your local system.
                  If you have an existing compilation of WPS and/or WRF then simply choose
                  the corresponding folders below. If you compiled with <code>dmpar</code> make sure
                  to tick the "MPI" checkbox. Alternatively, you can download pre-compiled
                  distributions by clicking on the buttons below. Note that pre-compiled
                  distributions are only available with basic nesting support.
                  </html>"""
        label = QLabel(text)
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)
        vbox.addWidget(label)

        hbox = QHBoxLayout()
        mpi_enabled = QCheckBox('MPI')
        mpi_enabled.setChecked(self.options.mpi_enabled)
        mpi_enabled.clicked.connect(self.on_mpi_enabled_clicked)
        hbox.addWidget(mpi_enabled)
        mpi_processes = QSpinBox()
        mpi_processes.setRange(1, multiprocessing.cpu_count())
        mpi_processes.setValue(self.options.mpi_processes)
        mpi_processes.setFixedWidth(70)
        hbox.addWidget(mpi_processes)
        mpi_processes_lbl = QLabel('MPI Processes')
        hbox.addWidget(mpi_processes_lbl)
        vbox.addLayout(hbox)

        wps_dir, hbox = create_file_input(input_label='WPS directory',
            is_folder=True, start_folder=self.options.distributions_dir, value=self.options.wps_dir)
        vbox.addLayout(hbox)

        wrf_dir, hbox = create_file_input(input_label='WRF directory',
            is_folder=True, start_folder=self.options.distributions_dir, value=self.options.wrf_dir)
        vbox.addLayout(hbox)

        hbox = QHBoxLayout()
        download_wps = QPushButton('Download Pre-Compiled WPS Distribution...')
        download_wrf = QPushButton('Download Pre-Compiled WRF Distribution...')
        download_wps.clicked.connect(self.download_wps)
        download_wrf.clicked.connect(self.download_wrf)
        hbox.addWidget(download_wps)
        hbox.addWidget(download_wrf)
        hbox.addStretch()
        vbox.addLayout(hbox)

        return mpi_enabled, mpi_processes, wps_dir, wrf_dir, gbox

    def create_rda_auth_input(self) -> Tuple[QLineEdit, QLineEdit, QGroupBox]:
        username = QLineEdit(self.options.rda_username)
        password = QLineEdit(self.options.rda_password)
        password.setEchoMode(QLineEdit.Password)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Username: '))
        hbox.addWidget(username)
        hbox.addWidget(QLabel('Password: '))
        hbox.addWidget(password)

        gbox = QGroupBox("NCAR's Research Data Archive (RDA)")
        text = """<html>GIS4WRF allows you to download datasets from
                <a href="https://rda.ucar.edu/">NCAR's Reseach Data Archive (RDA)</a>
                through the use of its API. If you do not have an RDA account, you need to
                <a href="https://rda.ucar.edu/index.html?hash=data_user&amp;action=register">register for a Data Account</a> first.
                Once you have completed your registration and your account is live you can save your log-in information to download meteorological
                data from GIS4WRF > Datasets > Met.</html>"""
        label = QLabel(text)
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)
        vbox = QVBoxLayout()
        vbox.addWidget(label)
        vbox.addLayout(hbox)
        gbox.setLayout(vbox)

        return username, password, gbox

    def on_mpi_enabled_clicked(self) -> None:
        if not self.mpi_enabled.isChecked():
            return
        
        plat = platform.system()

        if plat == 'Windows':
            has_msmpi = os.environ.get('MSMPI_BIN')
            if not has_msmpi:
                self.mpi_enabled.setChecked(False)
                reply = QMessageBox.question(
                    self, 'Microsoft MPI not found',
                    'Microsoft MPI is not installed on your system. ' +
                    'Do you want to be redirected to the download page? ' +
                    'Note that QGIS must be restarted after the installation.',
                    QMessageBox.Yes, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    webbrowser.open(MSMPI_DOWNLOAD_PAGE)
        elif plat in ['Darwin', 'Linux']:
            try: 
                if plat == 'Linux':
                    subprocess.check_output(['mpiexec', '-h'])
                else: # Darwin # FIXME: momentarily hardcode path
                    subprocess.check_output(['/usr/local/bin/mpiexec', '-h'])
            except FileNotFoundError:
                self.mpi_enabled.setChecked(False)
                if plat == 'Linux':
                    extra = 'For Debian/Ubuntu, run "sudo apt install mpich".'
                else: # Darwin
                    extra = 'If you use Homebrew, run "brew install mpich".'
                QMessageBox.critical(self, 'MPICH not found',
                    'MPICH does not seem to be installed on your system. ' + extra)
        else:
            self.mpi_enabled.setChecked(False)
            QMessageBox.critical(self, 'Unsupported platform',
                PLUGIN_NAME + ' does not support MPI on ' + plat)

    def download_wps(self) -> None:
        mpi = self.mpi_enabled.isChecked()
        url = wrap_error(self, lambda: get_wps_dist_url(mpi))
        if not url:
            return

        self.download_dist('WPS', mpi, url, on_success=lambda folder: self.wps_dir.setText(folder))

    def download_wrf(self) -> None:
        mpi = self.mpi_enabled.isChecked()
        url = wrap_error(self, lambda: get_wrf_dist_url(mpi))
        if not url:
            return

        self.download_dist('WRF', mpi, url, on_success=lambda folder: self.wrf_dir.setText(folder))

    def download_dist(self, name: str, mpi: bool, url: str, on_success: Callable[[str],None]) -> None:
        mpi = self.mpi_enabled.isChecked()
        # TODO check if mpiexec/mpirun etc is installed and if not prompt user to install it

        if not self.confirm_dist_download(name, mpi, url):
            return

        wait_dialog = WaitDialog(self, 'Downloading...')
                
        folder = self.get_dist_download_folder(name, mpi)
        thread = TaskThread(lambda: download_and_extract_dist(url, folder))
        thread.finished.connect(lambda: wait_dialog.accept())
        thread.succeeded.connect(lambda: on_success(folder))
        thread.failed.connect(reraise)
        thread.start()

    def confirm_dist_download(self, name: str, mpi: bool, url: str) -> bool:
        reply = QMessageBox.question(self, 'Confirm Download',
            'You are about to download a pre-compiled distribution of {} {} in {} mode.\n\nURL: {}'.format(
                name, WRF_WPS_DIST_VERSION, 'MPI' if mpi else 'non-MPI', url),
            QMessageBox.Ok, QMessageBox.Cancel)
        return reply == QMessageBox.Ok

    def get_dist_download_folder(self, name: str, mpi: bool) -> str:
        return os.path.join(self.options.distributions_dir, 
                            '{}-{}-{}'.format(name, WRF_WPS_DIST_VERSION, ('' if mpi else 'no') + 'mpi'))
