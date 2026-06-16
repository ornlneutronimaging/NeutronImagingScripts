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

- `pixi run test` — pytest (the data-dependent tests read the IPTS-20267
  dataset; it is fetched on first run via pooch, then the 916-frame load
  makes the suite ~30-90 s). Tests skip rather than fail if the dataset is
  unreachable.
- `pixi run fetch-data` — pre-download the example dataset into the pooch
  cache (CI runs this before the tests so a missing asset fails loudly)
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
- Release = tag on main (`v*`). A push of a `v*` tag triggers
  `.github/workflows/publish.yml`, which builds the sdist+wheel and uploads to
  PyPI via OIDC trusted publishing (no API token). The publish job runs in the
  `pypi` GitHub environment; the trusted publisher on PyPI is bound to owner
  `ornlneutronimaging`, repo `NeutronImagingScripts`, workflow `publish.yml`,
  environment `pypi`. (Supersedes the earlier "no publish automation" decision,
  2026-06-16.) Untagged commits build dev versions and are not published.
- License is MIT (team decision 2026-06-12, NDP standard) — this settled the
  historical GPLv3-file / BSD-setup.py / LGPLv2-classifier contradiction.

## Branch model

`main` only (decided 2026-06-10). The stale `next`/`qa` relic branches and
all merged feature branches were deleted 2026-06-15; the only non-`main`
remotes left are Jean's unmerged WIP (`11_pixi`, `8_tof_normalization`) and
`item376_autonorm_mars`.

## Conventions and caveats

- ALL committed notebooks under `example/` carry executed outputs (users
  browse them on GitHub). NEVER clear outputs — re-execute instead; figures
  must be static (`%matplotlib inline`), not widget renders. The notebooks
  write `.npz` by-products next to themselves; those are gitignored.
- `data/` (the ~570 MB IPTS-20267 dataset shared by tests and examples) is
  externalized: untracked from git (gitignored), published as the `data-v1`
  release asset `nis-test-data-v1.tar.gz`, and fetched on demand by
  `neutronimaging.datasets` (pooch). `example_data_dir()` resolves it
  ($NEUTRONIMAGING_DATA_DIR → a populated local `data/` → download);
  `ensure_repo_data()` materializes it at `data/` for the notebooks. Bump the
  tag + sha256 in `datasets.py` together if the dataset changes. Do NOT adopt
  LFS (tried and deliberately abandoned in ef81aed). The 274 MB of history is
  intentionally left intact — a `git filter-repo` purge to shrink clones is a
  separate, coordinate-with-Jean follow-up (it rewrites his branch SHAs).
- Golden profiles `ref_*.npz` (inside the dataset) regenerate only via
  `scripts/regenerate_test_refs.py` after a reviewed behavior change.
- The auto gamma filter in `detector_correction.load_images` replicates
  NeuNorm 1.x exactly (dtype-max-minus-5 threshold, zero-padded 8-neighbor
  mean); the contract tests pin it — do not "simplify" it.
- The Timepix chip-geometry correction is a gated optional feature
  (`--chipcorrection`, `NeutronImaging[chipcorrection]` extra). It was
  deliberately converted from commented-out code to a documented switch
  (issue #13) — keep it that way.
