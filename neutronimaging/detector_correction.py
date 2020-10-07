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


def read_shutter_time(filename: str) -> pd.DataFrame:
    """Parse in shutter time from csv"""
    _df = pd.read_csv(
        filename,
        sep="\t",
        names=['shutter_index', 'start_frame', 'end_frame'],
    )
    # NOTE: confirm whether we should stop or skip at first 
    #       zero count location
    _df = _df[_df['end_frame']>0]
    # NOTE: the start/end frame here is delta, we need the absolute
    #       therefore, cumulative sum for times
    _lbs = ['start_frame', 'end_frame']
    _tmp = _df[_lbs].values
    _df[_lbs] = _tmp.flatten().cumsum().reshape(_tmp.shape)
    return _df


def read_spectra(filename: str) -> pd.DataFrame:
    """Parse in spectra data from csv"""
    return pd.read_csv(filename, sep='\t', names=['shutter_time', 'counts'])


def merge_meta_data(
    shutter_count: pd.DataFrame, 
    shutter_time: pd.DataFrame, 
    spectra: pd.DataFrame,
    ) -> pd.DataFrame:
    """Consolidate meta data from three different dataframes into one"""
    _df = spectra.copy(deep=True)
    _df_shutter = pd.concat([shutter_count, shutter_time], axis=1)
    _df["run_num"] = spectra.index
    # initialize fields
    _df["shutter_index"] = -1
    _df["shutter_counts"] = -1
    for _, row in _df_shutter.iterrows():
        _idx, _cnt, _, _start, _end = row
        print(_idx, _cnt, _start, _end)
        _df.loc[_df["shutter_time"].between(_start, _end), "shutter_index"] = int(_idx)
        _df.loc[_df["shutter_time"].between(_start, _end), "shutter_counts"] = int(_cnt)
    return _df


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
    print(df_shutter_time)
    #
    spectra_file = os.path.join(test_data_dir, "OB_1_005_Spectra.txt")
    df_spectra = read_spectra(spectra_file)
    print(df_spectra)
    #
    df_meta = merge_meta_data(df_shutter_count, df_shutter_time, df_spectra)
    print(df_meta)
