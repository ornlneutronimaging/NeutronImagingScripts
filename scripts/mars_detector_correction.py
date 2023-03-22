#!/usr/bin/env python

"""MARS Detector Correction.

Usage:
    mars_detector_correction [options] <input> <output>
    mars_detector_correction [options] (--median | --mean | --match) <input> <output>

Options:
    --skipimg          skip first and last image
    --select_time=<st> select ob&dc based on time in sec
    --median           use median to combine selected ob
    --mean             use mean to combine selected ob
    --match            perform one to one matching between projections and obs
    -h --help          print this message
    -v --version       print version info
    -V --verbose       verbose output
"""
import os
import logging
from datetime import datetime
from docopt import docopt

if __name__ == "__main__":
    args = docopt(__doc__, help=True, version="MARS Detector Correction 1.0")

    # parsing input
    input_dir = args["<input>"]
    output_dir = args["<output>"]
    skip_first_last_img = args["--skipimg"]
    verbose = args["--verbose"]
    # get time range
    if args["--select_time"]:
        select_time = float(args["--select_time"])
    else:
        select_time = None
    # get combine method
    # NOTE: mutually exclusive options are handled by docopt
    if args["--median"]:
        combine_method = "median"
    elif args["--mean"]:
        combine_method = "mean"
    elif args["--match"]:
        combine_method = "match"
    else:
        combine_method = "median"

    # setup logging (terminal and file)
    timestr = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(args["<output>"], f"mars_detector_correction_{timestr}.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger().addHandler(logging.StreamHandler())

    logging.info("MARS Detector Correction")
    logging.info(f"input_dir: {input_dir}")
    logging.info(f"output_dir: {output_dir}")
    logging.info(f"skip_first_last_img: {skip_first_last_img}")
    logging.info(f"verbose: {verbose}")
    logging.info(f"select_time: {select_time}")
    logging.info(f"combine_method: {combine_method}")

    # extract IPTS root from given input directory

    # get list of all tiffs in input directory
    # infer the ob and dc folder position
    # match ob and dc based on time and metadata

    # use selected method to combine ob

    # use median to combine dc/df

    # perform detector correction

    # save output

    logging.info("Done")
