"""Contract tests pinning load_images() ahead of the NeuNorm removal.

The existing npz regression tests assert per-frame *means*, which are
invariant under transpose/flip/rotation/pixel permutation; these tests pin
the parts a loader replacement could silently break: pixel values against
an independent reader, dtype, ordering, exclusions, truncation semantics,
and image orientation.
"""

import shutil

import numpy as np
import pytest
from astropy.io import fits

from neutronimaging.detector_correction import load_images


def _write_fits_int16(path, image: np.ndarray) -> None:
    """Write a big-endian int16 FITS file, matching the shipped MCP data."""
    hdu = fits.PrimaryHDU(image.astype(">i2"))
    fits.HDUList([hdu]).writeto(str(path))


def _stack(o_norm) -> np.ndarray:
    return np.array(o_norm.data["sample"]["data"])


def _astropy_read_float32(path) -> np.ndarray:
    with fits.open(str(path), ignore_missing_end=True) as hdulist:
        return np.squeeze(np.asarray(hdulist[0].data, dtype=np.float32))


class TestShippedDataContract:
    """Pin the load contract on the full shipped 916-frame OB stack."""

    @pytest.fixture(scope="class")
    def frames(self, data_dir):
        """Per-frame view of the shipped stack.

        Deliberately NOT stacked into one contiguous array: these
        assertions only need per-frame access, and stacking would
        duplicate ~1 GB alongside the loader's own copy in CI.
        """
        return load_images(str(data_dir)).data["sample"]["data"]

    def test_shape_and_dtype(self, frames):
        assert len(frames) == 916
        assert all(frame.shape == (512, 512) for frame in frames)
        assert {frame.dtype for frame in frames} == {np.dtype(np.float32)}

    def test_sampled_pixel_goldens(self, frames):
        """Spot values at off-center coordinates fail loudly on any spatial
        transform, unlike the mean-profile regressions."""
        assert frames[100][37, 411] == 69.0
        assert frames[100][250, 17] == 194.0
        assert frames[500][37, 411] == 55.0
        assert frames[500][250, 17] == 138.0
        assert frames[915][37, 411] == 43.0
        assert frames[915][250, 17] == 84.0

    def test_frame0_total_counts(self, frames):
        """Frame 0's pixel sum equals the first Spectra counts entry."""
        assert float(frames[0].sum()) == 162259.0


class TestLoadSemantics:
    def test_values_match_independent_reader(self, data_dir, tmp_path):
        """Pixel-value parity against a direct astropy read.

        The shipped frames are int16 far below the auto-gamma-filter
        threshold (max value 1514 vs 32762), so loaded values must equal
        the raw file contents exactly.
        """
        names = ["OB_1_005_00000.fits", "OB_1_005_00100.fits", "OB_1_005_00500.fits"]
        for name in names:
            shutil.copy(data_dir / name, tmp_path / name)

        loaded = _stack(load_images(str(tmp_path)))
        assert loaded.shape[0] == len(names)
        for frame, name in zip(loaded, names, strict=True):
            np.testing.assert_array_equal(frame, _astropy_read_float32(tmp_path / name))

    def test_sorted_order_and_summedimg_excluded(self, data_dir, tmp_path):
        """Frames load in sorted-filename order; *_SummedImg* is excluded."""
        # copy in deliberately unsorted creation order
        for name in ["OB_1_005_00500.fits", "OB_1_005_00000.fits", "OB_1_005_00100.fits"]:
            shutil.copy(data_dir / name, tmp_path / name)
        shutil.copy(data_dir / "OB_1_005_00000.fits", tmp_path / "OB_1_005_SummedImg.fits")

        loaded = _stack(load_images(str(tmp_path)))
        assert loaded.shape[0] == 3  # SummedImg excluded
        np.testing.assert_array_equal(loaded[0], _astropy_read_float32(tmp_path / "OB_1_005_00000.fits"))
        np.testing.assert_array_equal(loaded[2], _astropy_read_float32(tmp_path / "OB_1_005_00500.fits"))

    def test_orientation_canary(self, tmp_path):
        """A corner marker must land exactly where it was written.

        The shipped frames carry no orientation-asymmetric ground truth,
        so a vertical flip (the classic FITS origin bug) would be invisible
        to every other test.
        """
        size, row, col = 32, 3, 7
        image = np.full((size, size), 100, dtype=np.int16)
        image[row, col] = 999
        _write_fits_int16(tmp_path / "marker_00000.fits", image)

        loaded = _stack(load_images(str(tmp_path)))[0]
        assert loaded[row, col] == 999.0
        assert loaded[col, row] == 100.0  # transpose guard
        assert loaded[size - 1 - row, col] == 100.0  # vertical-flip guard
        assert loaded[row, size - 1 - col] == 100.0  # horizontal-flip guard

    def test_duplicated_runs_truncation(self, tmp_path):
        """nbr_of_duplicated_runs=N keeps the first 1/N of the sorted list."""
        for k in range(4):
            _write_fits_int16(tmp_path / f"a_set1_{k:05d}.fits", np.full((16, 16), 1, dtype=np.int16))
            _write_fits_int16(tmp_path / f"b_set2_{k:05d}.fits", np.full((16, 16), 2, dtype=np.int16))

        loaded = _stack(load_images(str(tmp_path), nbr_of_duplicated_runs=2))
        assert loaded.shape[0] == 4
        np.testing.assert_array_equal(loaded, np.full((4, 16, 16), 1, dtype=np.float32))

    @pytest.mark.parametrize("jupyter", [False, True])
    def test_in_jupyter_both_paths(self, tmp_path, monkeypatch, jupyter):
        """load_images consults in_jupyter() for its progress bar; both
        branches must load identically (a loader rewrite could silently
        drop the plumbing)."""
        import neutronimaging.util

        monkeypatch.setattr(neutronimaging.util, "in_jupyter", lambda: jupyter)
        _write_fits_int16(tmp_path / "x_00000.fits", np.full((16, 16), 7, dtype=np.int16))

        loaded = _stack(load_images(str(tmp_path)))
        np.testing.assert_array_equal(loaded[0], np.full((16, 16), 7, dtype=np.float32))
