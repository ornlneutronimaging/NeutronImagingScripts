#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

import numpy as np
import pandas as pd
from astropy.io import fits
from tqdm.auto import tqdm


def read_shutter_count(filename: str) -> pd.DataFrame:
    """Parse in shutter count data from csv"""
    _df = pd.read_csv(filename, sep="\t", names=["shutter_index", "shutter_counts"])
    _df = _df[_df["shutter_counts"] > 0]
    _df["shutter_n_ratio"] = _df["shutter_counts"] / _df["shutter_counts"].values[0]
    return _df


def read_shutter_time(filename: str) -> pd.DataFrame:
    """Parse in shutter time from csv"""
    _df = pd.read_csv(
        filename,
        sep="\t",
        names=["shutter_index", "start_frame", "end_frame"],
    )
    _df = _df[_df["end_frame"] > 0]
    # NOTE: the start/end frame here is delta, we need the absolute
    #       therefore, cumulative sum for times
    _lbs = ["start_frame", "end_frame"]
    _tmp = _df[_lbs].values
    _df[_lbs] = _tmp.flatten().cumsum().reshape(_tmp.shape)
    return _df


def read_spectra(filename: str) -> pd.DataFrame:
    """Parse in spectra data from csv"""
    return pd.read_csv(filename, sep="\t", names=["shutter_time", "counts"])


def merge_meta_data(
    shutter_count: pd.DataFrame,
    shutter_time: pd.DataFrame,
    spectra: pd.DataFrame,
) -> pd.DataFrame:
    """Consolidate meta data from three different dataframes into one"""
    _df = spectra.copy(deep=True)
    _df_shutter = pd.concat([shutter_count, shutter_time], axis=1)
    print(f"{_df_shutter =}")
    _df["run_num"] = spectra.index
    # initialize fields
    _df["shutter_index"] = -1
    _df["shutter_counts"] = -1
    for _, row in _df_shutter.iterrows():
        _idx, _cnt, _snr, _, _start, _end = row
        _df.loc[_df["shutter_time"].between(_start, _end), "shutter_index"] = int(_idx)
        _df.loc[_df["shutter_time"].between(_start, _end), "shutter_counts"] = int(_cnt)
        _df.loc[_df["shutter_time"].between(_start, _end), "shutter_n_ratio"] = _snr
    return _df


def skipping_meta_data(meta: pd.DataFrame) -> pd.DataFrame:
    """Skips first and last or each run in metadata"""
    _by_shutter = meta.groupby(['shutter_index'])
    # groupby returns (group_num, dataframe), thus the [1] first
    _with_skips = [item[1][1:-1] for item in _by_shutter]
    return pd.concat(_with_skips)


def list_image_files(raw_image_dir: str, nbr_of_duplicated_runs: int = 1) -> list[str]:
    """Sorted FITS frame files in a directory, excluding *_SummedImg*.

    if the nbr_of_duplicated_runs is higher than 1 (default value) that means the MCP produced by
    mistake other sets of the same data, those must be removed and not used in the reconstruction
    """
    import glob

    if nbr_of_duplicated_runs < 1:
        raise ValueError(f"nbr_of_duplicated_runs must be >= 1, got {nbr_of_duplicated_runs}")

    _img_names = [
        me for me in glob.glob(f"{raw_image_dir}/*.fits") if "_SummedImg" not in me
    ]
    _img_names.sort()

    final_index = int(len(_img_names) / nbr_of_duplicated_runs)
    return _img_names[0:final_index]


def _auto_gamma_filter(image: np.ndarray, raw_dtype) -> np.ndarray:
    """Replicate NeuNorm 1.x's automatic gamma filtering.

    For integer raw data, pixels strictly above ``iinfo(raw_dtype).max - 5``
    are treated as gamma hits and replaced by the mean of their 8 neighbors
    (zero-padded at the borders), computed on the unfiltered image — the
    exact semantics of NeuNorm 1.x's ``_auto_gamma_filtering`` (3x3 ones
    kernel with zero center, ``convolve(..., mode="constant")``).
    Float raw data is returned unchanged, as in 1.x.

    ``image`` must already be the float32 working copy.
    """
    if not np.issubdtype(np.dtype(raw_dtype), np.integer):
        return image
    threshold = np.iinfo(raw_dtype).max - 5
    gamma = image > threshold
    if not gamma.any():
        return image

    padded = np.pad(image, 1, mode="constant", constant_values=0.0)
    neighbor_mean = (
        padded[:-2, :-2] + padded[:-2, 1:-1] + padded[:-2, 2:]
        + padded[1:-1, :-2] + padded[1:-1, 2:]
        + padded[2:, :-2] + padded[2:, 1:-1] + padded[2:, 2:]
    ) / 8.0
    filtered = image.copy()
    filtered[gamma] = neighbor_mean[gamma]
    return filtered


