#!/usr/bin/env python

"""
Unit testing for detector correction module from package
NetronImaging
"""
import os
import pytest
import numpy as np
from neutronimaging.detector_correction import correct_images, load_images, read_shutter_count
from neutronimaging.detector_correction import read_shutter_time
from neutronimaging.detector_correction import read_spectra
from neutronimaging.detector_correction import merge_meta_data
from neutronimaging.detector_correction import calc_pixel_occupancy_probability


_file_root = os.path.dirname(os.path.abspath(__file__))
test_data_dir = os.path.join(_file_root, "../data")


def test_calc_pixel_occupancy_probability():
    """Use the pre-calculated profile as reference"""
    # prep
    np.random.seed(0)
    # process meta data for testing data
    shutter_counts_file = os.path.join(test_data_dir, "OB_1_005_ShutterCount.txt")
    df_shutter_count = read_shutter_count(shutter_counts_file)
    shutter_time_file = os.path.join(test_data_dir, "OB_1_005_ShutterTimes.txt")
    df_shutter_time = read_shutter_time(shutter_time_file)
    spectra_file = os.path.join(test_data_dir, "OB_1_005_Spectra.txt")
    df_spectra = read_spectra(spectra_file)
    df_meta = merge_meta_data(df_shutter_count, df_shutter_time, df_spectra)
    # load testing images
    o_norm = load_images(test_data_dir)
    # calculate pixel occupancy probability
    pops = calc_pixel_occupancy_probability(o_norm, df_meta)
    pop_prof = [np.mean(img) for img in pops]

    # load reference from cache
    with np.load(os.path.join(test_data_dir, "ref_pop_prof.npz")) as data:
        ref_pop_prof = data["arr_0"]

    # check if close
    np.testing.assert_array_almost_equal(pop_prof, ref_pop_prof)


def test_correct_images():
    """Use profile along shutter index axis for testing"""
    # prep
    np.random.seed(0)
    # process meta data for testing data
    shutter_counts_file = os.path.join(test_data_dir, "OB_1_005_ShutterCount.txt")
    df_shutter_count = read_shutter_count(shutter_counts_file)
    shutter_time_file = os.path.join(test_data_dir, "OB_1_005_ShutterTimes.txt")
    df_shutter_time = read_shutter_time(shutter_time_file)
    spectra_file = os.path.join(test_data_dir, "OB_1_005_Spectra.txt")
    df_spectra = read_spectra(spectra_file)
    df_meta = merge_meta_data(df_shutter_count, df_shutter_time, df_spectra)
    # load testing images
    o_norm = load_images(test_data_dir)

    # perform the correction
    imgs = correct_images(o_norm, df_meta)
    img_mean_prof = [np.mean(img) for img in imgs]

    # load reference profile
    with np.load(os.path.join(test_data_dir, "ref_img_mean_prof.npz")) as data:
        ref_img_mean_prof = data["arr_0"]

    # check
    np.testing.assert_array_almost_equal(img_mean_prof, ref_img_mean_prof)


if __name__ == '__main__':
    pytest.main([__file__])