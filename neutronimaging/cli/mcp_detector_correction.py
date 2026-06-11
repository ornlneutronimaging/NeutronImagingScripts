#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""MCP Detector Correction.

Usage:
    mcp_detector_correction [--skipimg] [--chipcorrection] [--verbose] <input_dir> <output_dir>
    mcp_detector_correction (-h | --help)
    mcp_detector_correction --version

Options:
    --skipimg         skip first and last image
    --chipcorrection  additionally apply Timepix chip-geometry correction
                      (requires the optional timepix-geometry-correction package)
    -h --help         print this message
    --version         print version info
    --verbose         verbose output
"""

import glob
import os
import shutil
from pathlib import Path

import numpy as np
import tifffile
from docopt import docopt

from neutronimaging.detector_correction import (
    correct_images,
    list_image_files,
    load_images,
    merge_meta_data,
    read_shutter_count,
    read_shutter_time,
    read_spectra,
    skipping_meta_data,
)


def main(argv=None):
    args = docopt(__doc__, argv=argv, help=True, version="MCP Detector Correction 1.0")

    # parsing input
    print("Parsing input")
    input_dir = args["<input_dir>"]
    output_dir = args["<output_dir>"]
    skip_first_last_img = args["--skipimg"]
    verbose = args["--verbose"]

    # validation
    print("Validating input arguments")
    if not Path(input_dir).is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not Path(output_dir).is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {output_dir}")

    # in some rare instances, the MCP creates a duplicate set of the run in the same folder
    # we need to only consider the first set in the autoreduction
    shutter_count_files = sorted(glob.glob(input_dir + "/*_ShutterCount.txt"))
    if not shutter_count_files:
        raise FileNotFoundError(f"No *_ShutterCount.txt file found in {input_dir}")
    nbr_of_duplicated_runs = len(shutter_count_files)
    if nbr_of_duplicated_runs > 1:
        print(f"The folder contains {nbr_of_duplicated_runs} sets of the same data!")

    # derive every sidecar file from one common prefix (the first set in
    # sorted order); four independent unsorted globs could mix files from
    # different duplicate sets
    shutter_count_file = shutter_count_files[0]
    _stem = Path(shutter_count_file).name[: -len("_ShutterCount.txt")]
    shutter_time_file = os.path.join(input_dir, f"{_stem}_ShutterTimes.txt")
    spectra_file = os.path.join(input_dir, f"{_stem}_Spectra.txt")
    summed_file = os.path.join(input_dir, f"{_stem}_SummedImg.fits")
    for _sidecar in (shutter_time_file, spectra_file, summed_file):
        if not Path(_sidecar).exists():
            raise FileNotFoundError(f"Expected sidecar file is missing: {_sidecar}")

    # process metadata
    print("Processing metadata")
    df_meta = merge_meta_data(
        read_shutter_count(shutter_count_file),
        read_shutter_time(shutter_time_file),
        read_spectra(spectra_file),
    )
    if verbose:
        print(df_meta)

    # load images
    print("Loading images into memory")
    images = load_images(input_dir, nbr_of_duplicated_runs)
    if images.shape[0] != len(df_meta):
        raise RuntimeError(
            f"loaded {images.shape[0]} frames but the spectra metadata has "
            f"{len(df_meta)} rows; the input directory is inconsistent"
        )

    # perform image correction
    print("Perform correction")
    img_corrected = correct_images(
        images,
        df_meta,
        skip_first_and_last=skip_first_last_img,
        apply_chip_correction=args["--chipcorrection"],
    )
    print("corrected image summary")
    print(f"\tdimension:\t{img_corrected.shape}")
    print(f"\ttype:\t{img_corrected.dtype}")

    # export results
    print(f"Writing data to {output_dir}")
    # one float32 TIFF per kept frame, named after its true source frame
    # (NeuNorm 1.x zip-truncated the full name list against the skip-reduced
    # stack, mislabeling kept frames with the first N source names)
    source_names = list_image_files(input_dir, nbr_of_duplicated_runs)
    if skip_first_last_img:
        kept_run_nums = skipping_meta_data(df_meta)["run_num"].values
        source_names = [source_names[i] for i in kept_run_nums]
    if len(source_names) != img_corrected.shape[0]:
        raise RuntimeError(
            f"corrected stack has {img_corrected.shape[0]} frames but "
            f"{len(source_names)} source names were selected for export"
        )
    for src, frame in zip(source_names, img_corrected):
        out_name = os.path.join(output_dir, Path(src).stem + ".tif")
        tifffile.imwrite(out_name, frame.astype(np.float32))
    out_shutter_count = os.path.join(output_dir, os.path.basename(shutter_count_file))
    out_shutter_time = os.path.join(output_dir, os.path.basename(shutter_time_file))
    out_spectra_file = os.path.join(output_dir, os.path.basename(spectra_file))
    out_summed_file = os.path.join(output_dir, os.path.basename(summed_file))
    shutil.copyfile(shutter_count_file, out_shutter_count)
    shutil.copyfile(shutter_time_file, out_shutter_time)
    shutil.copyfile(summed_file, out_summed_file)
    # handle proper spectra parsing
    if skip_first_last_img:
        # match the instrument-written format: headerless TSV with CRLF
        # line endings, so read_spectra and the non-skip (verbatim copy)
        # branch stay parseable the same way; pandas defaults previously
        # wrote comma-separated WITH header under the same filename
        skipping_meta_data(df_meta).to_csv(
            out_spectra_file,
            columns=["shutter_time", "counts"],
            index=False,
            header=False,
            sep="\t",
            lineterminator="\r\n",
        )
    else:
        shutil.copyfile(spectra_file, out_spectra_file)


if __name__ == "__main__":
    main()
