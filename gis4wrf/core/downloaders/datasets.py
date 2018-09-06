# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

geo_datasets = {
    "topo_10m": ("USGS GTOPO DEM", 0.16666667),
    "topo_5m": ("USGS GTOPO DEM", 0.08333333),
    "topo_2m": ("USGS GTOPO DEM", 0.03333333),
    "topo_30s": ("USGS GTOPO DEM", 0.00833333),
    "topo_gmted2010_30s": ("USGS GMTED2010 DEM", 0.03333333),
    "lake_depth": ("Lake Depth", 0.03333333),

    "landuse_10m": ("24-category USGS land use", 0.16666667),
    "landuse_5m": ("24-category USGS land use", 0.08333333),
    "landuse_2m": ("24-category USGS land use", 0.03333333),
    "landuse_30s": ("24-category USGS land use", 0.00833333),
    "landuse_30s_with_lakes": ("25-category USGS landuse", 0.00833333),
    "modis_landuse_20class_30s": ("Noah-modified 20-category IGBP-MODIS landuse", 0.00833333),
    "modis_landuse_20class_30s_with_lakes": ("New Noah-modified 21-category IGBP-MODIS landuse", 0.00833333),
    "modis_landuse_20class_15s": ("Noah-modified 20-category IGBP-MODIS landuse", 0.004166667),
    "modis_landuse_21class_30s": ("Noah-modified 21-category IGBP-MODIS landuse", 0.00833333),
    "nlcd2006_ll_30s": ("National Land Cover Database 2006", 0.00833333),
    "nlcd2006_ll_9s": ("National Land Cover Database 2006", 0.0025),
    "nlcd2011_imp_ll_9s.tar": ("National Land Cover Database 2011 -- imperviousness percent", 0.0025),
    "nlcd2011_can_ll_9s": ("National Land Cover Database 2011 -- canopy percent", 0.0025),
    "nlcd2011_ll_9s": ("National Land Cover Database 2011", 0.0025),
    "ssib_landuse_10m": ("12-category Simplified Simple Biosphere Model (SSiB) land use", 0.1666667),
    "ssib_landuse_5m": ("12-category Simplified Simple Biosphere Model (SSiB) land use", 0.08333333),

    "NUDAPT44_1km": ("National Urban Database (NUDAPT) for 44 US cities", 0.0025),

    "crop": ("Monthly green fraction", 'various'),
    "greenfrac": ("Monthly green fraction", 0.144),
    "greenfrac_fpar_modis": ("MODIS Monthly Leaf Area Index/FPAR", 0.00833333),
    "sandfrac_5m": ("Sand fraction", 0.08333333),
    "soiltemp_1deg": ("Soil temperature", 1.0),
    "lai_modis_10m": ("MODIS Leaf Area Index", 0.16666667),
    "lai_modis_30s": ("MODIS Leaf Area Index", 0.00833333),

    "bnu_soiltype_bot": ("16-category bottom-layer soil type", 0.00833333),
    "bnu_soiltype_top": ("16-category top-layer soil type", 0.00833333),
    "clayfrac_5m": ("Clay Fraction", 0.08333333),
    "soiltype_bot_10m": ("Bottom-layer soil type", 0.16666667),
    "soiltype_bot_5m": ("Bottom-layer soil type", 0.08333333),
    "soiltype_bot_2m": ("Bottom-layer soil type", 0.03333333),
    "soiltype_bot_30s": ("Bottom-layer soil type", 0.00833333),
    "soiltype_top_10m": ("Top-layer soil type", 0.16666667),
    "soiltype_top_5m": ("Top-layer soil type", 0.08333333),
    "soiltype_top_2m": ("Top-layer soil type", 0.03333333),
    "soiltype_top_30s": ("Top-layer soil type", 0.00833333),

    "albedo_ncep": ("NCEP Monthly surface albedo", 0.144),
    "maxsnowalb": ("Maximum snow albedo", 1.0),
    
    "groundwater": ("Groundwater data", 0.00833333),

    "islope": ("14-category slope index", 1.0),

    "orogwd_2deg": ("Subgrid orography information for gravity wave drag option", 2.0),
    "orogwd_1deg": ("Subgrid orography information for gravity wave drag option", 1.0),
    "orogwd_30m": ("Subgrid orography information for gravity wave drag option", 0.5),
    "orogwd_20m": ("Subgrid orography information for gravity wave drag option", 0.3333333),
    "orogwd_10m": ("Subgrid orography information for gravity wave drag option", 0.16666667),
    "varsso_10m": ("Variance of subgrid-scale orography", 0.16666667),
    "varsso_5m": ("Variance of subgrid-scale orography", 0.08333333),
    "varsso_2m": ("Variance of subgrid-scale orography", 0.03333333),
    "varsso": ("Variance of subgrid-scale orography", 0.00833333),

    "albedo_modis": ("Monthly MODIS surface albedo", 0.05),
    "greenfrac_fpar_modis_5m": ("MODIS FPAR, subsampled by NCAR/MMM 2018-05-23 from 30-arc-second", 0.00833333),
    "maxsnowalb_modis": ("MODIS maximum snow albedo", 0.05),
    "modis_landuse_20class_5m_with_lakes": ("Noah-modified 21-category IGBP-MODIS landuse, subsampled by NCAR/MMM 2018-05-23 from 30-arc-second", 0.00833333),
    "topo_gmted2010_5m": ("GMTED2010 5-arc-minute topography height, subsampled by NCAR/MMM 2018-05-23 from 30-arc-second", 0.0833333),
    "erod": ("EROD", 0.25),
    "soilgrids": ("soilgrids", 0.00833333),
    "urbfrac_nlcd2011": ("Urban fraction derived from 30 m NLCD 2011 (22 = 50%, 23 = 90%, 24 = 95%)", 30.0), # FIXME: this is in Albers proj with unit metres
    # TODO: add `updated_Iceland_LU.tar.gz``
}

