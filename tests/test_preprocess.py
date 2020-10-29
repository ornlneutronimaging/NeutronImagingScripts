#!/usr/bin/env python

"""
Unit testing for preprocess module
"""

import os
import pytest
from neutronimaging.preprocess import generate_config_CG1D

_file_root = os.path.dirname(os.path.abspath(__file__))
test_data_dir = os.path.join(_file_root, "../data")


def test_generate_config_CG1D():
    # NOTE:
    # we can only test if the function call will work, but the filepath
    # could vary, which makes comparing two dict difficult
    imgdir = os.path.join(test_data_dir, "IPTS-20267/raw/radiographs")
    opdir = os.path.join(test_data_dir, "IPTS-20267/raw/ob")
    dfdir = os.path.join(test_data_dir, "IPTS-20267/raw/df")
    generate_config_CG1D(imgdir, opdir, dfdir)


if __name__ == "__main__":
    pytest.main([__file__])
