# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 08:46:36 2019

@author: disbr007
"""


import argparse
import sys

import geopandas as gpd

from archive_analysis_utils import get_count
from logging_utils import create_logger
from query_danco import list_danco_footprint, query_footprint


logger = create_logger(__file__, 'sh')

def main(args):
    grid_p = args.input_grid
    footprint_p = args.input_footprint
    out_path = args.out_path
    date_col = args.date_col

    grid = gpd.read_file(grid_p)
    
    danco_footprints = list_danco_footprint()
    if footprint_p in danco_footprints:
        logger.info('Loading footprint from danco...')
        footprint = query_footprint(footprint_p)
    else:
        logger.info('Loading footprint...')
        footprint = gpd.read_file(footprint_p)

    logger.info('Calculating density...')
    density = get_count(grid, footprint, date_col=date_col)
    logger.info('Writing density...')
    # Convert any tuple columns to strings (occurs with agg-ing same column multiple ways)
    density.columns = [str(x) if type(x) == tuple else x for x in density.columns]
    density.to_file(out_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('input_grid', type=str, help='Grid to count density on.')
    parser.add_argument('input_footprint', type=str, help='Footprint to calculate density of.')
    parser.add_argument('out_path', type=str, help='Path to write the density shapefile.')
    parser.add_argument('--date_col', type=str, help="""Column in input footprint holding dates
        ')                                              to return min and max dates""")
    
    args = parser.parse_args()
    
    main(args)
