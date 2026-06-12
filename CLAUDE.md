# NeutronImagingScripts

Data-reduction modules and CLIs for ORNL neutron imaging: MCP detector
occupancy correction (VENUS) and CG1D configuration generation.

## Names

- PyPI package: `NeutronImaging` (PyPI still serves the ancient 1.2 until
  the v1.6 release)
- Python module: `neutronimaging` (flat layout, no src/)
- GitHub repo: `NeutronImagingScripts`

## Environment and commands

Pixi-managed — run everything through `pixi run`.

- `pixi run test` — pytest (the suite reads the shipped `data/` tree; the
  916-frame load makes it ~30-90 s)
- `pixi run pre-commit run --all-files` — lint (ruff, codespell, gitleaks,
  yamllint, taplo)
- Console commands from the editable install: `mcp_detector_correction`,
  `generate_config`. `scripts/*.py` are thin path-compatible wrappers around
  `neutronimaging.cli` — SNS/HFIR autoreduction may invoke them by path, so
  do not delete or rename them.

## Versioning and release

- versioningit from git tags; `neutronimaging/_version.py` is generated and
  gitignored. Dev versions read `1.5.0.dev*` because tag v1.5 is not an
  ancestor of main — the explicit v1.6 release tag supersedes this.
- No publish automation by decision (no known downstream pip consumers);
  release = tag on main → `python -m build` + twine.
- License is MIT (team decision 2026-06-12, NDP standard) — this settled the
  historical GPLv3-file / BSD-setup.py / LGPLv2-classifier contradiction.

## Branch model

`main` only (decided 2026-06-10). The remote `next`/`qa` branches are frozen
pre-2026 relics.

## Conventions and caveats

- ALL committed notebooks under `example/` carry executed outputs (users
  browse them on GitHub). NEVER clear outputs — re-execute instead; figures
  must be static (`%matplotlib inline`), not widget renders. The notebooks
  write `.npz` by-products next to themselves; those are gitignored.
- `data/` is ~571 MB of plain git objects, shared by tests and examples.
  Externalization (release asset / pooch) is an open decision — do not adopt
  LFS (tried and deliberately abandoned in ef81aed).
- Golden profiles `data/ref_*.npz` regenerate only via
  `scripts/regenerate_test_refs.py` after a reviewed behavior change.
- The auto gamma filter in `detector_correction.load_images` replicates
  NeuNorm 1.x exactly (dtype-max-minus-5 threshold, zero-padded 8-neighbor
  mean); the contract tests pin it — do not "simplify" it.
- The Timepix chip-geometry correction is a gated optional feature
  (`--chipcorrection`, `NeutronImaging[chipcorrection]` extra). It was
  deliberately converted from commented-out code to a documented switch
  (issue #13) — keep it that way.
