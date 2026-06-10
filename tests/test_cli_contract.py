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
        result = _run_cli(
            script_path("mcp_detector_correction.py"), "--skipimg", ds["input_dir"], ds["output_dir"]
        )
        assert result.returncode == 0, result.stderr

        tiffs = sorted(ds["output_dir"].glob("*.tif"))
        assert len(tiffs) == ds["n_groups"] * (ds["frames_per_group"] - 2)
        assert (ds["output_dir"] / f"{ds['prefix']}_Spectra.txt").exists()

    @pytest.mark.xfail(
        strict=True,
        reason="NeuNorm 1.x export zip-truncates the full filename list against the "
        "skip-reduced stack, mislabeling kept frames with the first N source names; "
        "the loader-replacement PR fixes this to use the true kept source names "
        "(remove this marker there).",
    )
    def test_skipimg_exports_true_source_names(self, synthetic_mcp_dataset, script_path):
        """Kept frames must be written under their true source stems."""
        ds = synthetic_mcp_dataset
        result = _run_cli(
            script_path("mcp_detector_correction.py"), "--skipimg", ds["input_dir"], ds["output_dir"]
        )
        assert result.returncode == 0, result.stderr

        kept = [
            g * ds["frames_per_group"] + i
            for g in range(ds["n_groups"])
            for i in range(1, ds["frames_per_group"] - 1)
        ]
        expected_names = {f"{ds['prefix']}_{k:05d}.tif" for k in kept}
        actual_names = {t.name for t in ds["output_dir"].glob("*.tif")}
        assert actual_names == expected_names

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


GENERATE_CONFIG_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="generate_config_CG1D's output= path json.dumps numpy int64 scalars and "
    "crashes (TypeError: Object of type int64 is not JSON serializable), so the CLI "
    "is broken end-to-end on modern numpy/pandas; the existing test_preprocess smoke "
    "never exercises output=. Fix lands in the correctness PR (remove this marker there).",
)


class TestGenerateConfigCli:
    @GENERATE_CONFIG_XFAIL
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

    @GENERATE_CONFIG_XFAIL
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
