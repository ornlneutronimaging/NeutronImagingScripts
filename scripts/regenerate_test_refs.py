#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Regenerate the golden reference profiles used by tests/test_detector_correction.py.

The goldens pin the per-frame mean of (a) the pixel occupancy probability and
(b) the corrected image stack, computed over the shipped 916-frame MCP
open-beam measurement (data/OB_1_005_*).

ONLY run this after an intentional, reviewed behavior change to the occupancy
correction: regenerating goldens enshrines whatever the current code produces,
so a blind run converts a regression into a passing test. Record the reason in
the commit message that updates the .npz files.

Usage:
    pixi run python scripts/regenerate_test_refs.py
"""

import os

import numpy as np

from neutronimaging.detector_correction import (
    calc_pixel_occupancy_probability,
    correct_images,
    load_images,
    merge_meta_data,
    read_shutter_count,
    read_shutter_time,
    read_spectra,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def main():
    df_meta = merge_meta_data(
        read_shutter_count(os.path.join(DATA_DIR, "OB_1_005_ShutterCount.txt")),
        read_shutter_time(os.path.join(DATA_DIR, "OB_1_005_ShutterTimes.txt")),
        read_spectra(os.path.join(DATA_DIR, "OB_1_005_Spectra.txt")),
    )
    images = load_images(DATA_DIR)

    pops = calc_pixel_occupancy_probability(images, df_meta)
    pop_prof = np.array([np.mean(img) for img in pops])
    np.savez(os.path.join(DATA_DIR, "ref_pop_prof.npz"), pop_prof)
    print(f"wrote data/ref_pop_prof.npz ({pop_prof.shape[0]} frames)")

    corrected = correct_images(images, df_meta)
    img_mean_prof = np.array([np.mean(img) for img in corrected])
    np.savez(os.path.join(DATA_DIR, "ref_img_mean_prof.npz"), img_mean_prof)
    print(f"wrote data/ref_img_mean_prof.npz ({img_mean_prof.shape[0]} frames)")


if __name__ == "__main__":
    main()
