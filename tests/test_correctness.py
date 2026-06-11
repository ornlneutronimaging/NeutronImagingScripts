"""Regression tests for the correctness batch (2026-06-10 audit issues
1, 2, 4-7, 9, 10 + the generate_config int64 JSON fix).

Each test pins a bug that previously corrupted output silently or crashed
with a misleading error; see the audit for the full failure analyses.
"""

import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from neutronimaging.detector_correction import (
    correct_images,
    merge_meta_data,
    read_shutter_count,
    read_shutter_time,
    read_spectra,
    skipping_meta_data,
)


def _run_cli(script, *args):
    return subprocess.run(
        [sys.executable, script, *map(str, args)],
        capture_output=True,
        text=True,
        timeout=300,
    )


def _read_fixture_meta(ds):
    input_dir = ds["input_dir"]
    return (
        read_shutter_count(str(input_dir / f"{ds['prefix']}_ShutterCount.txt")),
        read_shutter_time(str(input_dir / f"{ds['prefix']}_ShutterTimes.txt")),
        read_spectra(str(input_dir / f"{ds['prefix']}_Spectra.txt")),
    )


class TestMergeMetaData:
    def test_valid_data_merges_quietly(self, synthetic_mcp_dataset, capsys):
        """audit #7: the debug print(f'{_df_shutter =}') polluted every call"""
        counts, times, spectra = _read_fixture_meta(synthetic_mcp_dataset)
        meta = merge_meta_data(counts, times, spectra)

        assert capsys.readouterr().out == ""
        assert (meta["shutter_index"] != -1).all()
        assert meta["shutter_n_ratio"].notna().all()

    def test_unmatched_spectra_row_raises(self, synthetic_mcp_dataset):
        """audit #1: a spectra time outside every shutter window previously
        kept shutter_counts=-1 / NaN ratio and flowed downstream as
        fully-NaN or negative-occupancy frames, silently"""
        counts, times, spectra = _read_fixture_meta(synthetic_mcp_dataset)
        bad = pd.concat(
            [spectra, pd.DataFrame({"shutter_time": [0.5], "counts": [123]})],
            ignore_index=True,
        )

        with pytest.raises(ValueError, match="outside every shutter window"):
            merge_meta_data(counts, times, bad)

    def test_asymmetric_shutter_files_raise(self, synthetic_mcp_dataset):
        """audit #7: a window filtered from only one sidecar file previously
        misaligned the positional concat — cryptic int(NaN) ValueError one
        way, silently shifted windows the other"""
        ds = synthetic_mcp_dataset
        counts, times, spectra = _read_fixture_meta(ds)

        # drop window 1 from the counts side only
        counts_missing = counts[counts["shutter_index"] != 1]
        with pytest.raises(ValueError, match="ShutterCount and ShutterTimes disagree"):
            merge_meta_data(counts_missing, times, spectra)

        # and from the times side only
        times_missing = times[times["shutter_index"] != 1]
        with pytest.raises(ValueError, match="ShutterCount and ShutterTimes disagree"):
            merge_meta_data(counts, times_missing, spectra)


class TestOccupancyPoleGuard:
    @pytest.mark.filterwarnings("error::RuntimeWarning")
    def test_saturated_occupancy_masks_to_nan(self):
        """audit #10: occupancy >= 1 previously emitted inf (pop == 1) or
        silently NEGATIVE intensities (pop > 1, cumsum exceeding counts);
        the filterwarnings marker also pins that the guarded division does
        not leak RuntimeWarnings"""
        # one shutter window, two frames of constant value 100 against
        # shutter_counts 150: frame 0 has pop = 100/150 (fine), frame 1 has
        # pop = 200/150 > 1 (pole crossed)
        meta = pd.DataFrame(
            {
                "shutter_time": [0.1, 0.2],
                "counts": [1, 1],
                "run_num": [0, 1],
                "shutter_index": [0, 0],
                "shutter_counts": [150, 150],
                "shutter_n_ratio": [1.0, 1.0],
            }
        )
        images = np.full((2, 4, 4), 100.0, dtype=np.float32)

        corrected = correct_images(images, meta)

        assert np.isfinite(corrected[0]).all()
        assert (corrected[0] > 0).all()
        assert np.isnan(corrected[1]).all()


class TestCliSpectraFormat:
    def test_skipimg_spectra_round_trips_through_read_spectra(self, synthetic_mcp_dataset, script_path):
        """audit #2: --skipimg previously rewrote *_Spectra.txt with pandas
        defaults (comma-separated WITH header) while the non-skip branch
        copies the headerless TSV original verbatim — read_spectra
        mis-parsed the rewritten file into one un-split column"""
        ds = synthetic_mcp_dataset
        result = _run_cli(script_path("mcp_detector_correction.py"), "--skipimg", ds["input_dir"], ds["output_dir"])
        assert result.returncode == 0, result.stderr

        out_spectra = ds["output_dir"] / f"{ds['prefix']}_Spectra.txt"
        parsed = read_spectra(str(out_spectra))

        n_kept = ds["n_groups"] * (ds["frames_per_group"] - 2)
        assert parsed.shape == (n_kept, 2)
        assert parsed.notna().all().all()

        counts, times, spectra = _read_fixture_meta(ds)
        expected = skipping_meta_data(merge_meta_data(counts, times, spectra))
        np.testing.assert_allclose(parsed["shutter_time"].values, expected["shutter_time"].values)
        np.testing.assert_allclose(parsed["counts"].values, expected["counts"].values)

        # byte-level format contract: headerless TSV with CRLF, like the
        # instrument-written original
        raw = out_spectra.read_bytes()
        assert b"\t" in raw and b"\r\n" in raw
        assert b"," not in raw and b"shutter_time" not in raw


