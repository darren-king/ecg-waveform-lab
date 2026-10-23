# ECG Waveform Lab

A small, self-contained learning environment for ECG signal engineering. Work
through real, openly released twelve-lead recordings and controlled synthetic
examples to understand what happens between a waveform file and a PyTorch tensor.

The tutorials assume comfortable Python and some mathematical or clinical
background, but introduce ECG storage and signal-processing conventions gradually.
They explain ADC calibration, physical units, lead ordering, anti-aliasing,
polyphase resampling, window selection, padding masks and batching. This is a
personal educational project, not a rhythm-classification or model-training project.

## Start from a fresh checkout

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and obtain this
repository. In its root directory:

```bash
uv sync --locked
uv run --frozen jupyter lab notebooks
```

Python 3.12.15 is selected by `.python-version`; uv can install it if necessary.
`uv.lock` fixes exact dependencies and distribution hashes. The supported Python
range is 3.12.x. These tutorials use CPU tensors; a GPU is unnecessary. Linux uses
PyTorch's public CPU wheel index to avoid installing a CUDA runtime for these lessons.
The environment has been executed on Apple Silicon macOS; other platform lockfile
entries are resolved, but their execution has not been verified here.

Choose **Python 3 (ipykernel)** in the Jupyter instance launched by `uv run` and run
each notebook from top to bottom. There is no data download step: the public sample
is bundled in the repository. After dependency installation, normal notebooks and
tests work offline. Do not substitute a globally installed kernel with different
packages. The automated runner below explicitly uses the current interpreter.

## Recommended notebook order

1. [Decoding and physical units](notebooks/01_decoding_and_physical_units.ipynb):
   read structural header fields, inspect ADC counts, understand per-lead
   calibration and broadcasting, plot voltages and restore canonical lead order.
2. [Resampling, windows and batches](notebooks/02_resampling_windows_and_batches.ipynb):
   inspect time grids, compare anti-aliased and naive downsampling, select windows,
   make padding visible, and reason about batch/time-mask dimensions.
3. [Real-record validation](notebooks/03_real_record_validation.ipynb): distinguish
   checksums from signal quality, examine explicit failures, inspect the complete
   small sample and use a PyTorch Dataset/DataLoader without introducing labels.

Each notebook is independent, explains operations before executing them, uses the
package's actual functions, exposes intermediate values, and includes parameters
to change safely. Synthetic demonstrations are labelled as such. Raw files remain
unchanged. Notebook sources have cleared outputs; execution shows modest local
plots and tables. Save executed copies in ignored `outputs/` when sharing source
changes so bulky plots and local session metadata do not enter version control.

## Reproduce the engineering checks

```bash
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen python tools/run_notebooks.py
uv run --frozen python tools/check_publication.py
```

Tests use temporary synthetic fixtures plus the twelve bundled public recordings.
They cover calibration, units, channel order, shape, invalid/missing data,
anti-aliasing, rational resampling, windows, padding, batching, and comparison with
WFDB's physical decoder. The notebook runner starts a fresh local kernel for each
notebook, using this environment, and saves new executed copies/PNG previews under
`outputs/notebooks-*/`. It does not install a global kernel or overwrite sources.
Local kernel execution requires permission to open localhost sockets.

## Data and provenance

The sample contains **12 recordings (24 native files, 20,797,831 bytes; 19.83 MiB)**
from the **PhysioNet/CinC Challenge 2021 v1.0.3** public release:

| Source cohort | Examples | Teaching purpose |
|---|---:|---|
| CPSC 2018 | 4 | One nine-second record for padding; three longer windows |
| PTB Diagnostic ECG | 3 | Native 1000 Hz recordings for downsampling |
| PTB-XL | 4 | Native 500 Hz, ten-second recordings for calibration and batching |
| St Petersburg INCART | 1 | 257 Hz long recording for rational resampling |

The fixed selection seed is `20261023`. No diagnosis, demographic attribute or
research label was used for selection. Headers are official v1.0.3 headers, and
both headers and MAT waveforms match the publisher's SHA-256 checksums. Original
bytes are retained, not converted or cropped for storage. The full sample fits in
ordinary Git without Git LFS; the largest native file is about 10.59 MiB.

[Sample provenance](data/sample_manifest.json) records the exact public paths,
engineering selection reasons and hashes. [Data attribution](data/ATTRIBUTION.md)
contains the release citation, underlying source credits, CC BY 4.0 information,
selection algorithm and modifications statement. Offline checks use the retained
[official checksum excerpt](data/SHA256SUMS.selected.txt). This project is not
endorsed by the original data creators or PhysioNet.

## Scientific scope and limits

- The reader deliberately supports the bundled single-file, twelve-lead Challenge
  MAT format, not every WFDB format or an arbitrary clinical archive.
- Resampling uses an explicit polyphase FIR and boundary assumption. There is no
  extra notch filtering, amplitude normalisation, augmentation or learned fit.
- Time masks identify padding, not diagnostic quality. Missing leads and nonfinite
  values fail explicitly; exact constant leads are flagged for inspection.
- The sample is purposefully small and not clinically representative. A successful
  decode or checksum cannot establish valid labels, correct electrode placement,
  diagnostic suitability or population generalisability.
- The signal interface is relevant to ECG machine-learning workflows, but clinical
  label construction, patient grouping, evaluation splits, model design and
  training require separate scientific work. None is implemented here.

See [the signal contract](docs/SIGNAL_CONTRACT.md) for operations and limitations,
[verification results](docs/VERIFICATION.md) for the tested environment, and
[development notes](docs/DEVELOPMENT.md) for contribution and publication checks.

## Licensing and independence

Original package code, notebook text and documentation are under the [MIT licence](LICENSE).
The bundled ECG files are separately **CC BY 4.0**, with required attribution in
[data/ATTRIBUTION.md](data/ATTRIBUTION.md). Data-derived plots retain those attribution
obligations. Dependencies are installed from their public packages under their own
licences; their source code is not vendored here.

The educational topics grew out of earlier ECG-learning work. This repository has
newly written standalone code and tutorials, its own environment and Git history,
and no runtime dependency on that work or its research artifacts.
