# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

# TODO give datasets proper names
geo_datasets = {
    'NUDAPT44_1km': 'NUDAPT44_1km.tar.bz2',
    'albedo_ncep': 'albedo_ncep.tar.bz2',
    'bnu_soiltype_bot': 'bnu_soiltype_bot.tar.bz2',
    'bnu_soiltype_top': 'bnu_soiltype_top.tar.bz2',
    'clayfrac_5m': 'clayfrac_5m.tar.bz2',
    'crop': 'crop.tar.bz2',
    'greenfrac': 'greenfrac.tar.bz2',
    'greenfrac_fpar_modis': 'greenfrac_fpar_modis.tar.bz2',
    'groundwater': 'groundwater.tar.bz2',
    'hangl': 'hangl.tar.bz2',
    'hanis': 'hanis.tar.bz2',
    'hasynw': 'hasynw.tar.bz2',
    'hasys': 'hasys.tar.bz2',
    'hasysw': 'hasysw.tar.bz2',
    'hasyw': 'hasyw.tar.bz2',
    'hcnvx': 'hcnvx.tar.bz2',
    'hlennw': 'hlennw.tar.bz2',
    'hlens': 'hlens.tar.bz2',
    'hlensw': 'hlensw.tar.bz2',
    'hlenw': 'hlenw.tar.bz2',
    'hslop': 'hslop.tar.bz2',
    'hstdv': 'hstdv.tar.bz2',
    'hzmax': 'hzmax.tar.bz2',
    'islope': 'islope.tar.bz2',
    'lai_modis_10m': 'lai_modis_10m.tar.bz2',
    'lai_modis_30s': 'lai_modis_30s.tar.bz2',
    'lake_depth': 'lake_depth.tar.bz2',
    'landuse_10m': 'landuse_10m.tar.bz2',
    'landuse_5m': 'landuse_5m.tar.bz2',
    'landuse_2m': 'landuse_2m.tar.bz2',
    'landuse_30s': 'landuse_30s.tar.bz2',
    'landuse_30s_with_lakes': 'landuse_30s_with_lakes.tar.bz2',
    'maxsnowalb': 'maxsnowalb.tar.bz2',
    'modis_landuse_20class_30s': 'modis_landuse_20class_30s.tar.bz2',
    'modis_landuse_20class_30s_with_lakes': 'modis_landuse_20class_30s_with_lakes.tar.bz2',
    'modis_landuse_20class_15s': 'modis_landuse_20class_15s.tar.bz2',
    'modis_landuse_21class_30s': 'modis_landuse_21class_30s.tar.bz2',
    'nlcd2006_ll_30s': 'nlcd2006_ll_30s.tar.bz2',
    'nlcd2006_ll_9s': 'nlcd2006_ll_9s.tar.bz2',
    'nlcd2011_can_ll_9s': 'nlcd2011_can_ll_9s.tar.bz2',
    'nlcd2011_ll_9s': 'nlcd2011_ll_9s.tar.bz2',
    'orogwd_2deg': 'orogwd_2deg.tar.bz2',
    'orogwd_1deg': 'orogwd_1deg.tar.bz2',
    'orogwd_30m': 'orogwd_30m.tar.bz2',
    'orogwd_20m': 'orogwd_20m.tar.bz2',
    'orogwd_10m': 'orogwd_10m.tar.bz2',
    'sandfrac_5m': 'sandfrac_5m.tar.bz2',
    'soiltemp_1deg': 'soiltemp_1deg.tar.bz2',
    'soiltype_bot_10m': 'soiltype_bot_10m.tar.bz2',
    'soiltype_bot_5m': 'soiltype_bot_5m.tar.bz2',
    'soiltype_bot_2m': 'soiltype_bot_2m.tar.bz2',
    'soiltype_bot_30s': 'soiltype_bot_30s.tar.bz2',
    'soiltype_top_10m': 'soiltype_top_10m.tar.bz2',
    'soiltype_top_5m': 'soiltype_top_5m.tar.bz2',
    'soiltype_top_2m': 'soiltype_top_2m.tar.bz2',
    'soiltype_top_30s': 'soiltype_top_30s.tar.bz2',
    'ssib_landuse_10m': 'ssib_landuse_10m.tar.bz2',
    'ssib_landuse_5m': 'ssib_landuse_5m.tar.bz2',
    'topo_10m': 'topo_10m.tar.bz2',
    'topo_5m': 'topo_5m.tar.bz2',
    'topo_2m': 'topo_2m.tar.bz2',
    'topo_30s': 'topo_30s.tar.bz2',
    'topo_gmted2010_30s': 'topo_gmted2010_30s.tar.bz2',
    'varsso_10m': 'varsso_10m.tar.bz2',
    'varsso_5m': 'varsso_5m.tar.bz2',
    'varsso_2m': 'varsso_2m.tar.bz2',
    'varsso': 'varsso.tar.bz2',
}

# Lowest resolution of each mandatory field (WRF 3.9).
# See http://www2.mmm.ucar.edu/wrf/users/download/get_sources_wps_geog_V3.html.
geo_datasets_mandatory_lores = [
    'albedo_ncep',
    'clayfrac_5m',
    'greenfrac',
    'islope',
    'lai_modis_10m',
    'lake_depth',
    'landuse_10m',
    'maxsnowalb',
    'orogwd_2deg',
    'sandfrac_5m',
    'soiltemp_1deg',
    'soiltype_bot_10m',
    'soiltype_top_10m',
    'topo_10m',
    'varsso_10m'
]

# Highest resolution of each mandatory field (WRF 3.9).
# See http://www2.mmm.ucar.edu/wrf/users/download/get_sources_wps_geog_V3.html.
geo_datasets_mandatory_hires = [
    'albedo_ncep',
    'clayfrac_5m',
    'greenfrac_fpar_modis',
    'islope',
    'lai_modis_30s',
    'lake_depth',
    'modis_landuse_20class_30s_with_lakes',
    'maxsnowalb',
    'orogwd_10m',
    'sandfrac_5m',
    'soiltemp_1deg',
    'soiltype_bot_30s',
    'soiltype_top_30s',
    'topo_gmted2010_30s',
    'varsso'
]

met_datasets = { 
    'ds083.0' : 'NCEP FNL Operational Model Global Tropospheric Analyses, April 1997 through June 2007',
    'ds083.2' : 'NCEP FNL Operational Model Global Tropospheric Analyses, continuing from July 1999',
    'ds083.3' : 'NCEP GDAS/FNL 0.25 Degree Global Tropospheric Analyses and Forecast Grids',
    'ds084.1' : 'NCEP GFS 0.25 Degree Global Forecast Grids Historical Archive',
    'ds090.0' : 'CEP/NCAR Global Reanalysis Products, 1948-continuing'

}

met_datasets_vtables = {
    'ds083.0' : 'Vtable.GFS',
    'ds083.2' : 'Vtable.GFS',
    'ds083.3' : 'Vtable.GFS',
    'ds084.1' : 'Vtable.GFS',
    'ds090.0' : 'Vtable.NNRP'
}