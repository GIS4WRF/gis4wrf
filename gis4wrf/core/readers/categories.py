# GIS4WRF (https://doi.org/10.5281/zenodo.1288569)
# Copyright (c) 2018 D. Meyer and M. Riechert. Licensed under MIT.

# colors for categories defined directly in WPS Binary index file or WRF NetCDF global attributes
# (only used if existing category scheme does not contain the category)
darkblue = '#001DB1'
blue = '#0000FF'
lightblue = '#BAECFF'
black = '#000000'
LANDUSE_FIELDS = {
    'iswater': ('Water', darkblue),
    'islake': ('Lake', blue),
    'isice': ('Ice', lightblue),
    'isurban': ('Urban', black)
}

# values and labels from WRF's LANDUSE.TBL
LANDUSE = {
    'USGS': {
         1: ('Urban and Built-Up Land', '#FF0000'),
         2: ('Dryland Cropland and Pasture', '#FFFF00'),
         3: ('Irrigated Cropland and Pasture', '#FFF054'),
         4: ('Mixed Dryland/Irrigated Cropland and Pasture', '#F9FF56'),
         5: ('Cropland/Grassland Mosaic', '#DEFF68'),
         6: ('Cropland/Woodland Mosaic', '#FFE36B'),
         7: ('Grassland', '#FF9900'),
         8: ('Shrubland', '#993366'),
         9: ('Mixed Shrubland/Grassland', '#FFCC99'),
        10: ('Savanna', '#FFCC00'),
        11: ('Deciduous Broadleaf Forest', '#99FF99'),
        12: ('Deciduous Needleleaf Forest', '#99CC00'),
        13: ('Evergreen Broadleaf Forest', '#00FF00'),
        14: ('Evergreen Needleleaf Forest', '#008000'),
        15: ('Mixed Forest', '#339966'),
        16: ('Water Bodies', '#000080'),
        17: ('Herbaceous Wetland', '#008299'),
        18: ('Wooded Wetland', '#006699'),
        19: ('Barren or Sparsely Vegetated', '#808080'),
        20: ('Herbaceous Tundra', '#378754'),
        21: ('Wooded Tundra', '#008833'),
        22: ('Mixed Tundra', '#4A8760'),
        23: ('Bare Ground Tundra','#748760'),
        24: ('Snow or Ice', '#BAECFF'),
        25: ('Playa', '#C2DFA9'),
        26: ('Lava', '#C23E29'),
        27: ('White Sand', '#DEE8CD'),
        28: ('Lake', '#0000FF'),
        31: ('Low Intensity Residential', '#686868'),
        32: ('High Intensity Residential', '#515151'),
        33: ('Industrial or Commercial', '#2D2D2D')
    },
    'MODIFIED_IGBP_MODIS_NOAH': {
         1: ('Evergreen Needleleaf Forest', '#008000'),
         2: ('Evergreen Broadleaf Forest', '#00FF00'),
         3: ('Deciduous Needleleaf Forest', '#99CC00'),
         4: ('Deciduous Broadleaf Forest', '#99FF99'),
         5: ('Mixed Forests', '#339966'),
         6: ('Closed Shrublands', '#993366'),
         7: ('Open Shrublands', '#FFCC99'),
         8: ('Woody Savannas', '#CCFFCC'),
         9: ('Savannas', '#FFCC00'),
        10: ('Grasslands', '#FF9900'),
        11: ('Permanent wetlands', '#006699'),
        12: ('Croplands', '#FFFF00'),
        13: ('Urban and Built-Up', '#FF0000'),
        14: ('Cropland/Natural Vegetation Mosaic', '#999966'),
        15: ('Snow and Ice', '#BAECFF'),
        16: ('Barren or Sparsely Vegetated', '#808080'),
        17: ('Water', '#000080'),
        18: ('Wooded Tundra', '#008833'),
        19: ('Mixed Tundra', '#4A8760'),
        20: ('Barren Tundra', '#748760'),
        21: ('Lake', '#0000FF'),
        31: ('Low Intensity Residential', '#686868'),
        32: ('High Intensity Residential', '#515151'),
        33: ('Industrial or Commercial', '#2D2D2D')
    }
}
