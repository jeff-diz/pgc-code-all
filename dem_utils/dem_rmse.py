# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 22:18:52 2020

@author: disbr007
"""

import argparse
import logging.config
import numpy as np
import os
import random
import matplotlib.pyplot as plt

from osgeo import gdal, osr
import geopandas as gpd
from shapely.geometry import Point


from misc_utils.RasterWrapper import Raster
from misc_utils.logging_utils import create_logger, LOGGING_CONFIG
from misc_utils.gdal_tools import clip_minbb


logger = create_logger(__name__, 'sh', 'DEBUG')


# TODO: Add shape1 == shape2 checking and 
# TODO: if not clip to minimum bounding box (in memory)

# TODO: Add support for saving image/tif of raw differences

def dem_rmse(dem1_path, dem2_path, max_diff=None, outfile=None, out_diff=None, plot=False,
             show_plot=False, save_plot=None, bins=10, log_scale=True):
    # Load DEMs as arrays
    logger.info('Loading DEMs...')
    dem1 = Raster(dem1_path)
    dem2 = Raster(dem2_path)

    if dem1.geotransform != dem2.geotransform:
        logger.warning('''DEM geotransforms do not match. 
                          Clipping to minimum bounding box in memory....''')
        dem1 = None
        dem2 = None
        clipped = clip_minbb(rasters=[dem1_path, dem2_path],
                             in_mem=True,
                             out_format='vrt')
        logger.debug('Clipping complete. Reloading DEMs...')
        dem1 = Raster(clipped[0])
        arr1 = dem1.MaskedArray
        dem1 = None
        logger.debug('DEM1 loaded and array extracted...')
        dem2 = Raster(clipped[1])
        arr2 = dem2.MaskedArray
        dem2 = None
        logger.debug('DEM2 loaded and array extracted...')
    else:
        arr1 = dem1.MaskedArray
        dem1 = None
        arr2 = dem2.MaskedArray
        dem2 = None


    # Compute RMSE
    logger.info('Computing RMSE...')
    diffs = arr1 - arr2
    
    # Remove any differences bigger than max_diff
    if max_diff:
        logger.debug('Checking for large differences, max_diff: {}'.format(max_diff))
        size_uncleaned = diffs.size
        diffs = diffs[abs(diffs) < max_diff]
        size_cleaned = diffs.size
        if size_uncleaned != size_cleaned:
            logger.debug('Removed differences over max_diff ({}) from RMSE calculation...'.format(max_diff))
            logger.debug('Size before: {:,}'.format(size_uncleaned))
            logger.debug('Size after:  {:,}'.format(size_cleaned))
            logger.debug('Pixels removed: {:.2f}% of overlap area'.format(((size_uncleaned-size_cleaned)/size_uncleaned)*100))
    
    sq_diff = diffs**2
    mean_sq = sq_diff.sum() / sq_diff.count()
    logger.debug('Mean square error: {}'.format(mean_sq))
    rmse = np.sqrt(mean_sq)

    # Report differences
    diffs_valid_count = diffs.count()
    min_diff = diffs.min()
    max_diff = diffs.max()
    logger.debug('Minimum difference: {:.2f}'.format(min_diff))
    logger.debug('Maximum difference: {:.2f}'.format(max_diff))
    logger.debug('Pixels considered: {:,}'.format(diffs_valid_count))
    logger.info('RMSE: {:.2f}'.format(rmse))

    # Write text file of results
    if outfile:
        with open(outfile, 'w') as of:
            of.write("DEM1: {}\n".format(dem1_path))
            of.write("DEM2: {}\n".format(dem2_path))
            of.write('RMSE: {:.2f}\n'.format(rmse))
            of.write('Pixels considered: {:,}\n'.format(diffs_valid_count))
            of.write('Minimum difference: {:.2f}\n'.format(min_diff))
            of.write('Maximum difference: {:.2f}\n'.format(max_diff))
    
    # Write raster file of results
    if out_diff:
        logger.info('Out diff not supported, skipping writing.')
        # dem1.WriteArray(diffs, out_diff)
        
    # Plot results
    # TODO: Add legend
    # TODO: Incorporate min/max differences based on max_diff argument
    if plot:
        plt.style.use('ggplot')
        fig, ax = plt.subplots(1, 1)
        ax.hist(diffs.compressed().flatten(), log=log_scale, bins=bins, edgecolor='white', 
                alpha=0.875)
        ax.annotate('RMSE: {:.3f}'.format(rmse),
                    xy=(76, 0.75),
                    xycoords='axes fraction')
        plt.legend(loc="upper left")
        plt.tight_layout()
        
        if save_plot:
            plt.savefig(save_plot)
        if show_plot:
            plt.show()
        
    return rmse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('dem1', type=os.path.abspath,
                        help='Path to the first DEM')
    parser.add_argument('dem2', type=os.path.abspath,
                        help='Path to the second DEM')
    parser.add_argument('--max_diff', type=int, default=10,
                        help='Maximum difference to include in RMSE calculation.')
    parser.add_argument('--outfile', type=os.path.abspath,
                        help='Path to a txt file to write RMSE to.')
    parser.add_argument('--out_diff', type=os.path.abspath,
                        help='Path to write out difference raster.')
    parser.add_argument('--plot', action='store_true',
                        help='Plot the differences.')
    parser.add_argument('--show_plot', action='store_true',
                        help='Opens the plot in a new window.')
    parser.add_argument('--save_plot', type=os.path.abspath,
                        help="Save the plot to this location.")
    parser.add_argument('--bins', type=int, default=10,
                        help='Number of bins to use for histogram.')
    parser.add_argument('--no_log_scale', action='store_true',
                        help='Do not use log scale for counts of histogram.')
    
    args = parser.parse_args()
    
    dem1_path = args.dem1
    dem2_path = args.dem2
    outfile = args.outfile
    max_diff = args.max_diff
    out_diff = args.out_diff
    plot = args.plot
    show_plot = args.show_plot
    save_plot = args.save_plot
    bins = args.bins
    log_scale = not args.no_log_scale # if no_log_scale is passed, log_scale should be False
        
    dem_rmse(dem1_path=dem1_path, 
             dem2_path=dem2_path, 
             outfile=outfile,
             max_diff=max_diff,
             out_diff=out_diff,
             plot=plot,
             show_plot=show_plot,
             save_plot=save_plot,
             bins=bins,
             log_scale=log_scale)