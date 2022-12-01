from io import StringIO
import os
import re

from PyQt5.QtGui import (
    QGuiApplication, QTextOption
)
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit,
    QMessageBox, QDialogButtonBox
)
from PyQt5.Qt import QTextCursor

from gis4wrf.core import read_namelist, verify_namelist
from .helpers import IgnoreKeyPressesDialog
from .browser_nml_schema import NmlSchemaBrowser

# The dialog inherits from IgnoreKeyPressesDialog
# because ignoring key presses is necessary as otherwise pressing
# enter in the search box closes the self.
class NmlEditorDialog(IgnoreKeyPressesDialog):
    def __init__(self, path: str, schema: dict):
        super().__init__()

        with open(path, 'r') as fp:
            text = fp.read()

        geom = QGuiApplication.primaryScreen().geometry()
        w, h = geom.width(), geom.height()
    
        self.setWindowTitle(os.path.basename(path))
        self.resize(int(w * 0.7), int(h * 0.6))
        
        layout = QVBoxLayout()
        self.setLayout(layout)

        hbox = QHBoxLayout()
        layout.addLayout(hbox)

        editor = QPlainTextEdit(text, self)
        editor.setWordWrapMode(QTextOption.NoWrap)
        hbox.addWidget(editor)

        schema_vbox = QVBoxLayout()
        hbox.addLayout(schema_vbox)

        schema_browser = NmlSchemaBrowser(schema)
        schema_browser.setMaximumWidth(int(self.width() * 0.3))

        schema_search = QLineEdit()
        schema_search.setMaximumWidth(schema_browser.maximumWidth())
        schema_search.setPlaceholderText('Find...')

        def search_from_start():
            schema_browser.moveCursor(QTextCursor.Start)
            schema_browser.find(schema_search.text())

            # TODO scroll such that search term is vertically centered
            #      currently page is minimally scrolled and term is often at the bottom
        
        def search_from_cursor():
            found = schema_browser.find(schema_search.text())
            if not found:
                search_from_start()

        schema_search.textChanged.connect(search_from_start)
        schema_search.returnPressed.connect(search_from_cursor)

        schema_vbox.addWidget(schema_search)
        schema_vbox.addWidget(schema_browser)

        def on_cursor_pos_changed():
            cursor = editor.textCursor()
            line = cursor.block().text()
            match = re.match(r'\s*&?([a-zA-Z0-9_]+)', line)
            if not match:
                return
            name = match.group(1)
            if name not in schema_browser.anchors:
                return
            schema_browser.scrollToAnchor(name)

        editor.cursorPositionChanged.connect(on_cursor_pos_changed)

        def validate_and_save():
            text = editor.toPlainText()
            # TODO catch "'ascii' codec can't decode byte 0xe2 in position 200: ordinal not in range(128)"
            #      and either auto-convert to ascii or display more helpful message
            text_io = StringIO(text)
            try:
                nml = read_namelist(text_io)
            except Exception as e:
                QMessageBox.critical(
                    self, 'Syntax error', 'Error in namelist syntax. ' + str(e),
                    QMessageBox.Ok)
                return
            try:
                verify_namelist(nml, schema)
            except (TypeError, ValueError) as e:
                btn = QMessageBox.critical(
                    self, 'Schema error', str(e),
                    QMessageBox.Cancel | QMessageBox.Ignore,
                    QMessageBox.Cancel)
                if btn != QMessageBox.Ignore:
                    return
            with open(path, 'w') as fp:
                fp.write(text)
            self.accept()

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(validate_and_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        doc = editor.document()
        font = doc.defaultFont()
        font.setFamily("Courier New")
        font.setPointSize(11)
        doc.setDefaultFont(font)