def load_images(raw_image_dir: str, nbr_of_duplicated_runs: int = 1) -> np.ndarray:
    """Load all frame images into memory as a float32 stack.

    Frames are read with astropy in sorted-filename order (excluding
    *_SummedImg*), squeezed to 2D, gamma-filtered (integer data only, see
    _auto_gamma_filter) and cast to float32. Returns an ndarray of shape
    (n_frames, height, width). The stack is preallocated and filled one
    frame at a time, so peak memory is one stack plus one frame.

    Raises
    ------
    OSError
        If the directory contains no frame files, or a frame's shape does
        not match the previously loaded frames.
    """
    _img_names = list_image_files(raw_image_dir, nbr_of_duplicated_runs)
    if not _img_names:
        raise OSError(f"No FITS frame files found in {raw_image_dir}")

    stack = None
    for _i, _name in enumerate(tqdm(_img_names, desc="Loading sample", leave=False)):
        # memmap=False: fully materialize while the file is open, so the
        # array never references a closed file mapping
        with fits.open(_name, ignore_missing_end=True, memmap=False) as hdulist:
            raw = hdulist[0].data
            _image = np.squeeze(np.asarray(raw, dtype=np.float32))
            raw_dtype = raw.dtype
        _image = _auto_gamma_filter(_image, raw_dtype)
        if stack is None:
            stack = np.empty((len(_img_names), *_image.shape), dtype=np.float32)
        elif _image.shape != stack.shape[1:]:
            raise OSError("Shape of sample does not match previously loaded data set!")
        stack[_i] = _image
    return stack


def calc_pixel_occupancy_probability(
    images: np.ndarray,
    metadata: pd.DataFrame,
) -> np.ndarray:
    """calculate pixel occupancy probability"""
    _imgs = np.asarray(images)
    _pops = np.zeros_like(_imgs)

    # calculation is done on a per shutter index base
    for _idx in metadata["shutter_index"].unique():
        _run_num = metadata.loc[metadata["shutter_index"] == _idx, "run_num"].values
        _cnts = metadata.loc[metadata["shutter_index"] == _idx, "shutter_counts"].values
        _tmp = _imgs[_run_num, :, :].cumsum(axis=0)
        _pops[_run_num, :, :] = np.divide(_tmp, _cnts[:, np.newaxis, np.newaxis])
    return _pops


def _apply_chip_geometry_correction(images: np.ndarray) -> np.ndarray:
    """Apply Timepix chip-geometry correction to a corrected stack.

    Sub-pixel shift correction plus inter-chip gap interpolation, delegated
    to the optional ``timepix-geometry-correction`` package. This is the
    proper home of the feature originally added in 51e93bd (issue #9) and
    turned off in 9d15860 (issue #13): available, documented, and gated off
    by default instead of commented out.
    """
    try:
        from timepix_geometry_correction.correct import TimepixGeometryCorrection
    except ImportError as error:
        raise ImportError(
            "Chip-geometry correction requires the optional "
            "'timepix-geometry-correction' package. Install it with "
            "pip install 'NeutronImaging[chipcorrection]' "
            "(or pip install timepix-geometry-correction)."
        ) from error

    corrector = TimepixGeometryCorrection(raw_images=images)
    return corrector.correct(display=False)


def correct_images(
    images: np.ndarray,
    metadata: pd.DataFrame,
    skip_first_and_last=False,
    apply_chip_correction=False,
) -> np.ndarray:
    """
    Correct raw images based on shutter info in metadata

    Parameters
    ----------
    images : ndarray
        Raw frame stack (n_frames, height, width).
    metadata : DataFrame
        Merged shutter/spectra metadata (see merge_meta_data).
    skip_first_and_last : bool, optional
        Drop the first and last frame of each shutter group. Default False.
    apply_chip_correction : bool, optional
        Additionally apply Timepix chip-geometry correction (sub-pixel
        shift + inter-chip gap interpolation). Off by default; requires the
        optional timepix-geometry-correction package. Default False.
    """
    _img = np.asarray(images)
    _pop = calc_pixel_occupancy_probability(images, metadata)
    _snr = metadata["shutter_n_ratio"].values[:, np.newaxis, np.newaxis]
    _rst = _img / (1 - _pop) / _snr
    # NOTE: The very first and last image of each frame (shutter_index)
    #       needs specicial correction, therefore removing them from
    #       standard pipeline if specified
    if skip_first_and_last:
        _tmp = []
        for _idx in metadata["shutter_index"].unique():
            _run_num = metadata.loc[metadata["shutter_index"] == _idx, "run_num"].values
            _tmp += list(_run_num[1:-1])
        _idx_to_keep = np.array(_tmp)
        _rst = _rst[_idx_to_keep, :, :]

    if apply_chip_correction:
        _rst = _apply_chip_geometry_correction(_rst)

    return _rst