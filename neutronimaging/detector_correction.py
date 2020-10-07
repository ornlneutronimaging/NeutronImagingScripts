#!/usr/bin/env python

"""
"""

import numpy as np
import pandas as pd


def read_shutter_count(filename: str) -> pd.DataFrame:
    """Parse in shutter count data from csv"""
    # TODO: confirm whether we should stop or skip at
    #       zero count location
    _df =  pd.read_csv(
        filename,
        sep="\t",
        names=['shutter_index', 'shutter_counts']
        )
    return _df[_df['shutter_counts'] > 0]


def read_shutter_time(filename: str, offset: float=0.0) -> pd.DataFrame:
    """Parse in shutter time from csv"""
    _df = pd.read_csv(
        filename,
        sep="\t",
        names=['shutter_index', 'start_frame', 'end_frame'],
    )
    # NOTE: confirm whether we should stop or skip at first 
    #       zero count location
    _df = _df[_df['end_frame']>0]
    _df['start_frame'] += offset
    _df['end_frame'] += offset
    return _df


def read_spectra(filename: str) -> pd.DataFrame:
    """Parse in spectra data from csv"""
    return pd.read_csv(filename, sep='\t', names=['shutter_time', 'counts'])


if __name__ == "__main__":
    import os
    _file_root = os.path.dirname(os.path.abspath(__file__))
    test_data_dir = os.path.join(_file_root, "../data")
    #
    shutter_counts_file = os.path.join(test_data_dir, "OB_1_005_ShutterCount.txt")
    df_shutter_count = read_shutter_count(shutter_counts_file)
    print(df_shutter_count)
    #
    shutter_time_file = os.path.join(test_data_dir, "OB_1_005_ShutterTimes.txt")
    df_shutter_time = read_shutter_time(shutter_time_file)
    # df_shutter_time = read_shutter_time(shutter_time_file, offset=1)
    print(df_shutter_time)
    #
    spectra_file = os.path.join(test_data_dir, "OB_1_005_Spectra.txt")
    df_spectra = read_spectra(spectra_file)
    print(df_spectra)
