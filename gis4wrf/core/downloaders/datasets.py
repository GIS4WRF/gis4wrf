# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

geo_datasets = {
    "topo_10m": "USGS GTOPO DEM (10' of arc)",
    "topo_5m": "USGS GTOPO DEM (5' of arc)",
    "topo_2m": "USGS GTOPO DEM (2' of arc)",
    "topo_30s": "USGS GTOPO DEM (30'' of arc)",
    "topo_gmted2010_30s": "USGS GMTED2010 DEM (30'' of arc)",
    "lake_depth": "Lake Depth (30'' of arc)",

    "landuse_10m": "24-category USGS land use (10' of arc)",
    "landuse_5m": "24-category USGS land use (5' of arc)",
    "landuse_2m": "24-category USGS land use (2' of arc)",
    "landuse_30s": "24-category USGS land use (30'' of arc)",
    "landuse_30s_with_lakes": "25-category USGS landuse (30'' of arc)",
    "modis_landuse_20class_30s": "Noah-modified 20-category IGBP-MODIS landuse (30'' of arc)",
    "modis_landuse_20class_30s_with_lakes": "New Noah-modified 21-category IGBP-MODIS landuse (30'' of arc)",
    "modis_landuse_20class_15s": "Noah-modified 20-category IGBP-MODIS landuse (15'' of arc)",
    "modis_landuse_21class_30s": "Noah-modified 21-category IGBP-MODIS landuse (30'' of arc)",
    "nlcd2006_ll_30s": "National Land Cover Database 2006 (30' of arc)",
    "nlcd2006_ll_9s": "National Land Cover Database 2006 (9' of arc)",
    "nlcd2011_imp_ll_9s.tar": "National Land Cover Database 2011 -- imperviousness percent (9'' of arc)",
    "nlcd2011_can_ll_9s": "National Land Cover Database 2011 -- canopy percent (9'' of arc)",
    "nlcd2011_ll_9s": "National Land Cover Database 2011 (9'' of arc)",
    "ssib_landuse_10m": "12-category Simplified Simple Biosphere Model (SSiB) land use (10' of arc)",
    "ssib_landuse_5m": "12-category Simplified Simple Biosphere Model (SSiB) land use (5' of arc)",

    "NUDAPT44_1km": "National Urban Database (NUDAPT) for 44 US cities (9'' of arc)",

    "crop": "Monthly green fraction (7' 30'' of arc)",
    "greenfrac": "Monthly green fraction (8' 38.4'' of arc)",
    "greenfrac_fpar_modis": "MODIS Monthly Leaf Area Index/FPAR (30'' of arc)",
    "sandfrac_5m": "Sand fraction (5' of arc)",
    "soiltemp_1deg": "Soil temperature (1° of arc)",
    "lai_modis_10m": "MODIS Leaf Area Index (10' of arc)",
    "lai_modis_30s": "MODIS Leaf Area Index (30'' of arc)",

    "bnu_soiltype_bot": "16-category bottom-layer soil type (30'' of arc)",
    "bnu_soiltype_top": "16-category top-layer soil type (30'' of arc)",
    "clayfrac_5m": "Clay Fraction (5' of arc)",
    "soiltype_bot_10m": "Bottom-layer soil type (10' of arc)",
    "soiltype_bot_5m": "Bottom-layer soil type (5' of arc)",
    "soiltype_bot_2m": "Bottom-layer soil type (2' of arc)",
    "soiltype_bot_30s": "Bottom-layer soil type (30'' of arc)",
    "soiltype_top_10m": "Top-layer soil type (10' of arc)",
    "soiltype_top_5m": "Top-layer soil type (5' of arc)",
    "soiltype_top_2m": "Top-layer soil type (2' of arc)",
    "soiltype_top_30s": "Top-layer soil type (30'' of arc)",

    "albedo_ncep": "NCEP Monthly surface albedo (8' 38.4'' of arc)",
    "maxsnowalb": "Maximum snow albedo (1° of arc)",
    
    "groundwater": "Groundwater data (30'' of arc)",

    "islope": "14-category slope index (1° of arc)",

    "orogwd_2deg": "Subgrid orography information for gravity wave drag option (2° of arc)",
    "orogwd_1deg": "Subgrid orography information for gravity wave drag option (1° of arc)",
    "orogwd_30m": "Subgrid orography information for gravity wave drag option (30' of arc)",
    "orogwd_20m": "Subgrid orography information for gravity wave drag option (20' of arc)",
    "orogwd_10m": "Subgrid orography information for gravity wave drag option (10' of arc)",
    "varsso_10m": "Variance of subgrid-scale orography (10' of arc)",
    "varsso_5m": "Variance of subgrid-scale orography (5' of arc)",
    "varsso_2m": "Variance of subgrid-scale orography (2' of arc)",
    "varsso": "Variance of subgrid-scale orography (30'' of arc)",

    "hangl": "Angle of the mountain range with respect to east (9' 59.94'' of arc)",
    "hanis": "Anisotropy/aspect ratio of orography (9' 59.94'' of arc)",
    "hasynw": "Orographic asymmetry in NW-SE plane (9' 59.94'' of arc)",
    "hasys": "Orographic asymmetry for upstream & downstream flow in S-N plane (9' 59.94'' of arc)",
    "hasysw": "Orographic asymmetry for upstream & downstream flow in SW-NE plane (9' 59.94'' of arc)",
    "hasyw": "Orographic asymmetry for upstream & downstream flow in W-E plane (9' 59.94'' of arc)",
    "hcnvx": "Normalized 4th moment of the orographic convexity (9' 59.94'' of arc)",
    "hlennw": "Orographic length scale for upstream & downstream flow in NW-SE plane (9' 59.94'' of arc)",
    "hlens": "Orographic length scale for upstream & downstream flow in S-N plane (9' 59.94'' of arc)",
    "hlensw": "Orographic length scale for upstream & downstream flow in SW-NE plane (9' 59.94'' of arc)",
    "hlenw": "Orographic length scale for upstream & downstream flow in W-E plane (9' 59.94'' of arc)",
    "hslop": "Slope of orography (9' 59.94'' of arc)",
    "hstdv": "Orographic standard deviation (9' 59.94'' of arc)",
    "hzmax": "Max height above mean orography (9' 59.94'' of arc)",
}

