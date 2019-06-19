# -*- coding: utf-8 -*-
"""
Created on Mon Feb  4 12:54:01 2019

@author: disbr007
"""

import geopandas as gpd
import pandas as pd
#import numpy as np
import os, tqdm

from dataframe_utils import determine_id_col, determine_stereopair_col


def type_parser(filepath):
    '''
    takes a file path (or dataframe) in and determines whether it is a dbf, 
    excel, txt, csv (or df), ADD SUPPORT FOR SHP****
    '''
    if type(filepath) == str:
        ext = os.path.splitext(filepath)[1]
        if ext == '.csv':
            with open(filepath, 'r') as f:
                content = f.readlines()
                for row in content[0]:
                    if len(row) == 1:
                        return 'id_only_txt' # txt or csv with just ids
                    elif len(row) > 1:
                        return 'csv' # csv with columns
                    else:
                        print('Error reading number of rows in csv.')
        elif ext == '.txt':
            return 'id_only_txt' 
        elif ext in ('.xls', '.xlsx'):
            return 'excel'
        elif ext == '.dbf':
            return 'dbf'
        elif ext == '.shp':
            return 'shp'
    elif isinstance(filepath, gpd.GeoDataFrame):
        return 'df'
    else:
        print('Unrecognized file type.')


def get_stereopair_ids(df):
    '''
    Get's ids from stereopair column of df 
    '''
    stereopair_col = determine_stereopair_col(df)
    ids = list(df[stereopair_col])
    
    return ids


def read_ids(ids_file, sep=None, stereo=False):
    '''Reads ids from a variety of file types. Can also read in stereo ids from applicable formats
    Supported types:
        .txt: one per line, optionally with other fields after "sep"
        .dbf: shapefile's associated dbf    
    '''
    ids = []
    # Determine file type
    file_type = type_parser(ids_file)
    # Text file
    if file_type == 'id_only_txt':
        with open(ids_file, 'r') as f:
            content = f.readlines()
            for line in content:
                if sep:
                    # Assumes id is first
                    the_id = line.split(sep)[0]
                    the_id = the_id.strip()
                else:
                    the_id = line.strip()
                ids.append(the_id)
    # DBF
    elif file_type == 'dbf':
        df = gpd.read_file(ids_file)
        id_col = determine_id_col(df)
        df_ids = list(df[id_col])
        for each_id in df_ids:
            ids.append(each_id)
        # If stereopairs are desired, find them
        sp_ids = get_stereopair_ids(df)
        for sp_id in sp_ids:
            ids.append(sp_id)
    else:
        print('Unsupported file type... {}'.format(file_type))
    return ids


def write_ids(ids, out_path, header=None):
    with open(out_path, 'w') as f:
        if header:
            f.write('{}\n'.format(header))
        for each_id in ids:
            f.write('{}\n'.format(each_id))


def combine_ids(*id_lists, write_path=None):
    '''
    Takes lists of ids and combines them into a new txt file
    ids_lists: txt files of one id per line to be combined
    '''
    comb_ids = []
    for each in id_lists:
        ids = read_ids(each)
        for i in ids:
            comb_ids.append(i)
    if write_path:
        with open(write_path, 'w') as out:
            for x in comb_ids:
                out.write('{}\n'.format(x))
    return comb_ids
    
    
def compare_ids(ids1_path, ids2_path, write_path=False):
    '''
    Takes two text files of ids, writes out unique to list 1, unique to list 2 and overlap
    '''
    # Read in both ids as sets
    ids1 = set(read_ids(ids1_path))
    ids2 = set(read_ids(ids2_path))
    for i, id_list in enumerate([ids1, ids2]):
        print('IDs in list {}: {}'.format(i, len(id_list)))
    
    ## Get ids unique to each list and those common to both
    # Unique
    print('Finding unique...')
    ids1_u = ids1 - ids2
    ids2_u = ids2 - ids1
    # Common
    print('Finding common...')
    ids_c = [x for x in tqdm.tqdm(ids1) if x in ids2]
    
    if write_path:
        for id_list in [(ids1_path, ids1_u), (ids2_path, ids2_u)]:
            out_dir = os.path.dirname(id_list[0])
            name = os.path.basename(id_list[0]).split('.')[0]
            write_ids(id_list[1], os.path.join(out_dir, '{}_unique.txt'.format(name)))
        write_ids(ids_c, os.path.join(out_dir, 'common.txt'))
    
    return ids1_u, ids2_u, ids_c


