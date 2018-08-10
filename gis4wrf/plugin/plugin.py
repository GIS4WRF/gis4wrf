# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List, Callable
import webbrowser
import time
import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QWidget
from qgis.core import QgsMessageLog, Qgis
from qgis.gui import QgisInterface

from gis4wrf.core import (
    get_latest_gis4wrf_version, get_installed_gis4wrf_version, is_newer_version,
    logger)

# Initialize Qt resources from auto-generated file resources.py
import gis4wrf.plugin.resources

from gis4wrf.plugin.ui.thread import TaskThread

from gis4wrf.plugin.ui.options import OptionsFactory
from gis4wrf.plugin.ui.dock import MainDock
from gis4wrf.plugin.ui.dialog_about import AboutDialog

from gis4wrf.plugin.geo import add_default_basemap, load_wps_binary_layer
from gis4wrf.plugin.constants import (
    PLUGIN_NAME, GIS4WRF_LOGO_PATH, ADD_WRF_NETCDF_LAYER_ICON_PATH, 
    ADD_BINARY_LAYER_ICON_PATH, ABOUT_ICON_PATH, BUG_ICON_PATH)


class QGISPlugin():
    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface
        self.actions = []  # type: List[QAction]
        self.dock_widget = None # type: MainDock

    def initGui(self) -> None:
        """Create the menu entries and toolbar icons inside the QGIS GUI.
           Note: This method is called by QGIS.
        """
        self.init_logging()

        self.menu = '&' + PLUGIN_NAME
        self.add_action(GIS4WRF_LOGO_PATH, text=PLUGIN_NAME, callback=self.show_dock, add_to_toolbar=True,
                        parent=self.iface.mainWindow(), status_tip='Run GIS4WRF')
        self.add_action(ADD_WRF_NETCDF_LAYER_ICON_PATH, text='Add WRF NetCDF Layer...', add_to_add_layer=True, add_to_menu=False,
                        parent=self.iface.mainWindow(), callback=self.add_wrf_layer)
        self.add_action(ADD_BINARY_LAYER_ICON_PATH, text='Add WPS Binary Layer...', add_to_add_layer=True, add_to_menu=False,
                        parent=self.iface.mainWindow(), callback=self.add_wps_binary_layer)
        self.add_action(ABOUT_ICON_PATH, text="About", callback=self.show_about,
                        parent=self.iface.mainWindow())
        self.add_action(BUG_ICON_PATH, text='Report a bug', callback=self.report_bug,
                        parent=self.iface.mainWindow(), status_tip='Report a bug')

        self.options_factory = OptionsFactory()
        self.iface.registerOptionsWidgetFactory(self.options_factory)

        self.check_version()

    def unload(self) -> None:
        """Removes the plugin menu item and icon from QGIS GUI.
           Note: This method is called by QGIS.
        """
        for action in self.actions:
            self.iface.removePluginMenu('&' + PLUGIN_NAME, action)
            self.iface.removeToolBarIcon(action)
            self.iface.removeAddLayerAction(action)
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
        self.iface.unregisterOptionsWidgetFactory(self.options_factory)

        self.destroy_logging()

    def show_dock(self) -> None:
        if not self.dock_widget:
            self.dock_widget = MainDock(self.iface, self.dock_widget)
        self.iface.addDockWidget(
            Qt.RightDockWidgetArea, self.dock_widget)
        add_default_basemap()

    def show_about(self) -> None:
        AboutDialog().exec_()

    def add_wrf_layer(self) -> None:
        path, _ = QFileDialog.getOpenFileName(caption='Open WRF NetCDF File')
        if not path:
            return
        if not self.dock_widget:
            self.show_dock()
        self.dock_widget.view_tab.add_dataset(path)
        self.dock_widget.open_view_tab()

    def add_wps_binary_layer(self) -> None:
        folder = QFileDialog.getExistingDirectory(caption='Select WPS Binary Dataset Folder')
        if not folder:
            return
        load_wps_binary_layer(folder)

    def report_bug(self) -> None:
        webbrowser.open('https://github.com/GIS4WRF/gis4wrf/issues')

    def init_logging(self) -> None:
        levels = {
            logging.NOTSET: getattr(Qgis, 'None'),
            logging.DEBUG: Qgis.Info,
            logging.INFO: Qgis.Info,
            logging.WARN: Qgis.Warning,
            logging.ERROR: Qgis.Critical,
            logging.CRITICAL: Qgis.Critical,
        }
        class QgsLogHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                log_entry = self.format(record)
                level = levels[record.levelno]                
                QgsMessageLog.logMessage(log_entry, PLUGIN_NAME, level, False)
        
        self.log_handler = QgsLogHandler()
        logger.addHandler(self.log_handler)

    def destroy_logging(self) -> None:
        logger.removeHandler(self.log_handler)

    def check_version(self) -> None:
        def get_latest_delayed() -> str:
            # When QGIS is started, display messages after QGIS 
            # is fully loaded by waiting for 2 mins as plugins
            # are activated whilst QGIS is loading.
            time.sleep(120)
            return get_latest_gis4wrf_version()

        def on_succeeded(latest: str) -> None:
            installed = get_installed_gis4wrf_version()
            if is_newer_version(latest, installed):
                QMessageBox.information(self.iface.mainWindow(), PLUGIN_NAME,
                   'Your ' + PLUGIN_NAME + ' version is outdated, please update.\n' + \
                   'Installed: ' + installed + ', Latest: ' + latest, QMessageBox.Ok)
        
        thread = TaskThread(get_latest_delayed)
        thread.succeeded.connect(on_succeeded)
        thread.start()

    def add_action(self, icon_path: str, text: str, callback: Callable,
                   enabled_flag: bool=True, add_to_menu: bool=True,
                   add_to_toolbar: bool=False, add_to_add_layer: bool=False,
                   status_tip: str=None, whats_this: str=None, parent: QWidget=None
                   ) -> QAction:
        """Helper function for creating menu items

        Parameters
        ----------
        icon_path: Path to the icon for this action. Can be a resource
            path (e.g. `:/plugins/foo/bar.png`) or a normal file system path.

        text: Text that should be shown in menu items for this action.

        callback: Function to be called when the action is triggered.

        enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.

        add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.

        add_to_toolbar: Flag indicating whether the action should also
            be added to the Plugins toolbar. Defaults to False.

        add_to_layer: Flag indicating whether the action should also
            be added to the Layer > Add Layer menu. Defaults to False.

        status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.

        whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action after clicking on `?`.

        parent: Parent widget for the new action. Defaults None.

        Returns
        -------
        out: The action that was created. Note that the action is
            also added to `self.actions` list.
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        if add_to_add_layer:
            self.iface.insertAddLayerAction(action)

        self.actions.append(action)

        return action
