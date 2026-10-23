# Bundled sample: attribution, licensing and provenance

## Release and licence

All 24 native files in `sample/` come from **Will Two Do? Varying Dimensions in
Electrocardiography: the PhysioNet/Computing in Cardiology Challenge 2021, v1.0.3**.
The [release page](https://physionet.org/content/challenge-2021/1.0.3/) and its
[licence page](https://physionet.org/content/challenge-2021/view-license/1.0.3/)
identify the release as **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

The exact released `LICENSE.txt` is retained as
[LICENSE-CC-BY-4.0.txt](LICENSE-CC-BY-4.0.txt), verified against the published checksum.
See also the [CC BY 4.0 deed and legal-code link](https://creativecommons.org/licenses/by/4.0/).
Give appropriate credit, retain licence information, identify changes and do not
imply endorsement. The data creators provide the material without warranties.
The repository's MIT code licence does not replace this data licence.

The native files include the metadata already openly released in those headers.
No supplementary patient linkage tables, research annotations, clinical target
files or private metadata are included. Tutorials do not use diagnosis or
demographic comments. The original header comments remain intact so the files
retain their official release hashes.

## Credit the release and platform

- **Release:** Reyna M, Sadr N, Gu A, Perez Alday EA, Liu C, Seyedi S, Shah A,
  Clifford G (2022). *Will Two Do? Varying Dimensions in Electrocardiography:
  The PhysioNet/Computing in Cardiology Challenge 2021*, version 1.0.3.
  PhysioNet. [doi:10.13026/34va-7q14](https://doi.org/10.13026/34va-7q14).
- **Challenge publication:** Reyna MA et al. (2021). *Will Two Do? Varying Dimensions
  in Electrocardiography: The PhysioNet/Computing in Cardiology Challenge 2021*.
  Computing in Cardiology, pp. 1–4.
  [doi:10.23919/CinC53138.2021.9662687](https://doi.org/10.23919/CinC53138.2021.9662687).
- **PhysioNet:** Pollard T et al. (2026). *PhysioNet as a global platform for
  biomedical research*. Nature Health 1, 792–795.
  [doi:10.1038/s44360-026-00096-z](https://doi.org/10.1038/s44360-026-00096-z).
  This is the platform citation currently requested on the release page.

## Credit the underlying sources represented here

| Included cohort | Source credit and citations |
|---|---|
| CPSC 2018 | China Physiological Signal Challenge 2018, organised with ICBEB. Liu F et al. (2018), *An Open Access Database for Evaluating the Algorithms of Electrocardiogram Rhythm and Morphology Abnormality Detection*, Journal of Medical Imaging and Health Informatics 8, 1368–1373. [doi:10.1166/jmihi.2018.2442](https://doi.org/10.1166/jmihi.2018.2442); [original challenge](http://2018.icbeb.org/Challenge.html). |
| PTB Diagnostic ECG | Physikalisch-Technische Bundesanstalt and the contributing clinical team, including Michael Oeff, Hans Koch, Ralf Bousseljot, Dieter Kreiseler and Lothar Schmitz. [Dataset v1.0.0](https://physionet.org/content/ptbdb/1.0.0/), [doi:10.13026/C28C71](https://doi.org/10.13026/C28C71). Bousseljot R, Kreiseler D, Schnabel A (1995), *Nutzung der EKG-Signaldatenbank CARDIODAT der PTB über das Internet*, Biomedizinische Technik 40, supplement 1, p. 317. |
| PTB-XL | Wagner P, Strodthoff N, Bousseljot RD, Samek W, Schaeffter T (2020), [dataset v1.0.1](https://physionet.org/content/ptb-xl/1.0.1/), [doi:10.13026/x4td-x982](https://doi.org/10.13026/x4td-x982). Wagner P et al. (2020), *PTB-XL, a large publicly available electrocardiography dataset*, Scientific Data 7, 154, [doi:10.1038/s41597-020-0495-6](https://doi.org/10.1038/s41597-020-0495-6). |
| St Petersburg INCART | St Petersburg Institute of Cardiological Technics; developed by Viktor Tihonenko and Alexander Khaustov, with verification by Sergey Ivanov and Alexei Rivin, contributed through Evgeny Yakushenko. [Dataset v1.0.0](https://physionet.org/content/incartdb/1.0.0/), [doi:10.13026/C2V88N](https://doi.org/10.13026/C2V88N). |

These credits describe the origins of the selected Challenge files. The files
bundled here are the **Challenge v1.0.3 release copies**, not additional downloads
from those upstream database releases. Other releases/formats can have different
licence notices; this project does not relicense them or claim ownership of the ECGs.

## Selection: deterministic teaching coverage, not a clinical cohort

Seed: **20261023**. `tools/acquire_sample.py` documents the complete algorithm:
within each ordered stratum, lexicographically sort the official `.hea` paths,
shuffle with Python 3.12 `random.Random(f"{seed}:{cohort}:{kind}")`, then take the
first qualifying distinct records. Header checks and selection use only structural
fields, not age, sex, diagnoses, visual appearance or quality scores.

| Stratum, in order | Count | Structural criterion | Purpose |
|---|---:|---|---|
| CPSC `short` | 1 | Twelve leads; 5 ≤ duration < 10 s | Explicit right padding |
| CPSC `long` | 3 | Twelve leads; 10 < duration ≤ 60 s | Window position and duration |
| PTB `any` | 3 | Twelve leads | 1000 → 500 Hz conversion |
| PTB-XL `any` | 4 | Twelve leads | Native 500 Hz calibration and batching |
| INCART `any` | 1 | Twelve leads | 257 → 500 Hz rational resampling |

No selected recording was replaced because of its appearance or diagnosis. The
single-file format and per-file 16 MiB cap are explicit acquisition checks that fail
rather than silently selecting another example. All selected records satisfy them.
The twelve recordings total **20,797,831 bytes** in 24 native files. Observed
sampling rates are 257, 500 and 1000 Hz; durations range from 9 to 1800 seconds.
Lead permutation is demonstrated synthetically in memory because selection does
not require a naturally permuted recording.

## Verification and reconstruction

[The sample manifest](sample_manifest.json) stores each source cohort, public record
ID, original release paths, bundled relative paths, selection reason, byte sizes,
structural dimensions, and header/waveform SHA-256 hashes.
[SHA256SUMS.selected.txt](SHA256SUMS.selected.txt) retains the exact relevant lines
from the publisher's full checksum file, including its licence entry.

The full official checksum manifest is pinned to SHA-256:

```text
f29c2609343c38734f3a3d62be4a9052ca56a9e560e7ad2efc2118563fca2473
```

Its public source is
[Challenge v1.0.3 SHA256SUMS.txt](https://physionet.org/files/challenge-2021/1.0.3/SHA256SUMS.txt).
For initial assembly, existing official public caches were reused after validating
the checksum-manifest digest; every included header and waveform was then rehashed
against that list. Historical headers were not used. The licence was retrieved
from the official release and also verified. No local cache paths are required
or recorded in this repository.

Normal use verifies the bundle offline. A maintainer can reconstruct the same
selection directly from public URLs using this **explicit network operation**:

```bash
uv run --frozen python tools/acquire_sample.py --download-public-sample
```

This may fetch many candidate headers to find a short recording and can be slow.
It is not part of installation, tests or notebooks. Download caches are ignored.
Existing differing files are never overwritten. Rebuilding the selection is not
necessary for a fresh clone because the verified native examples are bundled.

## Modifications and derived examples

**No modifications** were made to the bundled native `.hea` or `.mat` bytes.
Their relative directory tree preserves the public release paths below `sample/`.
The licence file was renamed locally for clarity; its contents are unchanged.
The manifest and checksum excerpt are newly assembled provenance aids.

Notebook voltages, permutations, resampled signals, selected/padded windows and
plots are explicitly derived **in memory**. They are not written back to native
files. Sine-wave and arithmetic demonstrations are synthetic and are not clinical
recordings. Shared data-derived figures must retain source attribution and describe
those transformations. Nothing here is endorsed by the contributing institutions.