# Lowest resolution of each mandatory field (WRF 3.9).
# See http://www2.mmm.ucar.edu/wrf/users/download/get_sources_wps_geog_V3.html.
geo_datasets_mandatory_lores = [
    "albedo_ncep",
    "clayfrac_5m",
    "greenfrac",
    "islope",
    "lai_modis_10m",
    "lake_depth",
    "landuse_10m",
    "maxsnowalb",
    "orogwd_2deg",
    "sandfrac_5m",
    "soiltemp_1deg",
    "soiltype_bot_10m",
    "soiltype_top_10m",
    "topo_10m",
    "varsso_10m"
]

# Highest resolution of each mandatory field (WRF 3.9).
# See http://www2.mmm.ucar.edu/wrf/users/download/get_sources_wps_geog_V3.html.
geo_datasets_mandatory_hires = [
    "albedo_ncep",
    "clayfrac_5m",
    "greenfrac_fpar_modis",
    "islope",
    "lai_modis_30s",
    "lake_depth",
    "modis_landuse_20class_30s_with_lakes",
    "maxsnowalb",
    "orogwd_10m",
    "sandfrac_5m",
    "soiltemp_1deg",
    "soiltype_bot_30s",
    "soiltype_top_30s",
    "topo_gmted2010_30s",
    "varsso"
]

met_datasets = { 
    "ds083.0" : "NCEP FNL Operational Model Global Tropospheric Analyses, April 1997 through June 2007",
    "ds083.2" : "NCEP FNL Operational Model Global Tropospheric Analyses, continuing from July 1999",
    "ds083.3" : "NCEP GDAS/FNL 0.25 Degree Global Tropospheric Analyses and Forecast Grids",
    "ds084.1" : "NCEP GFS 0.25 Degree Global Forecast Grids Historical Archive",
    "ds090.0" : "CEP/NCAR Global Reanalysis Products, 1948-continuing"

}

met_datasets_vtables = {
    "ds083.0" : "Vtable.GFS",
    "ds083.2" : "Vtable.GFS",
    "ds083.3" : "Vtable.GFS",
    "ds084.1" : "Vtable.GFS",
    "ds090.0" : "Vtable.NNRP"
}