# Lowest resolution of each mandatory field (WRF 4.0).
# See http://www2.mmm.ucar.edu/wrf/users/download/get_sources_wps_geog.html.
geo_datasets_mandatory_lores = [
    "albedo_modis",
    "greenfrac_fpar_modis",
    "greenfrac_fpar_modis_5m",
    "lai_modis_10m",
    "maxsnowalb_modis",
    "modis_landuse_20class_5m_with_lakes",
    "orogwd_1deg",
    "soiltemp_1deg",
    "soiltype_bot_5m",
    "soiltype_top_5m",
    "topo_gmted2010_5m"
]

# Highest resolution of each mandatory field (WRF 4.0).
# See http://www2.mmm.ucar.edu/wrf/users/download/get_sources_wps_geog.html.
geo_datasets_mandatory_hires = [
    "albedo_modis",
    "greenfrac_fpar_modis",
    "lai_modis_10m",
    "lai_modis_30s",
    "maxsnowalb_modis",
    "modis_landuse_20class_30s_with_lakes",
    "orogwd_2deg",
    "orogwd_1deg",
    "orogwd_30m",
    "orogwd_20m",
    "orogwd_10m",
    "soiltemp_1deg",
    "soiltype_bot_30s",
    "soiltype_top_30s",
    "topo_gmted2010_30s",
    "varsso",
    "varsso_10m",
    "varsso_5m",
    "varsso_2m"
]

met_datasets = { 
    "ds083.0" : "NCEP FNL Operational Model Global Tropospheric Analyses, April 1997 through June 2007",
    "ds083.2" : "NCEP FNL Operational Model Global Tropospheric Analyses, continuing from July 1999",
    "ds083.3" : "NCEP GDAS/FNL 0.25 Degree Global Tropospheric Analyses and Forecast Grids",
    "ds084.1" : "NCEP GFS 0.25 Degree Global Forecast Grids Historical Archive"
}

met_datasets_vtables = {
    "ds083.0" : "Vtable.GFS",
    "ds083.2" : "Vtable.GFS",
    "ds083.3" : "Vtable.GFS",
    "ds084.1" : "Vtable.GFS"
}