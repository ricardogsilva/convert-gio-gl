#!/usr/bin/env python

'''
A script to convert DSSF files from the Geoland-2 project from HDF5 file to
georeferenced GeoTiffs.
'''

import os
import logging
import argparse
import numpy as np
import tables
from osgeo import gdal
from osgeo import osr

# TODO
# allow conversion of other datasets, not just the main one

class GeolandFileConverter(object):

    numpy_d_type = np.int16
    gdal_d_type = gdal.GDT_Int16
    pixel_size = 0.05 # degrees

    def convert_to_geotiff(self, file_path, output_dir, tolerance = 0.1):
        '''
        Inputs:

            file_path - A string with the full path of the HDF5 file to convert

            output_dir - A string with the output directory for the converted
                files.
        '''

        outDriver = gdal.GetDriverByName('GTiff')
        out_name = ''.join((os.path.basename(file_path), '.tif'))
        out_path = os.path.join(output_dir, out_name)
        in_dataset = tables.openFile(file_path)
        main_dataset = in_dataset.root._v_attrs['PRODUCT']
        n_lines = int(in_dataset.root._v_attrs['NL'])
        n_cols = int(in_dataset.root._v_attrs['NC'])
        node = in_dataset.getNode('/%s' % main_dataset)
        missing_value = int(node._v_attrs['MISSING_VALUE'])
        scaling_factor = float(node._v_attrs['SCALING_FACTOR'])
        first_lat = int(in_dataset.root._v_attrs['FIRST_LAT'])
        first_lon = int(in_dataset.root._v_attrs['FIRST_LON'])
        data = node.read().astype(self.numpy_d_type)
        in_dataset.close()
        # dealing with the missing value and scaling factor
        data_mask = abs(data - missing_value) > tolerance
        missing_value_mask = abs(data - missing_value) <= tolerance
        data[data_mask] = data[abs(data - missing_value) > tolerance] / scaling_factor
        data[missing_value_mask] = missing_value
        output = outDriver.Create(str(out_path), n_cols, n_lines,
                                  1, self.gdal_d_type)
        outBand = output.GetRasterBand(1)
        outBand.WriteArray(data, 0, 0)
        ullon = first_lon * 1.0 - self.pixel_size / 2.0
        ullat = first_lat * 1.0 + self.pixel_size / 2.0
        output.SetGeoTransform([ullon, self.pixel_size, 0, ullat, 0,
                              -self.pixel_size])
        srs = osr.SpatialReference()
        srs.SetWellKnownGeogCS("WGS84")
        output.SetProjection(srs.ExportToWkt())
        outBand.SetNoDataValue(missing_value)
        outBand.FlushCache()
        output = None


def _create_output_dir(out_dir):
    if not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir)
        except OSError as err:
            print(err)
            raise SystemExit

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output_dir', help='The directory where to save '
                        'converted files')
    parser.add_argument('HDF5_files', nargs='+', help='HDF5 files to '
                        'convert to GeoTiff')
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()
    logger.debug('Creating output directory...')
    _create_output_dir(args.output_dir)
    converter = GeolandFileConverter()
    for index, file_path in enumerate(args.HDF5_files):
        logger.info('Processing file (%i/%i) %s' % (index+1,
                                                    len(args.HDF5_files),
                                                    file_path))
        converter.convert_to_geotiff(file_path, args.output_dir)


