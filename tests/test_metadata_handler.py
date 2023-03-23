#!/usr/bin/env python

"""Unit test for metadata handler module from package NeutronImaging"""

import os
import pytest
from neutronimaging.metadata_handler import MetadataHandler
from neutronimaging.mars.metadata_handler import MetadataName

def test_get_time_stamp():
    """Test get_time_stamp method."""
    # Case_0: tiff file
    _file_root = os.path.dirname(os.path.abspath(__file__))
    test_data_dir = os.path.join(_file_root, "../data")
    file_name = os.path.join(
        test_data_dir,
        "IPTS-20267/raw/radiographs/Jan07_2020_sam1_lightOff/20200107_sam1_D2O_LightOff_0030_0313.tiff")
    # process
    time_stamp = MetadataHandler.get_time_stamp(file_name, ext="tif")
    # test
    assert time_stamp == 1578444252.1587958

    # Case_1: fits file
    file_name = os.path.join(
        test_data_dir,
        "OB_1_005_00000.fits",
    )
    # process
    time_stamp = MetadataHandler.get_time_stamp(file_name, ext="fits")
    # test
    # NOTE: fits has no time stamp header, so we are using data
    # creation time instead, and the test has to be modified to
    # use os.path.getctime() instead of a hard-coded value.
    assert time_stamp == os.path.getctime(file_name)

    # Exception_0: non-supporting file type
    file_name = os.path.join(
        test_data_dir,
        "ref_pop_prof.npz",
    )
    # process
    with pytest.raises(NotImplementedError):
        MetadataHandler.get_time_stamp(file_name, ext="npz")

def test_convert_to_human_readable_format():
    # setup
    epoch_time = 1679594776.340314
    # process
    human_readable_time = MetadataHandler.convert_to_human_readable_format(epoch_time)
    # test
    assert human_readable_time == "2023-03-23 14:06:16"

def test_get_metadata():
    # case_0: empty file
    # setup
    file_name = ""
    # process
    metadata = MetadataHandler.get_metadata(file_name)
    # test
    assert metadata == {}

    # case_1: tiff file, all metadata
    # setup
    _file_root = os.path.dirname(os.path.abspath(__file__))
    test_data_dir = os.path.join(_file_root, "../data")
    file_name = os.path.join(
        test_data_dir,
        "IPTS-20267/raw/radiographs/Jan07_2020_sam1_lightOff/20200107_sam1_D2O_LightOff_0030_0313.tiff",
    )
    # process
    metadata = MetadataHandler.get_metadata(file_name)
    # test
    print(metadata)
    print(len(metadata))
    assert len(metadata) == 109

    # case_2: tiff file, specific metadata
    # setup
    list_metadata = [
        MetadataName.DETECTOR_MANUFACTURER,
        MetadataName.EXPOSURE_TIME,
    ]
    # process
    metadata = MetadataHandler.get_metadata(file_name, list_metadata)
    # test
    assert len(metadata) == 2
    assert metadata[MetadataName.DETECTOR_MANUFACTURER] == "ManufacturerStr:Andor"
    assert metadata[MetadataName.EXPOSURE_TIME] == "ExposureTime:30.000000"

def test_retrieve_metadata():
    # case_0: empty list
    # setup
    list_files = []
    # process
    metadata = MetadataHandler.retrieve_metadata(list_files)
    # test
    assert metadata == {}

    # case_1: 2 identical tiff file, all metadata
    # setup
    _file_root = os.path.dirname(os.path.abspath(__file__))
    test_data_dir = os.path.join(_file_root, "../data")
    file_name = os.path.join(
        test_data_dir,
        "IPTS-20267/raw/radiographs/Jan07_2020_sam1_lightOff/20200107_sam1_D2O_LightOff_0030_0313.tiff",
    )
    file_list = [file_name, file_name]
    # process
    metadata = MetadataHandler.retrieve_metadata(file_list)
    # test
    assert len(metadata) == 1
    assert len(metadata[file_name]) == 109

    # case_2: 2 tiff file, specific metadata
    # setup
    list_metadata = [
        MetadataName.DETECTOR_MANUFACTURER,
        MetadataName.EXPOSURE_TIME,
    ]
    # process
    metadata = MetadataHandler.retrieve_metadata(file_list, list_metadata)
    # test
    assert len(metadata) == 1
    assert len(metadata[file_name]) == 2
    assert metadata[file_name][MetadataName.DETECTOR_MANUFACTURER] == "ManufacturerStr:Andor"
    assert metadata[file_name][MetadataName.EXPOSURE_TIME] == "ExposureTime:30.000000"

def test_get_value_of_metadata_key():
    # case_0: empty file
    # setup
    file_name = ""
    # process
    rst = MetadataHandler.get_value_of_metadata_key(file_name)
    # test
    assert rst == {}

    # case_1: tiff file, all metadata
    # setup
    _file_root = os.path.dirname(os.path.abspath(__file__))
    test_data_dir = os.path.join(_file_root, "../data")
    file_name = os.path.join(
        test_data_dir,
        "IPTS-20267/raw/radiographs/Jan07_2020_sam1_lightOff/20200107_sam1_D2O_LightOff_0030_0313.tiff",
    )
    # process
    rst = MetadataHandler.get_value_of_metadata_key(file_name)
    # test
    assert len(rst) == 109

    # case_2: tiff file, specific metadata
    # setup
    list_metadata = [
        65026,
        65027,
    ]
    # process
    rst = MetadataHandler.get_value_of_metadata_key(file_name, list_metadata)
    # test
    assert len(rst) == 2
    assert rst[65026] == "ManufacturerStr:Andor"
    assert rst[65027] == "ExposureTime:30.000000"

def test_retrieve_value_of_metadata_key():
    # case_0: empty list
    # setup
    list_files = []
    # process
    rst = MetadataHandler.retrieve_value_of_metadata_key(list_files)
    # test
    assert rst == {}

    # case_1: 2 identical tiff file, all metadata
    # setup
    _file_root = os.path.dirname(os.path.abspath(__file__))
    test_data_dir = os.path.join(_file_root, "../data")
    file_name = os.path.join(
        test_data_dir,
        "IPTS-20267/raw/radiographs/Jan07_2020_sam1_lightOff/20200107_sam1_D2O_LightOff_0030_0313.tiff",
    )
    file_list = [file_name, file_name]
    # process
    rst = MetadataHandler.retrieve_value_of_metadata_key(file_list)
    # test
    assert len(rst) == 1
    assert len(rst[file_name]) == 109

    # case_2: 2 tiff file, specific metadata
    # setup
    list_metadata = [
        65026,
        65027,
    ]
    # process
    rst = MetadataHandler.retrieve_value_of_metadata_key(file_list, list_metadata)
    # test
    assert len(rst) == 1
    assert len(rst[file_name]) == 2
    assert rst[file_name][65026] == "ManufacturerStr:Andor"
    assert rst[file_name][65027] == "ExposureTime:30.000000"

if __name__ == "__main__":
    pytest.main([__file__])
