#!/usr/bin/env python

"""
Unit testing for numpy math module from package
NetronImaging
"""

import numpy as np
import pytest
from neutronimaging.npmath import find_edges_1d


def test_find_edges_1d():
    array1 = np.array([40, 40.5, 42, 41.7, 38])
    result1 = np.array(list(find_edges_1d(array1)))
    target1 = np.array([[37.5, 38.5], [38.5, 41.0], [41.0, 42.5]])
    np.testing.assert_almost_equal(result1, target1)

    array2 = np.array([40])
    result2 = np.array(list(find_edges_1d(array2)))
    target2 = np.array([[39.5, 40.5]])
    np.testing.assert_almost_equal(result2, target2)


if __name__ == "__main__":
    pytest.main([__file__])
