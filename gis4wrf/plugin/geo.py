# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

from typing import List, Tuple, Callable, Optional, Union
from threading import Timer

from osgeo import gdal
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsGeometry, QgsVectorLayer, QgsFeature,
    QgsVectorDataProvider, QgsProject, QgsMapLayer, QgsLayerTree, QgsLayerTreeGroup,
    QgsRasterLayer, QgsLayerTreeLayer, QgsSingleSymbolRenderer, QgsFillSymbol,
    QgsPalettedRasterRenderer, QgsMapSettings, QgsRectangle, QgsRasterDataProvider, QgsRaster,
    QgsSingleBandGrayRenderer, QgsRasterRenderer, QgsContrastEnhancement, QgsRasterMinMaxOrigin,
    QgsSingleBandPseudoColorRenderer
)
from qgis.gui import QgsMapCanvas

import gis4wrf.core
from gis4wrf.core import BoundingBox2D
from gis4wrf.plugin.ui.helpers import dispose_after_delete


def get_qgis_crs(proj4: str) -> QgsCoordinateReferenceSystem:
    # https://issues.qgis.org/issues/17781#change-85587
    crs = QgsCoordinateReferenceSystem.fromProj4(proj4) # type: QgsCoordinateReferenceSystem
    if not crs.authid():
        srs_id = crs.saveAsUserCrs('WRF CRS ({})'.format(proj4))
        assert srs_id != -1
        assert crs.isValid()
    return crs

def rect_to_bbox(rect: QgsRectangle) -> BoundingBox2D:
    return BoundingBox2D(minx=rect.xMinimum(), maxx=rect.xMaximum(),
                         miny=rect.yMinimum(), maxy=rect.yMaximum())

