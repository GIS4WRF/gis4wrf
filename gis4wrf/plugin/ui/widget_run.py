# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Optional, Tuple, List, Callable, Union, Iterable, Any
from io import StringIO
import os

from PyQt5.QtCore import (
    QMetaObject, Qt, QLocale, pyqtSlot, pyqtSignal, QModelIndex, QThread
)
from PyQt5.QtGui import (
    QDoubleValidator, QIntValidator, QPalette, QTextOption, QSyntaxHighlighter,
    QTextCharFormat, QColor, QFont
)
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLayout, QVBoxLayout, QDialog, QGridLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QComboBox, QScrollArea, QFileDialog, QRadioButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView, QPlainTextEdit, QSizePolicy,
    QMessageBox, QSizePolicy
)

from qgis.gui import QgisInterface

from gis4wrf.core import Project, get_namelist_schema, UserError, WRFDistributionError, WPSDistributionError

from gis4wrf.plugin.constants import PLUGIN_NAME
from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.ui.helpers import MessageBar
from gis4wrf.plugin.ui.thread import ProgramThread
from gis4wrf.plugin.ui.dialog_nml_editor import NmlEditorDialog

class RunWidget(QWidget):
    tab_active = pyqtSignal()
    view_wrf_nc_file = pyqtSignal(str)

    def __init__(self, iface: QgisInterface) -> None:
        super().__init__()

        self.iface = iface

        self.options = get_options()
        self.msg_bar = MessageBar(iface)

        self.wps_box, [open_namelist_wps, prepare_only_wps, run_geogrid, run_ungrib, run_metgrid, open_output_wps] = \
            self.create_gbox_with_btns('WPS', [
                'Open Configuration',
                'Prepare only',
                ['Run Geogrid', 'Run Ungrib', 'Run Metgrid'],
                'Visualize Output'
            ])
        self.wrf_box, [open_namelist_wrf, prepare_only_wrf, run_real, run_wrf, open_output_wrf] = \
            self.create_gbox_with_btns('WRF', [
                'Open Configuration',
                'Prepare only',
                ['Run Real', 'Run WRF'],
                'Visualize Output'
            ])
        self.control_box, [kill_program] = self.create_gbox_with_btns('Program control', [
            'Kill Program'
        ])
        self.control_box.setVisible(False)
        self.stdout_box, self.stdout_textarea, self.stdout_highlighter = \
            self.create_stdout_box()

        vbox = QVBoxLayout()
        vbox.addWidget(self.wps_box)
        vbox.addWidget(self.wrf_box)
        vbox.addWidget(self.control_box)
        vbox.addWidget(self.stdout_box)
        self.stdout_box.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.setLayout(vbox)

        open_namelist_wps.clicked.connect(self.on_open_namelist_wps_clicked)
        prepare_only_wps.clicked.connect(self.on_prepare_only_wps_clicked)
        run_geogrid.clicked.connect(self.on_run_geogrid_clicked)
        run_ungrib.clicked.connect(self.on_run_ungrib_clicked)
        run_metgrid.clicked.connect(self.on_run_metgrid_clicked)
        open_output_wps.clicked.connect(self.on_open_output_wps_clicked)

        open_namelist_wrf.clicked.connect(self.on_open_namelist_wrf_clicked)
        prepare_only_wrf.clicked.connect(self.on_prepare_only_wrf_clicked)
        run_real.clicked.connect(self.on_run_real_clicked)
        run_wrf.clicked.connect(self.on_run_wrf_clicked)
        open_output_wrf.clicked.connect(self.on_open_output_wrf_clicked)

        kill_program.clicked.connect(self.on_kill_program_clicked)


    @property
    def project(self) -> Project:
        return self._project

    @project.setter
    def project(self, val: Project) -> None:
        ''' Sets the currently active project. See tab_simulation. '''
        self._project = val

    def prepare_wps_run(self) -> None:
        if not self.options.wps_dir:
            raise WPSDistributionError('WPS is not setup')
        self.project.prepare_wps_run(self.options.wps_dir)

    def prepare_wrf_run(self) -> None:
        if not self.options.wrf_dir:
            raise WRFDistributionError('WRF is not setup')
        self.project.prepare_wrf_run(self.options.wrf_dir)

    def on_open_namelist_wps_clicked(self) -> None:
        self.project.update_wps_namelist()
        self.open_editor_dialog(self.project.wps_namelist_path,
                                get_namelist_schema('wps'))   

    def on_open_namelist_wrf_clicked(self) -> None:
        # TODO wrap exceptions (from wrf_namelist.py) into message bar messages
        #      (same for prepare_*_run)
        self.project.update_wrf_namelist()
        self.open_editor_dialog(self.project.wrf_namelist_path,
                                get_namelist_schema('wrf'))

    def on_prepare_only_wps_clicked(self) -> None:
        self.prepare_wps_run()

        self.msg_bar.success('Successfully prepared WPS files in ' + self.project.run_wps_folder)

    def on_prepare_only_wrf_clicked(self) -> None:
        self.prepare_wrf_run()

        self.msg_bar.success('Successfully prepared WRF files in ' + self.project.run_wrf_folder)

    def on_run_geogrid_clicked(self) -> None:
        self.prepare_wps_run()

        # TODO move this into core
        self.run_program(self.options.geogrid_exe, self.project.run_wps_folder,
                         supports_mpi=True)

    def on_run_ungrib_clicked(self) -> None:
        self.prepare_wps_run()
        self.run_program(self.options.ungrib_exe, self.project.run_wps_folder,
                         supports_mpi=False)

    def on_run_metgrid_clicked(self) -> None:
        self.prepare_wps_run()
        self.run_program(self.options.metgrid_exe, self.project.run_wps_folder,
                         supports_mpi=True)

    def on_run_real_clicked(self) -> None:
        self.prepare_wrf_run()
        self.run_program(self.options.real_exe, self.project.run_wrf_folder,
                         supports_mpi=True)

    def on_run_wrf_clicked(self) -> None:
        self.prepare_wrf_run()
        self.run_program(self.options.wrf_exe, self.project.run_wrf_folder,
                         supports_mpi=True)

    def on_open_output_wps_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            caption='Open WRF NetCDF File',
            directory=self.project.run_wps_folder,
            filter='geo_em*;met_em*')
        if not path:
            return
        self.view_wrf_nc_file.emit(path)

    def on_open_output_wrf_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            caption='Open WRF NetCDF File',
            directory=self.project.run_wrf_folder,
            filter='wrfinput*;wrfbdy*;wrfout*')
        if not path:
            return
        self.view_wrf_nc_file.emit(path)

    def on_kill_program_clicked(self) -> None:
        self.dont_report_program_status = True
        self.thread.kill_program()

    def run_program(self, path: str, cwd: str, supports_mpi: bool) -> None:
        self.dont_report_program_status = False
        self.wps_box.setVisible(False)
        self.wrf_box.setVisible(False)
        self.control_box.setVisible(True)
        try:
            self.run_program_in_background(path, cwd, self.on_program_execution_done, supports_mpi)
        except:
            self.on_program_execution_done(path, None)
            raise

    def on_program_execution_done(self, path: str, error: Union[bool, str, None]) -> None:
        self.wps_box.setVisible(True)
        self.wrf_box.setVisible(True)
        self.control_box.setVisible(False)
        # The above causes a resize of the program output textarea
        # which requires that we scroll to the bottom again.
        vert_scrollbar = self.stdout_textarea.verticalScrollBar()
        vert_scrollbar.setValue(vert_scrollbar.maximum())

        if self.dont_report_program_status:
            return
        
        if error is None:
            # An exception that will be reported by the caller after this function returns.
            return
        if error:
            if isinstance(error, str):
                raise UserError('Program {} failed: {}'.format(os.path.basename(path), error))
            else:
                raise UserError('Program {} failed with errors, check the logs'.format(os.path.basename(path)))
        else:
            QMessageBox.information(self.iface.mainWindow(), PLUGIN_NAME, 
                'Program {} finished without errors!'.format(os.path.basename(path)))

    def open_editor_dialog(self, path: str, nml_schema: dict) -> Optional[str]:
        dialog = NmlEditorDialog(path, nml_schema)
        dialog.exec_()

    def create_gbox_with_btns(self, gbox_name: str, btn_names: List[Union[str,List[str]]]) \
            -> Tuple[QGroupBox, List[QPushButton]]:
        vbox = QVBoxLayout()
        btns = []
        for name_or_list in btn_names:
            if isinstance(name_or_list, str):
                name = name_or_list
                btn = QPushButton(name)
                btns.append(btn)
                vbox.addWidget(btn)
            else:
                hbox = QHBoxLayout()
                for name in name_or_list:
                    btn = QPushButton(name)
                    btns.append(btn)
                    hbox.addWidget(btn)
                vbox.addLayout(hbox)
        gbox = QGroupBox(gbox_name)
        gbox.setLayout(vbox)
        return gbox, btns

    def create_stdout_box(self) -> Tuple[QGroupBox,QPlainTextEdit,QSyntaxHighlighter]:
        gbox = QGroupBox('Program output')
        
        vbox = QVBoxLayout()
        gbox.setLayout(vbox)

        text_area = QPlainTextEdit()
        vbox.addWidget(text_area)
        text_area.setReadOnly(True)
        text_area.setWordWrapMode(QTextOption.NoWrap)
        
        palette = text_area.palette() # type: QPalette
        palette.setColor(QPalette.Active, QPalette.Base, QColor('#1E1E1E'))
        palette.setColor(QPalette.Inactive, QPalette.Base, QColor('#1E1E1E'))
        text_area.setPalette(palette)
        
        font = QFont('Monospace', 9)
        font.setStyleHint(QFont.TypeWriter)
        fmt = QTextCharFormat()
        fmt.setFont(font)
        fmt.setForeground(QColor(212, 212, 212))
        text_area.setCurrentCharFormat(fmt)
        
        doc = text_area.document()
        highlighter = LogSeverityHighlighter(doc)
        
        return gbox, text_area, highlighter

    def run_program_in_background(self, path: str, cwd: str, on_done: Callable[[str,Union[bool,str,None]],None],
                                  supports_mpi: bool) -> None:
        self.stdout_textarea.clear()

        # WRF/WPS does not use exit codes to indicate success/failure,
        # therefore in addition we look for a pattern in the program output.
        # TODO add 'FATAL' as patterm
        wrf_error_pattern = 'ERROR'

        use_mpi = supports_mpi and self.options.mpi_enabled
        if use_mpi and '-nompi' in path:
            raise UserError(
                'MPI is enabled but your WRF/WPS distribution does not support it.\n'
                'In the plugin options, either choose/download a distribution with MPI support or disable MPI')

        # Using QThread and signals (instead of a plain Python thread) is necessary
        # so that the on_done callback is run on the UI thread, instead of the worker thread.
        thread = ProgramThread(path, cwd, wrf_error_pattern,
                               use_mpi=use_mpi,
                               mpi_processes=self.options.mpi_processes)

        def on_output(out: str) -> None:
            self.stdout_textarea.appendPlainText(out)
            vert_scrollbar = self.stdout_textarea.verticalScrollBar()
            vert_scrollbar.setValue(vert_scrollbar.maximum())

        def on_finished() -> None:
            # When lines come in fast, then the highlighter is not called on each line.
            # Re-highlighting at the end is a work-around to at least have correct
            # highlighting after program termination.
            self.stdout_highlighter.rehighlight()

            if thread.exc_info:
                on_done(path, None)
                raise thread.exc_info[0].with_traceback(*thread.exc_info[1:])
            on_done(path, thread.error)
        thread.output.connect(on_output)
        thread.finished.connect(on_finished)
        thread.start()
        # so that we can kill the program later if requested
        self.thread = thread

class LogSeverityHighlighter(QSyntaxHighlighter):
    colors = {
        'inform': (QColor('#B5CEA8'), False),
        'warning': (QColor('orange'), False),
        'error': (Qt.red, False),
        'success': (Qt.darkGreen, True),
    }

    def highlightBlock(self, line: str) -> None:
        line = line.lower()
        for word, (color, full) in self.colors.items():
            idx = line.find(word)
            if idx >= 0:
                fmt = QTextCharFormat()
                fmt.setForeground(color)
                if full:
                    self.setFormat(0, len(line), fmt)
                else:
                    self.setFormat(idx, len(word), fmt)
                break

