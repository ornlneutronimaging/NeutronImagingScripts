#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Configuration Generator

Usage:
    generate_config  <image_dir> <openbeam_dir> <darkfield_dir> <output_file> [--tolerance=<tor>]
    generate_config  (-h | --help)
    generate_config  --version

Options:
    -h --help           print this message
    --version           print version info
    --tolerance=<tor>   tolerance for slit position during clustering  [default (mm): 1]
"""

from docopt import docopt

from neutronimaging.preprocess import generate_config_CG1D


def main(argv=None):
    args = docopt(__doc__, argv=argv, help=True, version="Configuration Generator 1.0")

    # parsing input
    print("Parsing input")
    imgdir = args["<image_dir>"].split(",")
    obdir = args["<openbeam_dir>"]  # only one allowed here
    dfdir = args["<darkfield_dir>"]  # only one allowed here
    output = args["<output_file>"]
    tor = 1.0 if args["--tolerance"] is None else float(args["--tolerance"])

    # generate config
    generate_config_CG1D(imgdir, obdir, dfdir, output=output, tolerance_aperature=tor)


if __name__ == "__main__":
    main()
