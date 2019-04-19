# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 11:58:03 2019

@author: disbr007
Determine the number of unique cross track catalog ids not ordered, by month, overlap area, sensor
"""

import geopandas as gpd
import pandas as pd


## Xtrack data prep
# Load crosstrack database
xtrack_path = r"C:\Users\disbr007\imagery\dg_cross_track_2019jan09_deliv.gdb"
xtrack = gpd.read_file(xtrack_path, driver='OpenFileGDB', layer=1)
print('xtrack db loaded into geopandas')

# Assign each pair of catalog ids to a overlap bin, first by listed bins, second line by 250 increments to max of sqkm field
xtrack['ovlp_cat'] = pd.cut(xtrack.sqkm, [0, 250, 500, 1000, 999999], labels=['0-249', '250-500', '500-1000', '1000+'])
xtrack['ovlp_cat_fine'] = pd.cut(xtrack.sqkm, [x for x in range(0, int(max(xtrack.sqkm)+250), 250)])

# Split into '1' and '2' xtrack dataframes - 
# keep overlap area ids in both, acquire date, area (remove one later), overlap bins

# Drop geometry and other unncessary columns
xtrack1_cols = ['catalogid1', 'acqdate1', 'sqkm', 'ovlp_cat', 'ovlp_cat_fine']
xtrack2_cols = ['catalogid2', 'acqdate2', 'sqkm', 'ovlp_cat', 'ovlp_cat_fine']

# Drop unnecessary columns
xtrack1 = xtrack[xtrack1_cols]
xtrack2 = xtrack[xtrack2_cols]
# Set second set of ids to 0 so we don't count the same pair's area twice
xtrack2['sqkm'] = 0.0
del xtrack

# Stack '1' and '2' xtrack dataframes
# Rename columns for stacking
col_rename = {
        'catalogid1': 'catalogid',
        'catalogid2': 'catalogid',
        'acqdate1': 'acqdate',
        'acqdate2': 'acqdate'
        }
xtrack1.rename(index=str, columns=col_rename, inplace=True)
xtrack2.rename(index=str, columns=col_rename, inplace=True)
# Stack on top of each other
xtrack = pd.concat([xtrack1, xtrack2])

# Remove duplicate ids, keeping largest area id, so that an id in the 1000+ bin isn't also in the 500-1000 bin
xtrack.sort_values(by=['sqkm'])
xtrack.drop_duplicates('catalogid', keep='first', inplace=True)

# Determine platform of id
platform_code = {
        '101': 'QB02',
        '102': 'WV01',
        '103': 'WV02',
        '104': 'WV03',
        '105': 'GE01',
        '200': 'IK01'
        }
# Use first three characters of catalogid to determine platform
xtrack['platform'] = xtrack['catalogid'].str.slice(0,3).map(platform_code)

## Determine 'onhand' (PGC + NASA + ordered) - derived from another script that adds those three
onhand_ids_path = r'C:/Users/disbr007/imagery_orders/not_onhand/onhand_ids.txt'
oh_ids = []
with open(onhand_ids_path, 'r') as f:
    content = f.readlines()
    for line in content:
        oh_ids.append(line.strip())

# Determine xtrack onhand
xtrack['onhand'] = xtrack['catalogid'].isin(oh_ids)
xtrack = xtrack.set_index(pd.to_datetime(xtrack['acqdate']))


## GROUPING / RESAMPLING
aggregation = {
        'catalogid': 'nunique',
        'sqkm': 'sum'
        }
# Group by area overlap, unstack 'onhand/not onhand' from index
histo_xtrack = xtrack.groupby(['ovlp_cat', 'onhand']).agg(aggregation)
histo_xtrack = histo_xtrack.unstack(level=1)
# Group by area overlap with more bins
histo_xtrack_fine = xtrack.groupby(['ovlp_cat_fine', 'onhand']).agg(aggregation)
histo_xtrack_fine = histo_xtrack_fine.unstack(level=1)

## Monthly grouping
monthly_xtrack = xtrack.groupby([pd.Grouper(freq='M'), 'onhand', 'ovlp_cat', 'platform']).agg(aggregation)

monthly_xtrack = monthly_xtrack.unstack(level=-1) # Unstack 'onhand' column
monthly_xtrack = monthly_xtrack.unstack(level=-1) # Unstack platform column

# Rename to reflect aggregation
col_rename = {
        'catalogid': 'Unique_Strips',
        'sqkm': 'Total_Area',
        True: 'Onhand',
        False: 'Not onhand'}
monthly_xtrack.rename(index=str, columns=col_rename, inplace=True)
       

## Write to excel: monthly unique strips, w/ overlap area, and sensor, and totals
excel_path = r'C:\Users\disbr007\imagery\not_onhand\xtrack.xlsx'
excel_writer = pd.ExcelWriter(excel_path)
monthly_xtrack.to_excel(excel_writer, index=True)
histo_xtrack.to_excel(excel_writer, index=True, sheet_name='histo')
histo_xtrack_fine.to_excel(excel_writer, index=True, sheet_name='histo_fine')
excel_writer.save()
pd.to_pickle(monthly_xtrack, r'C:\Users\disbr007\imagery\not_onhand\xtrack.pkl')