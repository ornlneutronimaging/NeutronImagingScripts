#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This module contains necessary preprocessing toolkits for neutron imaging, including
- CG1D: reactor imaging beamline
-  
"""

import json
import itertools
import pandas as pd
from PIL import Image
from datetime import datetime
from neutronimaging.npmath import find_edges_1d
from neutronimaging.util import dir_tree_to_list
from neutronimaging.util import probe_folder
from neutronimaging.util import convert_epics_timestamp_to_rfc3339_timestamp
from typing import List, Tuple
from typing import Union


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
    rootdir: Union[str, List],
    output: str = None,
    tolerance_aperature: float = 1.0,  # in mm
    exclude_images: str = "calibration",
) -> dict:
    """frontend to allow list of rootdirs"""
    cfg_dict = {}
    if isinstance(rootdir, str):
        cfg_dict = _generate_config_CG1D(
            rootdir, None, tolerance_aperature, exclude_images
        )
    elif isinstance(rootdir, list):
        for this_dir in rootdir:
            cfg_dict[this_dir] = _generate_config_CG1D(
                this_dir, None, tolerance_aperature, exclude_images
            )
    else:
        raise ValueError(f"input dir has to be a string a list of strings")

    # dump dict to desired format if output file name provided
    if output is not None:
        if "json" in output.split(".")[-1].lower():
            with open(output, "w") as outputf:
                json.dump(cfg_dict, outputf, indent=2, sort_keys=True)
        else:
            raise NotImplementedError

    return cfg_dict


def _generate_config_CG1D(
    rootdir: str,
    output: str = None,
    tolerance_aperature: float = 1.0,  # in mm
    exclude_images: str = "calibration",
) -> dict:
    # build the metadata DataFrame
    img_list = dir_tree_to_list(probe_folder(rootdir), flatten=True, sort=True)
    img_list = [me for me in img_list if exclude_images.lower() not in me.lower()]
    img_list = [me for me in img_list if ".tif" in me.lower()]
    meta_data = (extract_metadata_tiff(me) for me in img_list)

    # NOTE:
    # If the image list gets way too long, we can consider using multiprocessing
    # to speed up the parsing process as it is mostly an IO/thread bound process.
    md_data = [md for md, _ in meta_data]
    _, header = extract_metadata_tiff(img_list[0])
    df = pd.DataFrame(data=md_data, columns=header)

    # need to add a few extra feature vector for clustering
    lbs = ["aperture_HR", "aperture_HL", "aperture_VT", "aperture_VB"]
    lbs_binned = [f"{lb}_binned" for lb in lbs]
    for lb, lb_binned in zip(lbs, lbs_binned):
        df.loc[:, lb_binned] = 0

    # group by
    # - exposure_time
    # - (detector_name, aperture_[HR|HL|VT|VB])
    # and populate dict
    exposure_times = df["exposure_time"].unique()
    cfg_dict = {}
    for exposure in exposure_times:
        data_dict = cfg_dict[exposure] = {}
        # first, we need to bin the interval to form the category
        for lb, lb_binned in zip(lbs, lbs_binned):
            vals = df.loc[df["exposure_time"] == exposure, lb].unique()
            bin_edges = list(find_edges_1d(vals, atol=tolerance_aperature))
            for _low, _up in bin_edges:
                df.loc[
                    (df["exposure_time"] == exposure) & (df[lb].between(_low, _up)),
                    lb_binned,
                ] = df.loc[
                    (df["exposure_time"] == exposure) & (df[lb].between(_low, _up)), lb
                ].mean()
        # second, find the categories
        detector_names = df.loc[
            df["exposure_time"] == exposure, "detector_manufacturer"
        ].unique()
        aperture_HRs = df.loc[
            df["exposure_time"] == exposure, "aperture_HR_binned"
        ].unique()
        aperture_HLs = df.loc[
            df["exposure_time"] == exposure, "aperture_HL_binned"
        ].unique()
        aperture_VTs = df.loc[
            df["exposure_time"] == exposure, "aperture_VT_binned"
        ].unique()
        aperture_VBs = df.loc[
            df["exposure_time"] == exposure, "aperture_VB_binned"
        ].unique()
        categories = itertools.product(
            detector_names, aperture_HRs, aperture_HLs, aperture_VTs, aperture_VBs
        )
        # last, populate each categroy
        metadata_info_keys = [
            "detector_manufacturer",
            "aperture_HR",
            "aperture_HL",
            "aperture_VT",
            "aperture_VB",
        ]
        list_sample_keys = ["filename", "time_stamp", "time_stamp_user_format"]
        for i, me in enumerate(categories):
            _tmp = data_dict[f"config{i}"] = {}
            # generate metadata_infos (the common core)
            _tmp["metadata_infos"] = {k: v for k, v in zip(metadata_info_keys, me)}
            # generate list of images (data_type: Raw)
            # generate list of ob (data_type: OB)
            # generate list of df (data_type: DF)
            for groupname, datatype in zip(
                ("list_sample", "list_ob", "list_df"), ("Raw", "OB", "DF")
            ):
                _df_tmp = df.loc[
                    (df["exposure_time"] == exposure)
                    & (df["detector_manufacturer"] == me[0])
                    & (df["aperture_HR_binned"] == me[1])
                    & (df["aperture_HL_binned"] == me[2])
                    & (df["aperture_VT_binned"] == me[3])
                    & (df["aperture_VB_binned"] == me[4])
                    & (df["data_type"] == datatype),
                    list_sample_keys,
                ]
                _tmp[groupname] = {
                    index: {k: v for k, v in zip(list_sample_keys, row)}
                    for index, row in enumerate(_df_tmp.to_numpy())
                }

            # generate for first images
            # generate for last images
            _tmp["first_images"] = {}
            _tmp["last_images"] = {}
            for groupname, datatype in zip(("sample", "ob", "df"), ("Raw", "OB", "DF")):
                _df_tmp = df.loc[
                    (df["exposure_time"] == exposure)
                    & (df["detector_manufacturer"] == me[0])
                    & (df["aperture_HR_binned"] == me[1])
                    & (df["aperture_HL_binned"] == me[2])
                    & (df["aperture_VT_binned"] == me[3])
                    & (df["aperture_VB_binned"] == me[4])
                    & (df["data_type"] == datatype),
                    list_sample_keys,
                ]
                _tmp["first_images"][groupname] = (
                    {
                        k: v
                        for k, v in zip(
                            list_sample_keys,
                            _df_tmp.sort_values("time_stamp").to_numpy()[0],
                        )
                    }
                    if _df_tmp.size > 0
                    else {}
                )
                _tmp["last_images"][groupname] = (
                    {
                        k: v
                        for k, v in zip(
                            list_sample_keys,
                            _df_tmp.sort_values("time_stamp").to_numpy()[-1],
                        )
                    }
                    if _df_tmp.size > 0
                    else {}
                )

    # dump dict to desired format if output file name provided
    if output is not None:
        if "json" in output.split(".")[-1].lower():
            with open(output, "w") as outputf:
                json.dump(cfg_dict, outputf, indent=2, sort_keys=True)
        elif "csv" in output.split(".")[-1].lower():
            df.to_csv(output, sep="\t", index=False)
        else:
            raise NotImplementedError

    return cfg_dict


if __name__ == "__main__":
    pass
