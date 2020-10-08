# NeutronImagingScripts

This pakcage contains a suite of Python modules and scripts that are critical for the data reduction of Neutron Imaging at Oak Ridge National Laboratory.


## Overview

## Installation

### General users

Install the package (once published on pip) with

```bash
$ pip install NeutronImagingScripts
```

### Developers
For developers, it is __highly__ recommended to setup an isolated virtual environment for this repository.
After cloning this repository to your local machine, go to the root of this repo and use the follwing commands to install dependencies

```bash
$ pip install -r requirements.txt
$ pip install -r requirements_dev.txt
```
use the following command to install this package to your path
```bash
$ pip install -e .
```
> For unit test, run `pytest tests` at the root of this repo.

## Usage

### Use as a Package
Examples of using this package as a Python module are provided as Jupyter Notebooks insdie the `example` folder.

### Use as a commandline tool
After installing this package, the scripts located in `scripts` should be visible in your Path.
Simpy type `mcp_detector_correction.py`, you should see the following
```bash
$ mcp_detector_correction.py
Usage:
    mcp_detector_correction [--skipimg] [--verbose] <input_dir> <output_dir>
    mcp_detector_correction (-h | --help)
    mcp_detector_correction --version
```
Therefore, you can process the example data with the following command at the root of this repo
```bash
$ mcp_detector_correction.py data tmp
```
and you will see the following in your terminal
```bash
$ mcp_detector_correction.py data tmp
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
