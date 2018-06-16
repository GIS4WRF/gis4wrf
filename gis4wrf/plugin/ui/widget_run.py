# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import Optional, Tuple, List, Callable, Union, Iterable, Any
from io import StringIO
import os
import signal
import sys
import subprocess
import re

from PyQt5.QtCore import (
    QMetaObject, Qt, QLocale, pyqtSlot, pyqtSignal, QModelIndex, QThread
)
from PyQt5.QtGui import (
    QDoubleValidator, QIntValidator, QPalette, QGuiApplication, QTextOption, QSyntaxHighlighter,
    QTextCharFormat, QColor, QFont
)
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLayout, QVBoxLayout, QDialog, QGridLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QComboBox, QScrollArea, QFileDialog, QRadioButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView, QPlainTextEdit, QSizePolicy,
    QDialogButtonBox, QMessageBox, QSizePolicy, QTextBrowser
)

from PyQt5.Qt import QTextCursor

from qgis.gui import QgisInterface

from gis4wrf.core import Project, read_namelist, verify_namelist, get_namelist_schema

from gis4wrf.plugin.constants import PLUGIN_NAME
from gis4wrf.plugin.options import get_options
from gis4wrf.plugin.ui.helpers import MessageBar, IgnoreKeyPressesDialog

class RunWidget(QWidget):
    tab_active = pyqtSignal()
    view_wrf_nc_file = pyqtSignal(str)

    def __init__(self, iface: QgisInterface) -> None:
        super().__init__()

        self.iface = iface

        self.options = get_options()
        self.msg_bar = MessageBar(iface)

        self.wps_box, [open_namelist_wps, prepare_only_wps, run_geogrid, run_ungrib, run_metgrid, open_output_wps] = \
            self.create_gbox('WPS', [
                'Open Configuration',
                'Prepare only',
                ['Run Geogrid', 'Run Ungrib', 'Run Metgrid'],
                'Visualize Output'
            ])
        self.wrf_box, [open_namelist_wrf, prepare_only_wrf, run_real, run_wrf, open_output_wrf] = \
            self.create_gbox('WRF', [
                'Open Configuration',
                'Prepare only',
                ['Run Real', 'Run WRF'],
                'Visualize Output'
            ])
        self.control_box, [kill_program] = self.create_gbox('Program control', [
            'Kill Program'
        ])
        self.control_box.setVisible(False)
        self.stdout_box, self.stdout_textarea = self.create_stdout_box()

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

    def verify_wps_nml(self, text: str) -> None:
        nml = read_namelist(StringIO(text))
        # TODO catch "'ascii' codec can't decode byte 0xe2 in position 200: ordinal not in range(128)"
        #      and either auto-convert to ascii or display more helpful message
        verify_namelist(nml, 'wps')

    def verify_wrf_nml(self, text: str) -> None:
        nml = read_namelist(StringIO(text))
        verify_namelist(nml, 'wrf')

    def prepare_wps_run(self) -> None:
        self.project.prepare_wps_run(self.options.wps_dir)

    def prepare_wrf_run(self) -> None:
        self.project.prepare_wrf_run(self.options.wrf_dir)

    def on_open_namelist_wps_clicked(self) -> None:
        self.project.update_wps_namelist()
        self.open_editor_dialog(self.project.wps_namelist_path,
                                self.verify_wps_nml,
                                get_namelist_schema('wps'))   

    def on_open_namelist_wrf_clicked(self) -> None:
        # TODO wrap exceptions (from wrf_namelist.py) into message bar messages
        #      (same for prepare_*_run)
        self.project.update_wrf_namelist()
        self.open_editor_dialog(self.project.wrf_namelist_path,
                                self.verify_wrf_nml,
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
        self.run_program(self.options.geogrid_exe, self.project.run_wps_folder)

    def on_run_ungrib_clicked(self) -> None:
        self.prepare_wps_run()
        self.run_program(self.options.ungrib_exe, self.project.run_wps_folder)

    def on_run_metgrid_clicked(self) -> None:
        self.prepare_wps_run()
        self.run_program(self.options.metgrid_exe, self.project.run_wps_folder)

    def on_run_real_clicked(self) -> None:
        self.prepare_wrf_run()
        self.run_program(self.options.real_exe, self.project.run_wrf_folder)

    def on_run_wrf_clicked(self) -> None:
        self.prepare_wrf_run()
        self.run_program(self.options.wrf_exe, self.project.run_wrf_folder)

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
        pid = self.thread.pid
        os.kill(pid, signal.SIGTERM)

    def run_program(self, path: str, cwd: str) -> None:
        self.dont_report_program_status = False
        self.wps_box.setVisible(False)
        self.wrf_box.setVisible(False)
        self.control_box.setVisible(True)
        self.run_program_in_background(path, cwd, self.on_program_execution_done)

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
                QMessageBox.critical(self.iface.mainWindow(), PLUGIN_NAME, 
                    'Program {} failed: {}'.format(os.path.basename(path), error))
            else:
                QMessageBox.critical(self.iface.mainWindow(), PLUGIN_NAME, 
                    'Program {} failed with errors, check the logs.'.format(os.path.basename(path)))
        else:
            QMessageBox.information(self.iface.mainWindow(), PLUGIN_NAME, 
                'Program {} finished without errors!'.format(os.path.basename(path)))

    def open_editor_dialog(self, path: str, validate: Callable[[str],Optional[str]],
                           nml_schema: dict) -> Optional[str]:
        with open(path, 'r') as fp:
            text = fp.read()

        geom = QGuiApplication.primaryScreen().geometry()
        w, h = geom.width(), geom.height()
        
        # Ignoring key presses is necessary as otherwise pressing
        # enter in the search box closes the dialog.
        dialog = IgnoreKeyPressesDialog()
        
        dialog.setWindowTitle(os.path.basename(path))
        dialog.resize(w * 0.7, h * 0.6)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        hbox = QHBoxLayout()
        layout.addLayout(hbox)

        editor = QPlainTextEdit(text, dialog)
        editor.setWordWrapMode(QTextOption.NoWrap)
        hbox.addWidget(editor)

        def to_fortran(val) -> str:
            if val is True:
                return '.true.'
            if val is False:
                return '.false.'
            if isinstance(val, str):
                val = f"'{val}'"
            return str(val)

        nml_help = '<html>'
        anchors = set() # type: Set[str]
        for section_name, section in nml_schema.items():
            anchors.add(section_name)
            nml_help += f'<h2><a name="{section_name}">&{section_name}</a></h2>'
            for var_name, variable in section.items():
                anchors.add(var_name)
                description = variable['description']
                type_ = variable['type']
                item_type = variable.get('itemtype')
                min_len = variable.get('minlen')
                min_ = variable.get('min')
                max_ = variable.get('max')
                if item_type:
                    type_label += f' of {item_type}'
                else:
                    type_label = type_
                default = variable.get('default')
                example = variable.get('example')
                options = variable.get('options')

                nml_help += f'<h3><a name="{var_name}">{var_name}</a></h3>'
                nml_help += f'<p>{description}</p>'
                nml_help += f'Type: {type_}<br>'
                if min_len is not None:
                    if isinstance(min_len, str):
                        min_len = f'<a href="#{min_len}">{min_len}</a>'
                    nml_help += f'Length: {min_len}<br>'
                if min_ is not None:
                    nml_help += f'Min: <code>{min_}</code><br>'
                if max_ is not None:
                    nml_help += f'Max: <code>{max_}</code><br>'
                if default is not None:
                    default_ = to_fortran(default)
                    if type_ == 'list':
                        if default == []:
                            nml_help += f'Default: empty list'
                        else:
                            nml_help += f'Default: list of <code>{default_}</code>'
                    else:
                        nml_help += f'Default: <code>{default_}</code><br>'
                if example is not None:
                    val_type = item_type if item_type else type_
                    if isinstance(example, str) and val_type != 'str':
                        # Here we have a literal example in Fortran syntax,
                        # so we avoid surrounding it with single quotes.
                        pass
                    else:
                        example = to_fortran(example)
                    nml_help += f'Example: <code>{example}</code><br>'
                if options:
                    if isinstance(options, list):
                        nml_help += 'Options: <code>' + ', '.join(map(to_fortran, options)) + '</code><br>'
                    else:
                        nml_help += '<br>Options: <table border=1>'
                        for val, description in options.items():
                            val = to_fortran(val)
                            nml_help += f'<tr><td width="30%" align="center"><code>{val}</code></td>'
                            nml_help += f'<td width="70%">{description}</td></tr>'
                        nml_help += '</table>'

        nml_help += '</html>'

        nml_help_vbox = QVBoxLayout()
        hbox.addLayout(nml_help_vbox)

        # TODO set encoding of help page, e.g. degree symbol appears incorrect
        nml_help_viewer = QTextBrowser()
        nml_help_viewer.setMaximumWidth(dialog.width() * 0.3)
        nml_help_viewer.setText(nml_help)

        nml_help_search = QLineEdit()
        nml_help_search.setMaximumWidth(nml_help_viewer.maximumWidth())
        nml_help_search.setPlaceholderText('Find...')

        def search_from_start():
            nml_help_viewer.moveCursor(QTextCursor.Start)
            nml_help_viewer.find(nml_help_search.text())

            # TODO scroll such that search term is vertically centered
            #      currently page is minimally scrolled and term is often at the bottom
        
        def search_from_cursor():
            found = nml_help_viewer.find(nml_help_search.text())
            if not found:
                search_from_start()

        nml_help_search.textChanged.connect(search_from_start)
        nml_help_search.returnPressed.connect(search_from_cursor)

        nml_help_vbox.addWidget(nml_help_search)
        nml_help_vbox.addWidget(nml_help_viewer)

        def on_cursor_pos_changed():
            cursor = editor.textCursor()
            line = cursor.block().text()
            match = re.match(r'\s*&?([a-zA-Z0-9_]+)', line)
            if not match:
                return
            name = match.group(1)
            if name not in anchors:
                return
            nml_help_viewer.scrollToAnchor(name)

        editor.cursorPositionChanged.connect(on_cursor_pos_changed)

        def validate_and_save():
            text = editor.toPlainText()
            try:
                validate(text)
            except (TypeError, ValueError) as e:
                btn = QMessageBox.critical(
                    dialog, 'Syntax error', str(e),
                    QMessageBox.Cancel | QMessageBox.Ignore,
                    QMessageBox.Cancel)
                if btn != QMessageBox.Ignore:
                    return
            with open(path, 'w') as fp:
                fp.write(text)
            dialog.accept()

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(validate_and_save)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        doc = editor.document()
        font = doc.defaultFont()
        font.setFamily("Courier New")
        font.setPointSize(11)
        doc.setDefaultFont(font)

        result = dialog.exec_()
        if result == QDialog.Rejected:
            return None
        return editor.toPlainText()

    def create_gbox(self, gbox_name: str, btn_names: List[Union[str,List[str]]]) \
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

    def create_stdout_box(self) -> Tuple[QGroupBox,QPlainTextEdit]:
        vbox = QVBoxLayout()
        text_area = QPlainTextEdit()
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
        text_area.setReadOnly(True)
        text_area.setWordWrapMode(QTextOption.NoWrap)
        doc = text_area.document()
        self.stdout_highlighter = LogSeverityHighlighter(doc)
        vbox.addWidget(text_area)
        gbox = QGroupBox('Program output')
        gbox.setLayout(vbox)
        return gbox, text_area

    def run_program_in_background(self, path: str, cwd: str, on_done: Callable[[str,Union[bool,str,None]],None]) -> None:
        self.stdout_textarea.clear()

        # Using QThread and signals (instead of a plain Python thread) is necessary
        # so that the on_done callback is run on the UI thread, instead of the worker thread.
        thread = ProgramThread(path, cwd)
        # TODO add support for MPI

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
        # so that we can read the pid later on
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

class ProgramThread(QThread):
    output = pyqtSignal(str)

    def __init__(self, path: str, cwd: str) -> None:
        super().__init__()
        self.path = path
        self.cwd = cwd
        self.pid = -1
        self.error = None
        self.exc_info = None

    def run(self):
        try:
            for msg_type, msg_val in run_program(self.path, self.cwd):
                if msg_type == 'pid':
                    self.pid = msg_val
                elif msg_type == 'log':
                    self.output.emit(msg_val)
                elif msg_type == 'error':
                    self.error = msg_val
                else:
                    raise RuntimeError('Invalid output received: {}'.format(msg_type))
        except:
            self.exc_info = sys.exc_info()

def run_program(path: str, cwd: str) -> Iterable[Tuple[str,Any]]:
    startupinfo = None
    if os.name == 'nt':
        # hides the console window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    process = subprocess.Popen([path], cwd=cwd,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             bufsize=1, universal_newlines=True,
                             startupinfo=startupinfo)
    yield ('pid', process.pid)
    stdout = ''
    while True:
        line = process.stdout.readline()
        if line != '':
            stdout += line
            yield ('log', line.rstrip())
        else:
            break
    process.wait()
    if process.returncode != 0:
        yield ('log', 'Exit code: {}'.format(process.returncode))

    error = process.returncode != 0 or 'ERROR' in stdout
    yield ('error', error)

