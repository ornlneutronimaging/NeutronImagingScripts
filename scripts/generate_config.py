#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Configuration Generator

Usage:
    generate_config.py  <image_dir> <openbeam_dir> <darkfield_dir> <output_file> [--tolerance=<tor>]
    generate_config.py  (-h | --help)
    generate_config.py  --version

Options:
    -h --help           print this message
    --version           print version info
    --tolerance=<tor>   tolerance for slit position during clustering  [default (mm): 1]
"""

from docopt import docopt
from neutronimaging.preprocess import generate_config_CG1D


if __name__ == "__main__":
    args = docopt(__doc__, help=True, version="Configuration Generateor 1.0")

    # parsing input
    print("Parsing input")
    imgdir = args["<image_dir>"].split(",")
    obdir = args["<openbeam_dir>"]  # only one allowed here
    dfdir = args["<darkfield_dir>"]  # only one allowed here
    output = args["<output_file>"]
    tor = 1.0 if args["--tolerance"] is None else float(args["--tolerance"])

    # generate config
    generate_config_CG1D(imgdir, obdir, dfdir, output=output, tolerance_aperature=tor)
