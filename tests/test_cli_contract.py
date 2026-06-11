"""CLI and export contract tests for the scripts/ entry points.

These pin the on-disk output contract of mcp_detector_correction (filenames,
dtype, full-array values, sidecar copies) ahead of the NeuNorm removal —
previously the export path had zero test coverage. The scripts have no
main() function, so they are exercised via subprocess, which also pins the
autoreduction-facing command-line interface itself.
"""

import filecmp
import json
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

from neutronimaging.detector_correction import (
    correct_images,
    load_images,
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


def _read_tiff(path) -> np.ndarray:
    with Image.open(path) as img:
        return np.array(img)


def _expected_corrected(input_dir, skip=False) -> np.ndarray:
    prefix_glob = sorted(input_dir.glob("*_ShutterCount.txt"))[0]
    stem = prefix_glob.name.replace("_ShutterCount.txt", "")
    meta = merge_meta_data(
        read_shutter_count(str(input_dir / f"{stem}_ShutterCount.txt")),
        read_shutter_time(str(input_dir / f"{stem}_ShutterTimes.txt")),
        read_spectra(str(input_dir / f"{stem}_Spectra.txt")),
    )
    o_norm = load_images(str(input_dir))
    return correct_images(o_norm, meta, skip_first_and_last=skip)


class TestMcpDetectorCorrectionCli:
    def test_end_to_end_export_contract(self, synthetic_mcp_dataset, script_path):
        """Full-array, full-naming export contract for the no-skip path."""
        ds = synthetic_mcp_dataset
        result = _run_cli(script_path("mcp_detector_correction.py"), ds["input_dir"], ds["output_dir"])
        assert result.returncode == 0, result.stderr

        # one float32 TIFF per source frame, named after the source stem
        tiffs = sorted(ds["output_dir"].glob("*.tif"))
        expected_names = [f"{ds['prefix']}_{k:05d}.tif" for k in range(ds["n_frames"])]
        assert [t.name for t in tiffs] == expected_names

        expected = _expected_corrected(ds["input_dir"]).astype(np.float32)
        for k, tiff in enumerate(tiffs):
            on_disk = _read_tiff(tiff)
            assert on_disk.dtype == np.float32
            np.testing.assert_array_equal(on_disk, expected[k])

        # sidecar metadata files are copied verbatim in the no-skip path
        for suffix in ("_ShutterCount.txt", "_ShutterTimes.txt", "_Spectra.txt", "_SummedImg.fits"):
            name = f"{ds['prefix']}{suffix}"
            assert filecmp.cmp(ds["input_dir"] / name, ds["output_dir"] / name, shallow=False), (
                f"{name} was not copied verbatim"
            )

    def test_skipimg_frame_count_and_spectra_emitted(self, synthetic_mcp_dataset, script_path):
        """--skipimg drops the first and last frame of each shutter group."""
        ds = synthetic_mcp_dataset
        result = _run_cli(script_path("mcp_detector_correction.py"), "--skipimg", ds["input_dir"], ds["output_dir"])
        assert result.returncode == 0, result.stderr

        tiffs = sorted(ds["output_dir"].glob("*.tif"))
        assert len(tiffs) == ds["n_groups"] * (ds["frames_per_group"] - 2)
        assert (ds["output_dir"] / f"{ds['prefix']}_Spectra.txt").exists()

    def test_skipimg_exports_true_source_names_and_content(self, synthetic_mcp_dataset, script_path):
        """Kept frames must be written under their true source stems, AND
        each file must contain the corrected frame belonging to that source
        — name-set equality alone would not catch frames written under the
        right names in the wrong order."""
        ds = synthetic_mcp_dataset
        result = _run_cli(script_path("mcp_detector_correction.py"), "--skipimg", ds["input_dir"], ds["output_dir"])
        assert result.returncode == 0, result.stderr

        kept = [
            g * ds["frames_per_group"] + i for g in range(ds["n_groups"]) for i in range(1, ds["frames_per_group"] - 1)
        ]
        expected_names = {f"{ds['prefix']}_{k:05d}.tif" for k in kept}
        actual_names = {t.name for t in ds["output_dir"].glob("*.tif")}
        assert actual_names == expected_names

        # content mapping: row r of the skip-corrected stack belongs to
        # kept source frame kept[r]
        expected = _expected_corrected(ds["input_dir"], skip=True).astype(np.float32)
        assert expected.shape[0] == len(kept)
        for row, k in enumerate(kept):
            on_disk = _read_tiff(ds["output_dir"] / f"{ds['prefix']}_{k:05d}.tif")
            np.testing.assert_array_equal(
                on_disk,
                expected[row],
                err_msg=f"frame written under source name {k:05d} does not match its corrected data",
            )

    def test_chip_correction_gated_off_by_default_and_invocable(self, synthetic_mcp_dataset, monkeypatch):
        """The Timepix chip-geometry correction is a proper optional feature:
        off by default, and when enabled it routes the corrected stack
        through TimepixGeometryCorrection (stubbed here so the test does not
        depend on the optional package being installed)."""
        import sys
        import types

        ds = synthetic_mcp_dataset
        input_dir = ds["input_dir"]
        meta = merge_meta_data(
            read_shutter_count(str(input_dir / f"{ds['prefix']}_ShutterCount.txt")),
            read_shutter_time(str(input_dir / f"{ds['prefix']}_ShutterTimes.txt")),
            read_spectra(str(input_dir / f"{ds['prefix']}_Spectra.txt")),
        )
        images = load_images(str(input_dir))

        marker = np.full((ds["n_frames"], 4, 4), 42.0, dtype=np.float32)
        received = {}

        class _StubCorrector:
            def __init__(self, raw_images=None, images_path=None, config=None):
                received["raw_images"] = raw_images

            def correct(self, display=False):
                return marker

        stub_module = types.ModuleType("timepix_geometry_correction.correct")
        stub_module.TimepixGeometryCorrection = _StubCorrector
        stub_package = types.ModuleType("timepix_geometry_correction")
        stub_package.correct = stub_module
        monkeypatch.setitem(sys.modules, "timepix_geometry_correction", stub_package)
        monkeypatch.setitem(sys.modules, "timepix_geometry_correction.correct", stub_module)

        # default: corrector never touched
        default_result = correct_images(images, meta)
        assert "raw_images" not in received

        # enabled: stack routed through the corrector, its output returned
        enabled_result = correct_images(images, meta, apply_chip_correction=True)
        np.testing.assert_array_equal(received["raw_images"], default_result)
        np.testing.assert_array_equal(enabled_result, marker)

    def test_chip_correction_missing_package_is_actionable(self, synthetic_mcp_dataset):
        """Enabling the flag without the optional package must raise an
        ImportError that says what to install, not a bare traceback."""
        try:
            import timepix_geometry_correction  # noqa: F401

            pytest.skip("timepix-geometry-correction installed; error path not reachable")
        except ImportError:
            pass

        ds = synthetic_mcp_dataset
        input_dir = ds["input_dir"]
        meta = merge_meta_data(
            read_shutter_count(str(input_dir / f"{ds['prefix']}_ShutterCount.txt")),
            read_shutter_time(str(input_dir / f"{ds['prefix']}_ShutterTimes.txt")),
            read_spectra(str(input_dir / f"{ds['prefix']}_Spectra.txt")),
        )
        images = load_images(str(input_dir))

        with pytest.raises(ImportError, match="timepix-geometry-correction"):
            correct_images(images, meta, apply_chip_correction=True)

    def test_skip_selector_consistency(self, synthetic_mcp_dataset):
        """correct_images inlines its own skip logic; pin that it selects the
        same rows as skipping_meta_data, which the CLI uses for the spectra."""
        ds = synthetic_mcp_dataset
        input_dir = ds["input_dir"]
        meta = merge_meta_data(
            read_shutter_count(str(input_dir / f"{ds['prefix']}_ShutterCount.txt")),
            read_shutter_time(str(input_dir / f"{ds['prefix']}_ShutterTimes.txt")),
            read_spectra(str(input_dir / f"{ds['prefix']}_Spectra.txt")),
        )
        o_norm = load_images(str(input_dir))

        full = correct_images(o_norm, meta)
        skipped = correct_images(o_norm, meta, skip_first_and_last=True)
        kept_run_nums = skipping_meta_data(meta)["run_num"].values

        assert skipped.shape[0] == len(kept_run_nums)
        np.testing.assert_array_equal(skipped, full[kept_run_nums])


class TestGenerateConfigCli:
    def test_single_image_dir(self, data_dir, tmp_path, script_path):
        out = tmp_path / "config.json"
        result = _run_cli(
            script_path("generate_config.py"),
            data_dir / "IPTS-20267/raw/radiographs",
            data_dir / "IPTS-20267/raw/ob",
            data_dir / "IPTS-20267/raw/df",
            out,
        )
        assert result.returncode == 0, result.stderr
        assert out.exists()
        json.loads(out.read_text())  # valid JSON

    def test_comma_separated_image_dirs_and_tolerance(self, data_dir, tmp_path, script_path):
        out = tmp_path / "config.json"
        imgdirs = ",".join(
            [
                str(data_dir / "IPTS-20267/raw/radiographs"),
                str(data_dir / "IPTS-20267/raw/alignment_calibration"),
            ]
        )
        result = _run_cli(
            script_path("generate_config.py"),
            imgdirs,
            data_dir / "IPTS-20267/raw/ob",
            data_dir / "IPTS-20267/raw/df",
            out,
            "--tolerance=2.0",
        )
        assert result.returncode == 0, result.stderr
        assert out.exists()
        json.loads(out.read_text())
