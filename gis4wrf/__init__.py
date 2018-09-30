# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

""" QGIS plugin discovery """
from gis4wrf.bootstrap import bootstrap

def classFactory(iface):
    """Load QGISPlugin class.

    Parameters
    ----------
    iface: qgis.gui.QgisInterface
        An interface instance that will be passed to this class
        which provides the hook by which you can manipulate the QGIS
        application at run time.

    Returns
    -------
    out: gis4wrf.plugin.QGISPlugin
        The QGIS Plugin Implementation.
    """
    bootstrap_with_ui(iface)

    from gis4wrf.plugin.plugin import QGISPlugin
    return QGISPlugin(iface)

def bootstrap_with_ui(iface):
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5.QtCore import QCoreApplication
    from gis4wrf.plugin.constants import PLUGIN_NAME
    from gis4wrf.plugin.ui.helpers import WaitDialog

    app = QCoreApplication.instance()

    parent = iface.mainWindow()
    dialog = None
    log = ''
    try:
        for msg_type, msg_val in bootstrap():
            # Ideally, bootstrap() should run in a QThread, however this requires bigger refactoring
            # since the classFactory() function above needs to import the plugin module and return an instance.
            # To make this asynchronous, the plugin class would have to be changed to lazy-initialize itself.
            app.processEvents()

            if msg_type == 'log':
                log += msg_val
            elif msg_type == 'needs_install':
                QMessageBox.information(parent, PLUGIN_NAME,
                    PLUGIN_NAME + ' requires additional or updated versions of Python packages to function. ' +
                    'These will be installed into a separate folder specific to ' + PLUGIN_NAME + ' and ' +
                    'will not influence any existing Python installation.',
                    QMessageBox.Ok)
                dialog = WaitDialog(parent, PLUGIN_NAME)
            elif msg_type == 'install_done':
                dialog.accept()
    except Exception as e:
        if dialog:
            dialog.accept()
        QMessageBox.critical(parent, PLUGIN_NAME,
            'An error occurred during the installation of Python packages. ' +
            'Click on "Stack Trace" in the QGIS message bar for details.')
        raise RuntimeError(PLUGIN_NAME + ': Error installing Python packages\nLog:\n' + log) from e