class TestCliInputResolution:
    def test_duplicate_sets_resolve_to_first_sorted_prefix(self, synthetic_mcp_dataset, script_path):
        """audit #6: four independent unsorted globs could mix sidecar files
        from different duplicate sets; everything must derive from the
        first set in sorted order"""
        ds = synthetic_mcp_dataset
        input_dir = ds["input_dir"]

        # fabricate a complete second set whose prefix sorts AFTER the
        # primary; its frames carry different values so a mixed selection
        # would change the exported data
        dup_prefix = "ZZ_synth_999"
        for name in (
            "_ShutterCount.txt",
            "_ShutterTimes.txt",
            "_Spectra.txt",
            "_SummedImg.fits",
        ):
            src = input_dir / f"{ds['prefix']}{name}"
            (input_dir / f"{dup_prefix}{name}").write_bytes(src.read_bytes())
        from astropy.io import fits

        for k in range(ds["n_frames"]):
            hdu = fits.PrimaryHDU(np.full(ds["shape"], 999, dtype=">i2"))
            fits.HDUList([hdu]).writeto(str(input_dir / f"{dup_prefix}_{k:05d}.fits"))

        result = _run_cli(script_path("mcp_detector_correction.py"), input_dir, ds["output_dir"])
        assert result.returncode == 0, result.stderr
        assert "2 sets" in result.stdout

        exported = sorted(p.name for p in ds["output_dir"].glob("*.tif"))
        expected = sorted(f"{ds['prefix']}_{k:05d}.tif" for k in range(ds["n_frames"]))
        assert exported == expected, "exported frames must all come from the first sorted set"

    def test_missing_sidecar_fails_descriptively(self, synthetic_mcp_dataset, script_path):
        """audit #6: a missing sidecar previously died with a bare IndexError
        from glob(...)[0] before any validation ran"""
        ds = synthetic_mcp_dataset
        (ds["input_dir"] / f"{ds['prefix']}_ShutterTimes.txt").unlink()

        result = _run_cli(script_path("mcp_detector_correction.py"), ds["input_dir"], ds["output_dir"])
        assert result.returncode != 0
        assert "Expected sidecar file is missing" in result.stderr
        assert "IndexError" not in result.stderr

    def test_empty_input_dir_fails_descriptively(self, tmp_path, script_path):
        empty_in = tmp_path / "empty_in"
        out = tmp_path / "out"
        empty_in.mkdir()
        out.mkdir()

        result = _run_cli(script_path("mcp_detector_correction.py"), empty_in, out)
        assert result.returncode != 0
        assert "No *_ShutterCount.txt" in result.stderr


class TestTimeRange:
    @pytest.fixture(scope="class")
    def config(self, data_dir):
        from neutronimaging.preprocess import generate_config_CG1D

        return generate_config_CG1D(
            str(data_dir / "IPTS-20267/raw/radiographs"),
            str(data_dir / "IPTS-20267/raw/ob"),
            str(data_dir / "IPTS-20267/raw/df"),
        )

    def test_no_epoch_timestamps_leak(self, config):
        """audit #5: a category with sample but no OB previously reported
        time_range_s ~ 1.58e9 s (the raw epoch timestamp, ~50 years) —
        shipped in the committed example notebook"""
        for configs in config.values():
            for cfg in configs.values():
                for side, value in cfg["time_range_s"].items():
                    assert 0 <= value < 1e8, f"{side} leaked an epoch timestamp: {value}"

    def test_time_range_consistent_with_first_last_images(self, config):
        """audit #4: 'after' previously read the FIRST ob timestamp (copy-
        paste from the 'before' block) and subtracted in the wrong order;
        the reference implementation computes max(last_ob - last_sample, 0)"""
        checked_after = 0
        for configs in config.values():
            for cfg in configs.values():
                first, last = cfg["first_images"], cfg["last_images"]
                tr = cfg["time_range_s"]
                if first["sample"] and first["ob"]:
                    expected = max(first["sample"]["time_stamp"] - first["ob"]["time_stamp"], 0)
                    assert tr["before"] == expected
                else:
                    assert tr["before"] == 0.0
                if last["sample"] and last["ob"]:
                    expected = max(last["ob"]["time_stamp"] - last["sample"]["time_stamp"], 0)
                    assert tr["after"] == expected
                    checked_after += 1
                else:
                    assert tr["after"] == 0.0
        assert checked_after > 0, "shipped data must exercise the both-sides-present path"


class TestInJupyter:
    def test_headless_without_ipython_returns_false(self, monkeypatch):
        """audit #9: without IPython installed, in_jupyter() previously
        escaped its `except NameError` with a ModuleNotFoundError and
        crashed the caller"""
        monkeypatch.setitem(sys.modules, "IPython", None)

        from neutronimaging.util import in_jupyter

        assert in_jupyter() is False
