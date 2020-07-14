# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 12:03:31 2019

@author: disbr007
"""
import copy
import math
import numpy as np

import geopandas as gpd
import pandas as pd
import tqdm
from fiona.crs import from_epsg, from_string

from misc_utils.logging_utils import create_logger

logger = create_logger(__name__, 'sh', 'DEBUG')


# def area_calc(geodataframe, area_col='area_sqkm'):
#     '''
#     Takes a geodataframe in and calculates the area based
#     on UTM zones of each feature. Returns a geodataframe
#     with added 'utm_sqkm' column and 'polar_area' column
#     for those features north of south of utm zones boundaries
#     geodataframe: geodataframe
#     area_col: name of column to hold area
#     '''
#     gdf = copy.deepcopy(geodataframe)
#
#     ## Load UTM zones shapefile
#     utm_zone_path = r'E:\disbr007\general\UTM_Zone_Boundaries\UTM_Zone_Boundaries.shp'
#     utm_zones = gpd.read_file(utm_zone_path, driver='ESRI Shapefile')
#
#     ## Locate zone of each feature based on centroid
#     # Get original geometry column name and original crs
#     geom_name = gdf.geometry.name
#     source_crs = gdf.crs
#     # Get original list of columns - add new area col
#     cols = list(gdf)
# #    area_col = 'sqkm_utm'
#     area_col = area_col
#     # area_col = 'polar_area'
#     cols.append(area_col)
#     # cols.append(area_col)
#     # gdf[area_col] = np.nan
#     # gdf[area_col] = np.nan
#
#     # Use centroid to locate UTM zone
#     gdf['centroid'] = gdf.centroid
#     gdf.set_geometry('centroid', inplace=True)
#     # Find points north and south of UTM zone boundary
#     north_pole = gdf[gdf.centroid.y >= 84]
#     south_pole = gdf[gdf.centroid.y <= -80]
#
#     # Find all points that fall in a utm zone
#     gdf = gpd.sjoin(gdf, utm_zones, how='left', op='within')
#     gdf.drop('centroid', axis=1, inplace=True)
#
#     # Reset to original geometry
#     gdf.set_geometry(geom_name, inplace=True)
#
#     ## Loop through all zones found, reproject to relevant utm zone and calculate area
#     dfs_with_area = []
# #    for utm_zone, df in tqdm.tqdm(gdf.groupby('Zone_Hemi')):
#     for utm_zone, df in gdf.groupby('Zone_Hemi'):
#         zone = utm_zone.split(',')[0].replace(' ', '')
#         hemi = utm_zone.split(',')[1].replace(' ', '')
#         if hemi == 's':
#             proj4 = r'+proj=utm +zone={} +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
#         elif hemi == 'n':
#             proj4 = r'+proj=utm +zone={} +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(zone)
#         logger.debug('Projecting to: {}'.format(proj4))
#         df.geometry = df.geometry.to_crs(proj4)
#         df.crs = from_string(proj4)
#         logger.debug('Calculating area in {} column...'.format(area_col))
#         df[area_col] = df.geometry.area / 10**6
#         df.geometry = df.geometry.to_crs(source_crs)
#         df.crs = source_crs
#         df = df[cols]
#         dfs_with_area.append(df)
#
#     ## Calculate south pole areas using Anatarctic polar stereographic and north pole using Arctic polar stereographic
#     for each_df, epsg in [(south_pole, '3031'), (north_pole, '3995')]:
#         # Return to orginal geometry
#         each_df.set_geometry(geom_name, inplace=True)
#         each_df = each_df.to_crs({'init':'epsg:{}'.format(epsg)})
#         logger.debug('Calculating area in {} column...'.format(area_col))
#         each_df[area_col] = each_df.geometry.area / 10**6
#         each_df = each_df.to_crs(source_crs)
#         each_df = each_df[cols]
#         dfs_with_area.append(each_df)
#
#     for df in dfs_with_area:
#         print(list(df))
#     recombine = pd.concat(dfs_with_area)
#     recombine = recombine[cols]
#     recombine[area_col] = np.where(recombine[area_col].isna(), recombine[area_col], np.NaN)
#
#     return recombine


def area_calc(geodataframe, area_col='area_sqkm', units='sqkm', polar=True):
    gdf = copy.deepcopy(geodataframe)

    src_geom_name = gdf.geometry.name
    src_crs = gdf.crs
    src_cols = list(gdf)
    src_cols.append(area_col)

    epsg_col = 'epsg_col'
    gdf[epsg_col] = gdf.geometry.centroid.apply(lambda x: find_epsg(x))

    gdf_area = gpd.GeoDataFrame()
    for epsg, df in gdf.groupby(epsg_col):
        logger.debug('Calculating areas for epsg: {}, Features: {}'.format(epsg, len(df)))
        reprj = df.to_crs('epsg:{}'.format(epsg))
        if units == 'sqkm':
            reprj[area_col] = reprj.geometry.area / 10e6
        elif units == 'sqm':
            reprj[area_col] = reprj.geometry.area
        else:
            logger.error('Unrecognized units argument: {}'.format(units))

        gdf_area = pd.concat([gdf_area, reprj])

    gdf_area = gdf_area[src_cols]

    return gdf_area


def find_epsg(point):
    if point.y >= 60:
        epsg = "3413"
    elif point.y <= -60:
        epsg = "3031"
    else:
        zone_number = int(math.ceil((point.x + 180) / 6))
        if point.y <= 0:
            epsg = "327{}".format(str(zone_number).zfill(2))
        else:
            epsg = "326{}".format(str(zone_number).zfill(2))

    return epsg
