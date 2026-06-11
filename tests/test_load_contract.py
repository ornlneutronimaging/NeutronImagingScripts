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


def _stack(images) -> np.ndarray:
    return np.asarray(images)


def _astropy_read_float32(path) -> np.ndarray:
    with fits.open(str(path), ignore_missing_end=True) as hdulist:
        return np.squeeze(np.asarray(hdulist[0].data, dtype=np.float32))


class TestShippedDataContract:
    """Pin the load contract on the full shipped 916-frame OB stack."""

    @pytest.fixture(scope="class")
    def frames(self, data_dir):
        """The shipped stack; load_images() now returns the float32
        ndarray directly, so iterating/indexing it yields per-frame views
        with no additional copy."""
        return load_images(str(data_dir))

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

    def test_empty_directory_raises(self, tmp_path):
        """assert loading from a directory without frames fails fast
        instead of returning a degenerate empty array"""
        with pytest.raises(OSError, match="No FITS frame files"):
            load_images(str(tmp_path))

    def test_zero_duplicated_runs_raises(self, tmp_path):
        """assert nbr_of_duplicated_runs < 1 is rejected up front
        (previously a bare ZeroDivisionError)"""
        from neutronimaging.detector_correction import list_image_files

        with pytest.raises(ValueError, match="nbr_of_duplicated_runs"):
            list_image_files(str(tmp_path), nbr_of_duplicated_runs=0)

    def test_progress_bar_headless(self, tmp_path):
        """Loading must work headless: the progress bar is tqdm.auto,
        which renders a widget in Jupyter and a console bar elsewhere
        (this replaced the in_jupyter()/NeuNorm notebook= plumbing)."""
        _write_fits_int16(tmp_path / "x_00000.fits", np.full((16, 16), 7, dtype=np.int16))

        loaded = _stack(load_images(str(tmp_path)))
        np.testing.assert_array_equal(loaded[0], np.full((16, 16), 7, dtype=np.float32))


class TestAutoGammaFilter:
    """Pin exact NeuNorm 1.x gamma-filter parity (maintainer decision:
    replicate, not drop). Every expected value below was verified against
    NeuNorm 1.6.12 itself before the removal: pixels strictly above
    iinfo(dtype).max - 5 are replaced by the mean of their 8 neighbors,
    zero-padded at borders, computed on the unfiltered image; float data
    passes through untouched."""

    def _load_single(self, tmp_path, image: np.ndarray) -> np.ndarray:
        _write_fits_int16(tmp_path / "g_00000.fits", image)
        return _stack(load_images(str(tmp_path)))[0]

    def test_interior_saturated_pixel_neighbor_mean(self, tmp_path):
        image = np.full((5, 5), 8, dtype=np.int16)
        image[2, 2] = 32767
        image[1, 1], image[1, 2], image[1, 3] = 10, 20, 30
        loaded = self._load_single(tmp_path, image)
        assert loaded[2, 2] == (10 + 20 + 30 + 8 * 5) / 8.0  # = 12.5, verified vs 1.x
        assert loaded[1, 1] == 10.0  # neighbors untouched

    def test_corner_saturated_pixel_zero_padding(self, tmp_path):
        image = np.full((5, 5), 8, dtype=np.int16)
        image[0, 0] = 32767
        loaded = self._load_single(tmp_path, image)
        assert loaded[0, 0] == 3.0  # (3 real neighbors x 8) / 8, verified vs 1.x

    def test_adjacent_saturated_use_unfiltered_neighbors(self, tmp_path):
        image = np.full((5, 5), 8, dtype=np.int16)
        image[2, 2] = image[2, 3] = 32767
        loaded = self._load_single(tmp_path, image)
        expected = (8 * 7 + 32767) / 8.0  # = 4102.875, verified vs 1.x
        assert loaded[2, 2] == expected
        assert loaded[2, 3] == expected

    def test_threshold_is_strict(self, tmp_path):
        image = np.full((5, 5), 8, dtype=np.int16)
        image[2, 2] = 32762  # == iinfo(int16).max - 5: NOT above threshold
        loaded = self._load_single(tmp_path, image)
        assert loaded[2, 2] == 32762.0

        image[2, 2] = 32763  # strictly above: replaced
        for old in tmp_path.glob("*.fits"):
            old.unlink()
        loaded = self._load_single(tmp_path, image)
        assert loaded[2, 2] == 8.0

    def test_float_fits_passes_through_unfiltered(self, tmp_path):
        image = np.full((5, 5), 1.0e30, dtype=np.float64)
        hdu = fits.PrimaryHDU(image)
        fits.HDUList([hdu]).writeto(str(tmp_path / "f_00000.fits"))
        loaded = _stack(load_images(str(tmp_path)))[0]
        assert loaded.dtype == np.float32
        np.testing.assert_array_equal(loaded, image.astype(np.float32))
