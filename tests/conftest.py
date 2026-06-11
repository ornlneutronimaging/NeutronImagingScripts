"""Shared fixtures for NeutronImagingScripts tests."""

import os
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return REPO_ROOT / "data"


def _write_fits_int16(path: Path, image: np.ndarray) -> None:
    """Write a big-endian int16 FITS file, matching the shipped MCP data."""
    hdu = fits.PrimaryHDU(image.astype(">i2"))
    fits.HDUList([hdu]).writeto(str(path))


@pytest.fixture
def synthetic_mcp_dataset(tmp_path):
    """A miniature but complete MCP dataset for CLI/export contract tests.

    3 shutter windows x 4 frames of constant-valued 32x32 big-endian int16
    images, with matching ShutterCount/ShutterTimes/Spectra TSV files and a
    _SummedImg.fits, mirroring the layout the beamline autoreduction feeds
    to mcp_detector_correction.
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    prefix = "OB_synth_005"
    n_groups, frames_per_group = 3, 4
    n_frames = n_groups * frames_per_group
    shape = (32, 32)

    # constant-valued frames, value = 10 + frame index, so every frame is
    # distinguishable and occupancy stays far from the 1-pole
    frame_values = [10 + k for k in range(n_frames)]
    for k, value in enumerate(frame_values):
        _write_fits_int16(input_dir / f"{prefix}_{k:05d}.fits", np.full(shape, value, dtype=np.int16))
    # excluded from loading, but required by the CLI's input validation
    _write_fits_int16(input_dir / f"{prefix}_SummedImg.fits", np.full(shape, 1, dtype=np.int16))

    # ShutterCount.txt: index\tcounts; trailing zero-count row is filtered out
    counts = [100000, 80000, 60000]
    lines = [f"{i}\t{c}" for i, c in enumerate(counts)] + ["3\t0"]
    (input_dir / f"{prefix}_ShutterCount.txt").write_text("\n".join(lines) + "\n")

    # ShutterTimes.txt: index\tstart_delta\tend_delta; read_shutter_time
    # cumulative-sums the flattened deltas, so deltas of (0.001, 0.002) per
    # row yield absolute windows [0.001,0.003], [0.004,0.006], [0.007,0.009]
    lines = [f"{i}\t0.001\t0.002" for i in range(n_groups)] + ["3\t0\t0"]
    (input_dir / f"{prefix}_ShutterTimes.txt").write_text("\n".join(lines) + "\n")

    # Spectra.txt: time\tcounts, headerless TSV; 4 times inside each window
    window_starts = [0.001, 0.004, 0.007]
    spectra_times = [start + offset for start in window_starts for offset in (0.0002, 0.0008, 0.0014, 0.0019)]
    lines = [f"{t:.6f}\t{value * shape[0] * shape[1]}" for t, value in zip(spectra_times, frame_values, strict=True)]
    (input_dir / f"{prefix}_Spectra.txt").write_text("\n".join(lines) + "\n")

    return {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "prefix": prefix,
        "n_groups": n_groups,
        "frames_per_group": frames_per_group,
        "n_frames": n_frames,
        "shape": shape,
        "frame_values": frame_values,
    }


@pytest.fixture
def script_path():
    def _script(name: str) -> str:
        return os.fspath(REPO_ROOT / "scripts" / name)

    return _script