def update_domain_outline_layers(canvas: QgsMapCanvas, project: gis4wrf.core.Project,
                                 zoom_out=True) -> None:
    gdal_ds = gis4wrf.core.convert_project_to_gdal_outlines(project)
    gdal_layer = gdal_ds.GetLayer(0) # type: ogr.Layer
    gdal_srs = gdal_layer.GetSpatialRef() # type: osr.SpatialReference
    proj4 = gdal_srs.ExportToProj4()

    qgs_crs = get_qgis_crs(proj4)

    group_name = 'WRF Domains (Vector)'

    registry = QgsProject.instance() # type: QgsProject
    root = registry.layerTreeRoot() # type: QgsLayerTree

    group = root.findGroup(group_name) # type: QgsLayerTreeGroup
    if group is None:
        group = root.insertGroup(0, group_name)
        group.setExpanded(False)
    else:
        group.removeAllChildren()

    gdal_layer.ResetReading()
    for idx, feature in enumerate(gdal_layer):
        title = 'Domain {}'.format(idx + 1)
        layer = QgsVectorLayer('Polygon?crs=' + qgs_crs.authid(), title, 'memory')
        sym = QgsFillSymbol.createSimple({
            'outline_color': 'red' if idx == 0 else 'blue',
            'style': 'no' # disable filling
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

        wkt = feature.geometry().ExportToWkt()
        qgs_geom = QgsGeometry.fromWkt(wkt) # type: QgsGeometry

        # QGIS's on-the-fly reprojection would only reproject the four corner points.
        # The work-around is to densify the geometry. This allows the domain layers
        # to be displayed accurately if the map projection differs from the domain projection.
        qgs_geom_dense = qgs_geom.densifyByCount(100)

        qgs_feature = QgsFeature()
        qgs_feature.setGeometry(qgs_geom_dense)

        provider = layer.dataProvider() # type: QgsVectorDataProvider
        provider.addFeature(qgs_feature)

        registry.addMapLayer(layer, False)
        group.addLayer(layer)
        if zoom_out and idx == project.domain_count - 1:
            zoom_out_to_layer(canvas, layer)

def update_domain_grid_layers(project: gis4wrf.core.Project) -> None:
    vrts = gis4wrf.core.convert_project_to_gdal_checkerboards(project)
    vrt_and_titles = [(vrt, 'Domain {}'.format(i + 1), None) for i, vrt in enumerate(vrts)]
    load_layers(vrt_and_titles, 'WRF Domains (Grid)', visible=False, expanded=False)

def zoom_out_to_layer(canvas: QgsMapCanvas, layer: QgsVectorLayer) -> None:
    settings = canvas.mapSettings() # type: QgsMapSettings
    new_extent = settings.layerExtentToOutputExtent(layer, layer.extent()) # type: QgsRectangle
    new_extent.scale(1.05)

    old_extent = canvas.extent() # type: QgsRectangle

    if old_extent.contains(new_extent):
        return

    canvas.setExtent(new_extent)
    canvas.refresh()

def load_layers(uris_and_names: List[Tuple[str,str,Optional[str]]], group_name=None,
                visible: Union[bool,int]=0, expanded: bool=True) -> List[QgsRasterLayer]:
    registry = QgsProject.instance() # type: QgsProject
    root = registry.layerTreeRoot() # type: QgsLayerTree
    if group_name:
        group = root.findGroup(group_name) # type: QgsLayerTreeGroup
        if group is None:
            group = root.insertGroup(0, group_name)
            group.setExpanded(expanded)
            visibility = (type(visible) == bool and visible) or (type(visible) == int)
            group.setItemVisibilityChecked(visibility)
        else:
            group.removeAllChildren()
    layers = []
    for i, (uri, name, short_name) in enumerate(uris_and_names):
        layer = QgsRasterLayer(uri, name)
        
        if short_name:
            layer.setShortName(short_name)
        fix_style(layer)
        registry.addMapLayer(layer, False)
        if group_name:
            layer_node = group.addLayer(layer) # type: QgsLayerTreeLayer
            visibility = (type(visible) == bool) or (type(visible) == int and i == visible)
        else:
            layer_node = root.insertLayer(0, layer)
            visibility = (type(visible) == bool and visible) or (type(visible) == int and i == visible)
        layer_node.setItemVisibilityChecked(visibility)
        layers.append(layer)

    return layers

def fix_style(layer: QgsRasterLayer) -> None:
    ''' Sets a sensible default style for loaded raster layers and fix up other issues.

    By default QGIS uses MultiBandColor renderer if there are multiple bands.
    (See https://github.com/qgis/QGIS/blob/final-3_0_1/src/core/raster/qgsrasterlayer.cpp#L729).
    This function picks the right renderers, either a palette or gray-band renderer.

    Also, fake categories/classes that exist due to GDAL limitations are removed.
    Search for UNUSED_CATEGORY_LABEL to find details. '''
    provider = layer.dataProvider() # type: QgsRasterDataProvider
    color_interp = provider.colorInterpretation(1)
    is_palette = color_interp == QgsRaster.PaletteIndex

    # See the link below on how to create default-type renderers.
    # https://github.com/qgis/QGIS/blob/final-3_0_1/src/core/raster/qgsrasterrendererregistry.cpp#L128-L137

    renderer = layer.renderer() # type: QgsRasterRenderer
    new_renderer = None
    if is_palette:
        # For paletted layers we always re-create the renderer even if it is already a
        # paletted renderer. This is because we need to remove the UNUSED categories.
        color_table = provider.colorTable(1)
        classes = QgsPalettedRasterRenderer.colorTableToClassData(color_table)
        if not any(c.label == gis4wrf.core.UNUSED_CATEGORY_LABEL for c in classes):
            return
        new_classes = filter(lambda c: c.label != gis4wrf.core.UNUSED_CATEGORY_LABEL, classes)
        new_renderer = QgsPalettedRasterRenderer(renderer.input(), 1, new_classes)
        layer.setRenderer(new_renderer)
    else:
        if not isinstance(renderer, QgsSingleBandGrayRenderer):
            new_renderer = QgsSingleBandGrayRenderer(renderer.input(), 1)
            layer.setRenderer(new_renderer)
            layer.setDefaultContrastEnhancement() # must be *after* setting the renderer

def get_raster_layers_in_group(group_name: str) -> List[QgsRasterLayer]:
    registry = QgsProject.instance() # type: QgsProject
    root = registry.layerTreeRoot() # type: QgsLayerTree

    group = root.findGroup(group_name) # type: QgsLayerTreeGroup
    if group is None:
        return []
    layers = [tree_layer.layer()
              for tree_layer
              in group.findLayers()
              if isinstance(tree_layer.layer(), QgsRasterLayer)]
    return layers

def remove_group(group_name: str) -> None:
    registry = QgsProject.instance() # type: QgsProject
    root = registry.layerTreeRoot() # type: QgsLayerTree
    group = root.findGroup(group_name) # type: QgsLayerTreeGroup
    if group is None:
        return
    root.removeChildNode(group)    

def switch_band(layer: QgsRasterLayer, index: int) -> None:
    renderer = layer.renderer().clone() # type: QgsRasterRenderer
    renderer.setInput(layer.renderer().input())
    if isinstance(renderer, QgsSingleBandGrayRenderer):
        renderer.setGrayBand(index + 1)
    elif isinstance(renderer, QgsPalettedRasterRenderer):
        # TODO need to replace renderer to set new band
        pass
    elif isinstance(renderer, QgsSingleBandPseudoColorRenderer):
        renderer.setBand(index + 1)
    layer.setRenderer(renderer)
    layer.triggerRepaint()

def load_wps_binary_layer(folder: str) -> None:
    vrt_path, title, short_name, dispose = gis4wrf.core.convert_wps_binary_to_vrt_dataset(folder)
    layer = load_layers([(vrt_path, title, short_name)])[0]
    dispose_after_delete(layer, dispose)

def add_default_basemap() -> None:
    url = 'type=xyz&zmin=0&zmax=20&url=http://a.tile.stamen.com/terrain-background/{z}/{x}/{y}.png'
    attribution = 'Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL'
    attribution_url = 'http://maps.stamen.com'
    registry = QgsProject.instance() # type: QgsProject
    root = registry.layerTreeRoot() # type: QgsLayerTree

    tree_layers = filter(QgsLayerTree.isLayer, root.children())
    if any(tree_layer.layer().source() == url for tree_layer in tree_layers):
        return
    layer = QgsRasterLayer(url, 'Stamen Terrain Background', 'wms')
    layer.setAttribution(attribution)
    layer.setAttributionUrl(attribution_url)
    registry.addMapLayer(layer, False)
    root.addLayer(layer)

    # Reset the Project CRS to WGS84 otherwise it will be set to the stamen layer CRS
    def setWGS84():
        registry.setCrs((QgsCoordinateReferenceSystem.fromProj4("+proj=longlat +datum=WGS84 +no_defs")))
    setWGS84()
    # Again with a delay, which is a work-around as sometimes QGIS does not apply the CRS change above.
    Timer(0.5, setWGS84).start()