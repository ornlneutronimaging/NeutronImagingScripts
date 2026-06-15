#!/usr/bin/env python

"""
Unit testing for preprocess module
"""

import os

import pytest

from neutronimaging.preprocess import generate_config_CG1D


def test_generate_config_CG1D(data_dir):
    # NOTE:
    # we can only test if the function call will work, but the filepath
    # could vary, which makes comparing two dict difficult
    imgdir = os.path.join(data_dir, "IPTS-20267/raw/radiographs")
    opdir = os.path.join(data_dir, "IPTS-20267/raw/ob")
    dfdir = os.path.join(data_dir, "IPTS-20267/raw/df")
    generate_config_CG1D(imgdir, opdir, dfdir)


if __name__ == "__main__":
    pytest.main([__file__])
