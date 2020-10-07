#!/usr/bin/env python

"""
"""

import numpy as np
import pandas as pd


def read_shutter_count(filename: str) -> pd.DataFrame:
    """Parse in shutter count data from CSV"""
    # TODO: confirm whether we should stop or skip at
    #       zero count location
    _df =  pd.read_csv(
        filename,
        setp="\t",
        names=['shutter_index', 'shutter_counts']
        )
    return _df[_df['shutter_counts'] > 0]

if __name__ == "__main__":
    pass