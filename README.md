# NeutronImagingScripts

This package contains a suite of Python modules and scripts that are critical for the data reduction of Neutron Imaging
at Oak Ridge National Laboratory.


## Overview

| Component | What it does |
|---|---|
| `neutronimaging.detector_correction` | MCP detector occupancy (deadtime) correction: shutter metadata parsing, FITS stack loading with NeuNorm-1.x-equivalent gamma filtering, per-shutter-window occupancy correction, optional Timepix chip-geometry correction (gated behind `--chipcorrection`) |
| `neutronimaging.preprocess` | CG1D preprocessing: TIFF metadata extraction and measurement-configuration (JSON) generation |
| `neutronimaging.npmath` / `neutronimaging.util` | numerical and filesystem helpers (edge binning, EPICS timestamp conversion, folder trees) |
| `mcp_detector_correction` (CLI) | end-to-end MCP correction: validate input dir, correct, export float32 TIFFs under true source names + sidecar metadata |
| `generate_config` (CLI) | build the reduction configuration JSON from radiograph/OB/DF directories |

Image I/O is direct astropy (FITS) and tifffile (TIFF) — the NeuNorm dependency was
removed in [#19](https://github.com/ornlneutronimaging/NeutronImagingScripts/pull/19).

## Installation

### General users

Install the package from PyPI with

```bash
$ pip install NeutronImaging
```

> NOTE: the current PyPI release (1.2) long predates the NeuNorm removal and the
> 2026 correctness fixes; install from git until v1.6 is released (pending a
> license decision — see Developer Notes).

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

### Test data provenance

- `data/OB_1_005_*.fits` (916 frames) + `OB_1_005_{ShutterCount,ShutterTimes,Spectra}.txt`:
  an MCP open-beam measurement used by the detector-correction tests and the example notebook.
- `data/IPTS-20267/`: CG1D directory trees exercising `generate_config`.
- `data/ref_pop_prof.npz` / `data/ref_img_mean_prof.npz`: golden per-frame mean profiles
  for the occupancy correction. Regenerate ONLY after an intentional, reviewed behavior
  change with `pixi run python scripts/regenerate_test_refs.py` — running it blindly would
  enshrine whatever the current code does.
- The `data/` tree is ~571 MB of plain git objects (no LFS — deliberately abandoned in
  ef81aed); externalizing it (release asset / pooch) is an open team decision.

### Releasing

1. Settle the license metadata first (LICENSE file says GPLv3, the pre-migration
   setup.py said BSD, old classifiers said LGPLv2) — blocking for any PyPI upload.
2. Tag `vX.Y` on `main` (versioningit derives versions from tags).
3. Build and upload manually (`python -m build`, `twine upload dist/*`) — by decision
   there is no publish automation for this repo (no known downstream pip consumers).

### Branch model

`main` only (decided 2026-06-10): work lands on `main` via PRs; the historical
`next`/`qa` promotion branches are frozen relics of the pre-2026 flow.
