#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This module contains necessary preprocessing toolkits for neutron imaging, including
- CG1D: reactor imaging beamline
-  
"""

import pandas as pd
from PIL import Image
from datetime import datetime
from neutronimaging.util import dir_tree_to_list
from neutronimaging.util import probe_folder
from neutronimaging.util import convert_epics_timestamp_to_rfc3339_timestamp
from typing import Tuple


def extract_metadata_tiff(tiffname: str) -> Tuple[list, list]:
    # default offset from the TIFF file
    # - str entry
    DATAACQMODE = 65018  # 'DataAcqModeStr:White Beam',
    DATATYPE = 65019  # 'DataTypeStr:Raw'
    DETECTOR_MANUFACTURER = 65026  # 'ManufacturerStr:Andor'
    FILENAMESTR = 65010  # 'FileNameStr:sam1_Cineole_LightOn'
    INSTRUMENT = 65011  # 'InstrumentStr:CG1D'
    MODELSTRING = 65025  # 'ModelStr:DW936_BV'

    # - float entry
    APERTURE_HR = 65068  # 'MotSlitHR.RBV:40.000000',
    APERTURE_HL = 65070  # 'MotSlitHL.RBV:40.000000'
    APERTURE_VT = 65066  # 'MotSlitVT.RBV:40.000000',
    APERTURE_VB = 65064  # 'MotSlitVB.RBV:40.000000',
    EXPOSURE_TIME = 65027  # 'ExposureTime:30.000000',
    IMGCOUNTER = 65031  # 'ImageCounter:77'
    TIME_SEC = 65002  # time secs
    TIME_NSEC = 65003  # time nano secs
    TIME_FULL = 65000  # full time
    IPTS = 65012  # 'IPTS:20267',
    ITEMS = 65013  # 'ITEMS:67144'
    GROUPID = 65020  # 'GroupID:113424'

    _metadata = dict(Image.open(tiffname).tag_v2)

    # time entry requires some special handling
    try:
        time_stamp = _metadata[TIME_SEC] + _metadata[TIME_NSEC] * 1e-9
    except:
        time_stamp = _metadata[TIME_FULL]
    finally:
        time_stamp = convert_epics_timestamp_to_rfc3339_timestamp(time_stamp)

    time_stamp_user_format = datetime.fromtimestamp(time_stamp).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    header = [
        "filename",
        "time_stamp",
        "time_stamp_user_format",
        "data_acq_mode",
        "data_type",
        "detector_manufacturer",
        "filename_base",
        "instrument",
        "model_string",
        "aperture_HR",
        "aperture_HL",
        "aperture_VT",
        "aperture_VB",
        "exposure_time",
        "image_counter",
        "IPTS",
        "items",
        "groupid",
    ]

    data = [
        tiffname,
        time_stamp,
        time_stamp_user_format,
        _metadata[DATAACQMODE].split(":")[-1],
        _metadata[DATATYPE].split(":")[-1],
        _metadata[DETECTOR_MANUFACTURER].split(":")[-1],
        _metadata[FILENAMESTR].split(":")[-1],
        _metadata[INSTRUMENT].split(":")[-1],
        _metadata[MODELSTRING].split(":")[-1],
        float(_metadata[APERTURE_HR].split(":")[-1]),
        float(_metadata[APERTURE_HL].split(":")[-1]),
        float(_metadata[APERTURE_VT].split(":")[-1]),
        float(_metadata[APERTURE_VB].split(":")[-1]),
        float(_metadata[EXPOSURE_TIME].split(":")[-1]),
        int(_metadata[IMGCOUNTER].split(":")[-1]),
        int(_metadata[IPTS].split(":")[-1]),
        int(_metadata[ITEMS].split(":")[-1]),
        int(_metadata[GROUPID].split(":")[-1]),
    ]

    return data, header


def generate_config_CG1D(
    rootdir: str,
    output: str = None,
    tolerance_aperature: float = 1.0,
) -> dict:
    pass


if __name__ == "__main__":
    pass