def date_words(date=None, today=False):
    '''get todays date and convert to '2019jan07' style for filenaming'''
    from datetime import datetime, timedelta
    if today == True:
        date = datetime.now() - timedelta(days=1)
    else:
        date = datetime.strptime(date, '%Y-%m-%d')
    year = date.strftime('%Y')
    month = date.strftime('%b').lower()
    day = date.strftime('%d')
    date = r'{}{}{}'.format(year, month, day)
    return date


def archive_id_lut():
    from query_danco import query_footprint
    
    # Look up table names on danco
    print('Creating look-up table from danco table...')
    
    luts = {
            'GE01': 'index_dg_catalogid_to_ge_archiveid_ge01',
            'IK01': 'index_dg_catalogid_to_ge_archiveid_ik'
            }
    
    # Verify sensor
#    if sensor in luts:
#        pass
#    else:
#        print('{} look up table not found. Sensor must be in {}'.format(sensor, luts.keys()))
    
    # Create list to store tuples of (old id, new id)
    lut = []
    
    # Create tuples for each sensor, append to list
    for sensor in luts.keys():
        lu_df = query_footprint(layer=luts[sensor], table=True)
        # Combine old ids and new ids in tuples in a list
        sensor_lut = list(zip(lu_df.crssimageid, lu_df.catalog_identifier))
        for entry in sensor_lut:
            lut.append(entry)
    
    # Convert list of tuples to dictionary
    lu_dict = dict(lut)
    
    return lu_dict
    

def ge_ids2dg_ids(ids):
    '''
    takes a list of old GE ids and converts them to DG
    '''
    ## Assess what is in the list of ids
    print('Total ids in list: {}'.format(len(ids)))
    num_dg_style = len([x for x in ids if len(x) == 16])
    num_ge_style = len([x for x in ids if len(x) != 16])
    
    print('DG style ids: {}'.format(num_dg_style)) # DG style if 16 char (true?)
    print('Old style ids: {}'.format(num_ge_style))
    
    # Set up lists to store ids
    converted_ids = [] # ids to write out (DG style)
    convertable_ids = [] # ids that were converted (old style)
    not_conv_ids = [] # Ids that were not converted
    
    join_table = pd.DataFrame(columns=['catalogid', 'out_ids'])
    
    # Get list of all old ids for counting how many ids get converted
#    sensors = ['IK01', 'GE01']
#    for sensor in sensors:
#    print('Converting {} ids...'.format())
    # Look up table only for given sensor
    lu_dict = archive_id_lut()
    
    # Read ids into dataframe
    id_df = pd.DataFrame(ids, columns=['catalogid'])
    
    # Convert old ids that are in the look-up to DG style
    id_df['out_ids'] = id_df['catalogid'].map(lu_dict)
    
    # Copy ids that are already DG style to new column (where len catid is 16, make 'out_ids' = catid)     
    id_df.loc[id_df.catalogid.str.len() == 16, 'out_ids'] = id_df.catalogid

    
    join_table = pd.concat([join_table, id_df])
    
    # Add all converted, new style IDs to list
    for the_id in list(id_df.out_ids[~id_df.out_ids.isnull()]):
        converted_ids.append(the_id)

    # Create list of old style that were changed -> for removing from not converable (due to loop)
    for the_id in list(id_df.catalogid[~id_df.out_ids.isnull()]):
        convertable_ids.append(the_id)
            
    # List all not converted ids
    for the_id in list(id_df.catalogid[id_df.out_ids.isnull()]):
        not_conv_ids.append(the_id)

    converted_ids = list(set(converted_ids))
    not_conv_ids = list(set(not_conv_ids) - set(convertable_ids))
    
    print('Converted or already DG style ids: {}'.format(len(converted_ids)))
    print('Not convertable ids: {}'.format(len(not_conv_ids)))

    return converted_ids, not_conv_ids


