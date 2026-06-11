# NeutronImagingScripts

This package contains a suite of Python modules and scripts that are critical for the data reduction of Neutron Imaging
at Oak Ridge National Laboratory.


## Overview

## Installation

### General users

Install the package (once published on pip) with

```bash
$ pip install NeutronImaging
```

### Developers
Development uses [pixi](https://pixi.sh) to manage the environment. After cloning
this repository, run the following at the repo root:

```bash
$ pixi install          # solve and install the dev environment (editable package included)
$ pixi run test         # run the unit tests
$ pixi run pre-commit run --all-files   # lint
```

A plain-pip path also works in any Python >=3.12 environment:
```bash
$ pip install -e .
```

## Usage

### Use as a Package
Examples of using this package as a Python module are provided as Jupyter Notebooks inside the `example` folder.

### Use as a commandline tool

#### _Generate Configuration File for Data Reduction_
To generate the `json` file that is needed for subsequent data reduction, use

```bash
$ generate_config IPTS-20267/raw/radiographs IPTS-20267/raw/ob IPTS-20267/raw/df IPTS-20267.json
```

where

 - `IPTS-20267/raw/radiographs` contains the raw images
 - `IPTS-20267/raw/ob` contains open beam images (white field)
 - `IPTS-20267/raw/df` contains dark field images

If you would like to have __multiple__ experiment configuration files __nested__ in one `json` file, simply use

```bash
$ generate_config IPTS-20267/raw/radiographs,IPTS-20267-2/raw/radiographs IPTS-20267/raw/ob IPTS-20267/raw/df IPTS-20267.json
```

notice that:
- You can have more than one folder for raw images, but they need to be within the same string separated by `,`.
- You can have only __one__ folder for open beam directory
- You can have only __one__ folder for dark field directory

The command above will yield a `json` file with the following structure

```json
 {"IPTS-20267": {"CONFIG_DATA"},
  "IPTS-20268": {"CONFIG_DATA"}
 }
```

The default tolerance for the categorization with respect to aperture positions is 1mm.
However, you can change the default value by specify it as below

```bash
$ generate_config \
    IPTS-20267/raw/radiographs \
    IPTS-20267/raw/ob \
    IPTS-20267/raw/df \
    IPTS-20267.json --tolerance=2
```

#### _MCP Detector correction_
Installing this package provides the `mcp_detector_correction` console command
(callers that invoke the repo file by path can keep using `scripts/mcp_detector_correction.py`,
which is a thin wrapper around the same implementation).
Type `mcp_detector_correction -h`, you should see the following

```bash
$ mcp_detector_correction -h
Usage:
    mcp_detector_correction [--skipimg] [--verbose] <input_dir> <output_dir>
    mcp_detector_correction (-h | --help)
    mcp_detector_correction --version
```

Therefore, you can process the example data with the following command at the root of this repo

```bash
$ mcp_detector_correction data tmp
```

and you will see the following in your terminal

```bash
$ mcp_detector_correction data tmp
Parsing input
Validating input arguments
Processing metadata
Loading images into memory
Perform correction
corrected image summary
	dimension:	(916, 512, 512)
	type:	float64
Writing data to tmp
```

> NOTE: make sure you create a `tmp` folder first.

## Developer Notes
