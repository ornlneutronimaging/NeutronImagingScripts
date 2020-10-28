#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Configuration Generator

Usage:
    generate_config.py  <input_dir> <output_file>
    generate_config.py  (-h | --help)
    generate_config.py  --version

Options:
    -h --help   print this message
    --version   print version info
"""

from docopt import docopt
from neutronimaging.preprocess import generate_config_CG1D


if __name__ == "__main__":
    args = docopt(__doc__, help=True, version="Configuration Generateor 1.0")

    # parsing input
    print('Parsing input')
    rootdir = args['<input_dir>']
    output = args['<output_file>']

    # generate config
    generate_config_CG1D(rootdir, output=output)
