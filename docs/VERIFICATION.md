# Verification record

The standalone implementation, bundled sample and tutorials were checked on
Apple Silicon macOS using Python 3.12.15 and uv 0.13.5. The source notebooks retain
cleared outputs. Executed copies and plot previews are local, ignored artifacts.

## Declared environment

`uv.lock` records exact distributions and hashes. Direct dependency versions in
the verified environment are:

| Package | Version |
|---|---|
| NumPy | 2.5.4 |
| SciPy | 1.18.1 |
| WFDB | 4.3.1 |
| PyTorch | 2.14.1 |
| Matplotlib | 3.11.2 |
| pandas | 3.1.0 |
| JupyterLab | 4.6.4 |
| ipykernel | 7.4.0 |
| nbclient | 0.11.0 |
| nbformat | 5.11.1 |

Only CPU execution is needed or tested. Linux and Windows execution have not been
verified. Dependency resolution alone does not establish cross-platform support.

## Fresh environment and relocation check

The 47 publication-candidate files were copied into the final independent project
folder without any environment, cache, outputs or Git history. `uv sync --locked
--offline` created a new Python 3.12.15 environment from the locally cached locked
packages. The imported package resolved to that new checkout's own `src/` tree.
All 18 tests and all three fresh-kernel notebooks passed again there; `uv pip check`
confirmed compatibility of all 118 installed packages. This was a clean source-copy
check, not a Git clone: no initial commit or remote had been created.

## Checks completed during construction

- All 18 automated tests passed: 15 synthetic tests and three bundled-sample tests.
- All 12 records decoded; physical values matched WFDB's decoder within the test
  tolerance (absolute tolerance 1e-10 mV).
- All 24 native files and the data licence matched the retained official checksums.
- The complete official release checksum manifest was verified against its pinned
  SHA-256 before selection. Checksum-verified public cached copies were reused
  during construction; no fresh download of every selected waveform is claimed.
- Each tutorial executed in a new kernel with no cell errors:

| Notebook | Code cells | Figures | Result |
|---|---:|---:|---|
| 01 — decoding and physical units | 10 | 1 | Pass |
| 02 — resampling, windows and batches | 13 | 3 | Pass |
| 03 — real-record validation | 11 | 1 | Pass |

Calibration, aliasing and padding figures were visually checked for readable
labels, physical units and clearly marked synthetic transformations. Tutorials
expose native sampling rates, canonical lead order, float32 windows and time masks.

Publication checks cover absolute local paths, common secret patterns, private
research references, unexpected binaries, native-file hashes, file sizes, source
syntax and cleared notebook outputs. This bounded check complements manual review;
it is not a general-purpose secret detector or legal clearance.

## Reproduce

```bash
uv sync --locked
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python tools/run_notebooks.py
uv run --frozen python tools/check_publication.py
```

These commands need no data network access. Installing dependencies may require
public package downloads. No clinical validity, classification performance or
population representativeness is inferred from these engineering checks.
