"""Lazy access to the IPTS-20267 example/test dataset.

The dataset (~570 MB of FITS/TIFF frames plus the ``ref_*.npz`` golden
profiles) is no longer tracked in git. It is published once as a release
asset and fetched on demand with :mod:`pooch`. A source checkout that still
carries a populated ``data/`` directory uses it directly with no download.

Resolution order in :func:`example_data_dir`:

1. ``$NEUTRONIMAGING_DATA_DIR`` if set (CI mirror / a local copy).
2. A populated ``data/`` next to the source tree (developer checkout).
3. Download + unpack the release tarball into the pooch cache.

Bump ``_ARCHIVE``/``_ARCHIVE_SHA256``/``_DATA_TAG`` together whenever the
dataset itself changes (regenerate goldens via
``scripts/regenerate_test_refs.py`` first).
"""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
# repo layout is flat (no src/): data/ sits next to the neutronimaging/ package
_REPO_DATA = _PACKAGE_ROOT.parent / "data"

_DATA_TAG = "data-v1"
_ARCHIVE = "nis-test-data-v1.tar.gz"
_ARCHIVE_SHA256 = "afb44dbd9875705e271c5199de57f998325220c279b4aa97abdd7392bc7a4773"
_BASE_URL = f"https://github.com/ornlneutronimaging/NeutronImagingScripts/releases/download/{_DATA_TAG}/"


def _has_data(path: Path) -> bool:
    return path.is_dir() and any(path.iterdir())


def example_data_dir() -> Path:
    """Return the example-data root, fetching it on first use if needed.

    Returns
    -------
    Path
        Directory containing ``IPTS-20267/``, the ``OB_1_005_*`` frames and
        the ``ref_*.npz`` golden profiles, with the same layout the tests and
        example notebook expect.
    """
    override = os.environ.get("NEUTRONIMAGING_DATA_DIR")
    if override:
        return Path(override)
    if _has_data(_REPO_DATA):
        return _REPO_DATA
    return _fetch()


def ensure_repo_data() -> Path:
    """Materialize the example dataset at the repo ``data/`` path.

    Convenience for the example notebooks, which reference the data with
    ``../data`` relative paths. On first use this downloads + unpacks the
    release tarball and links (or copies) it to ``data/``; a no-op once that
    directory is populated. Returns the data root.
    """
    if _has_data(_REPO_DATA):
        return _REPO_DATA
    src = _fetch()
    if _REPO_DATA.exists():
        import shutil

        shutil.copytree(src, _REPO_DATA, dirs_exist_ok=True)
    else:
        try:
            _REPO_DATA.symlink_to(src, target_is_directory=True)
        except OSError:  # pragma: no cover - platforms/filesystems without symlinks
            import shutil

            shutil.copytree(src, _REPO_DATA)
    return _REPO_DATA


def _fetch() -> Path:
    try:
        import pooch
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without pooch
        raise ModuleNotFoundError(
            "The example dataset is not present locally and 'pooch' is not installed, "
            "so it cannot be downloaded. Install pooch (it ships in the pixi test and "
            "jupyter environments; for pip use `pip install pooch`) or point "
            "NEUTRONIMAGING_DATA_DIR at an existing copy of the data/ tree."
        ) from exc

    paths = pooch.retrieve(
        url=_BASE_URL + _ARCHIVE,
        known_hash="sha256:" + _ARCHIVE_SHA256,
        fname=_ARCHIVE,
        path=pooch.os_cache("neutronimaging"),
        processor=pooch.Untar(extract_dir=_DATA_TAG),
    )
    # Untar returns every extracted member; their common parent is the
    # extract_dir, which mirrors the original data/ layout.
    return Path(os.path.commonpath(paths))


if __name__ == "__main__":  # `pixi run fetch-data` / `python -m neutronimaging.datasets`
    print(example_data_dir())
