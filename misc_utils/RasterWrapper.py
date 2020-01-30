# -*- coding: utf-8 -*-
"""
Created on Fri Jul 19 10:20:36 2019

@author: disbr007

"""
import logging.config
import numpy as np
import numpy.ma as ma

from osgeo import gdal, osr, ogr

from misc_utils.logging_utils import create_logger, LOGGING_CONFIG

# logger = create_logger('RasterWrapper.py', 'sh')

logging.config.dictConfig(LOGGING_CONFIG('DEBUG'))
logger = logging.getLogger(__name__)


class Raster():
    '''
    A class wrapper using GDAL to simplify working with rasters.
    Basic functionality:
        -read array from raster
        -read stacked array
        -write array out with same metadata
        -sample raster at point in geocoordinates
        -sample raster with window around point
    '''
    
    def __init__(self, raster_path):
        self.data_src = gdal.Open(raster_path)
        self.geotransform = self.data_src.GetGeoTransform()
        
        self.prj = osr.SpatialReference()
        self.prj.ImportFromWkt(self.data_src.GetProjectionRef())
        # try:
        #     self.epsg = self.prj.GetAttrValue("PROJCS|GEOGCS|AUTHORITY", 1)
        # except KeyError as e:
        #     logger.error(""""Trying to get EPSG of unprojected Raster,
        #                      not currently supported.""")
        #     raise e
        self.prj.wkt = self.prj.ExportToWkt()
        
        self.x_sz = self.data_src.RasterXSize
        self.y_sz = self.data_src.RasterYSize
        
        self.x_origin = self.geotransform[0]
        self.y_origin = self.geotransform[3]
        
        self.pixel_width = self.geotransform[1]
        self.pixel_height = self.geotransform[5]
        
        self.nodata_val = self.data_src.GetRasterBand(1).GetNoDataValue()
        self.dtype = self.data_src.GetRasterBand(1).DataType
        
        ## Get the raster as an array
        ## Defaults to band 1 -- use ReadArray() to return stack 
        ## of multiple bands
        self.Array = self.data_src.ReadAsArray()
        self.Mask = self.Array == self.nodata_val
        self.MaskedArray = ma.masked_array(self.Array, mask=self.Mask)
    
    
    def raster_bounds(self):
        '''
        GDAL only version of getting bounds for a single raster.
        '''
        gt = self.geotransform
        
        ulx = gt[0]
        uly = gt[3]
        lrx = ulx + (gt[1] * self.x_sz)
        lry = uly + (gt[5] * self.y_sz)
        
        return ulx, lry, lrx, uly
    
    
    def GetBandAsArray(self, band_num, mask=True):
        """
        Parameters
        ----------
        band_num : INT
            The band number to return.
        mask : BOOLEAN
            Whether to mask to array that is returned
        
        Returns
        -------
        np.ndarray
        
        """
        band_arr = self.data_src.GetRasterBand(band_num).ReadAsArray()
        # TODO: add masking support
        # band_nodata_val = band.GetNoDataValue()
        # band_mask = band_arr == band_nodataval
        
        return band_arr
    

    def NDVI(self, red_num, nir_num):
        red = self.GetBandAsArray(red_num)
        nir = self.GetBandAsArray(nir_num)
        ndvi = (nir - red) / (nir + red)
        
        return ndvi
    
    
    def ArrayWindow(self, projWin):
        """
        Takes a projWin in geocoordinates, converts
        it to pixel coordinates and returns the 
        array referenced
        """
        xmin, ymin, xmax, ymax = self.projWin2pixelWin(projWin)
        self.arr_window = self.Array[ymin:ymax, xmin:xmax]
        
        return self.arr_window


    def geo2pixel(self, geocoord):
        """
        Convert geographic coordinates to pixel coordinates
        """

        py = int(np.around((geocoord[0] - self.geotransform[3]) / self.geotransform[5]))
        px = int(np.around((geocoord[1] - self.geotransform[0]) / self.geotransform[1]))
        
        return (py, px)
    
    
    def projWin2pixelWin(self, projWin):
        """
        Convert projWin in geocoordinates to pixel coordinates
        """
        ul = (projWin[1], projWin[0])
        lr = (projWin[3], projWin[2])
        
        puly, pulx = self.geo2pixel(ul)
        plry, plrx = self.geo2pixel(lr)
        
        return [pulx, puly, plrx, plry]    
        
    
    def ReadStackedArray(self, stacked=True):
        '''
        Read raster as array, stacking multiple bands as either stacked array or multiple arrays
        stacked: boolean - specify False to return a separate array for each band
        '''
        ## Get number of bands in raster
        num_bands = self.data_src.RasterCount
        ## For each band read as array and add to list
        band_arrays = []
        for band in range(num_bands):
            band_arr = self.data_src.GetRasterBand(band).ReadAsArray()
            band_arrays.append(band_arr)
        
        ## If stacked is True, stack bands and return
        if stacked == True:
            ## Control for 1 band rasters as stacked=True is the default
            if num_bands > 1:
                stacked_array = np.dstack(band_arrays)
            else:
                stacked_array = band_arrays[0]
                
            return stacked_array
        
        ## Return list of band arrays
        else:
            return band_arrays
            
        
    def WriteArray(self, array, out_path):
        '''
        Writes the passed array with the metadata of the current raster object
        as new raster.
        '''
        # Get dimensions of input array
        try:
            rows, cols, depth = array.shape
        except ValueError as e:
            rows, cols = array.shape
            depth = 1
        
        # Create output file
        fmt = 'GTiff'
        driver = gdal.GetDriverByName(fmt)
        dst_ds = driver.Create(out_path, self.x_sz, self.y_sz, 1, self.dtype)
        dst_ds.SetGeoTransform(self.geotransform)
        dst_ds.SetProjection(self.prj.ExportToWkt())

        # Loop through each layer of array and right as band
        for i in range(depth):        
            band = i+1
            dst_ds.GetRasterBand(band).WriteArray(array)
            dst_ds.GetRasterBand(band).SetNoDataValue(self.nodata_val)
        
        dst_ds = None
        
        
    def SamplePoint(self, point):
        '''
        Samples the current raster object at the given point. Must be the
        sampe coordinate system used by the raster object.
        point: tuple of (y, x) in geocoordinates
        '''
        ## Convert point geocoordinates to array coordinates
        py = int(np.around((point[0] - self.geotransform[3]) / self.geotransform[5]))
        px = int(np.around((point[1] - self.geotransform[0]) / self.geotransform[1]))
        ## Handle point being out of raster bounds
        try:    
            point_value = self.Array[py, px]
        except IndexError as e:
            logger.warning('Point not within raster bounds.')
            logger.warning(e)
            point_value = None
        return point_value
    
    
    def SampleWindow(self, center_point, window_size, agg='mean', grow_window=False, max_grow=100000):
        '''
        Samples the current raster object using a window centered 
        on center_point. Assumes 1 band raster.
        center_point: tuple of (y, x) in geocoordinates
        window_size: tuple of (y_size, x_size) as number of pixels (must be odd)
        agg: type of aggregation, default is mean, can also me sum, min, max
        grow_window: set to True to increase the size of the window until a valid value is 
                        included in the window
        max_grow: the maximum area (x * y) the window will grow to          
        '''
        
        
        def window_bounds(window_size, py, px):
            '''
            Takes a window size and center pixel coords and 
            returns the window bounds as ymin, ymax, xmin, xmax
            window_size: tuple (3,3)
            py: int 125
            px: int 100
            '''
            ## Get window around center point
            # Get size in y, x directions
            y_sz = window_size[0]
            y_step = int(y_sz / 2)
            x_sz = window_size[1]
            x_step = int(x_sz / 2)
            
            # Get pixel locations of window bounds
            ymin = py - y_step
            ymax = py + y_step + 1 # slicing doesn't include stop val so add 1
            xmin = px - x_step
            xmax = px + x_step + 1 
            
            return ymin, ymax, xmin, xmax
        
        
        ## Convert center point geocoordinates to array coordinates
        py = int(np.around((center_point[0] - self.geotransform[3]) / self.geotransform[5]))
        px = int(np.around((center_point[1] - self.geotransform[0]) / self.geotransform[1]))
        
        ## Handle window being out of raster bounds
        try:
            growing = True
            while growing == True:
                ymin, ymax, xmin, xmax = window_bounds(window_size, py, px)
                window = self.Array[ymin:ymax, xmin:xmax].astype(np.float32)
                window = np.where(window==-9999.0, np.nan, window)
                
                ## Test for window with all nans to avoid getting 0's for all nans
                # Returns an array of True/False where True is valid values
                window_valid = window == window
                
                if True in window_valid:
                    ## Window contains at least one valid value, do aggregration
                    agg_lut = {
                        'mean': np.nanmean(window),
                        'sum': np.nansum(window),
                        'min': np.nanmin(window),
                        'max': np.nanmax(window)
                        }
                    window_agg = agg_lut[agg]
                    
                    # Do not grow if valid values found
                    growing = False
                    
                else:
                    ## Window all nan's, return nan value (arbitratily picking -9999)
                    # If grow_window is True, increase window (y+2, x+2)
                    if grow_window == True:
                        window_size = (window_size[0]+2, window_size[1]+2)
                    # If grow_window is False, return no data and exit while loop
                    else:
                        window_agg = -9999
                        growing = False
            
            
        except IndexError as e:
            logger.error('Window bounds not within raster bounds.')
            logger.error(e)
            window_agg = None
            
        return window_agg


def same_srs(raster1, raster2):
    """
    Compares the spatial references of two rasters.

    Parameters
    ----------
    raster1 : os.path.abspath
        Path to the first raster.
    raster2 : os.path.abspath
        Path to the second raster.

    Returns
    -------
    BOOL : True is match.

    """
    r1 = Raster(raster1)
    r1_srs = r1.prj
    # r1 = None
    
    r2 = Raster(raster2)
    r2_srs = r2.prj
    # r2 = None
    
    result = r1_srs.IsSame(r2_srs)
    if result == 1:
        same = True
    elif result == 0:
        same = False
    else:
        logger.error('Unknown return value from IsSame, expected 0 or 1: {}'.format(result))
    return same
