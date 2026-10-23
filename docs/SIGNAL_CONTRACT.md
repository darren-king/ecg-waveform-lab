# Signal contract and scientific boundaries

The public implementation is `src/ecg_waveform_lab/signal.py`. Notebooks expose its
stages and call these same functions. There is no second notebook-only loader.

| Operation | Input | Output / behaviour |
|---|---|---|
| `read_native` | Local `.hea` with its declared `.mat` file | `NativeECG`, native channel order and rate, ADC counts plus float64 mV |
| `calibrate` | `(12, N)` counts; 12 gains, baselines and units | `(counts - baseline) / gain`, converted to mV per channel |
| `reorder_leads` | Physical array plus channel names | Canonical I, II, III, aVR, aVL, aVF, V1–V6 order |
| `resample_signal` | Full `(12, N)` array and two rates | Float64 values at the target rate, polyphase FIR |
| `make_window` | Canonical mV array already on target grid | CPU float32 tensor and boolean time mask |
| `prepare_ecg` | `NativeECG` | Compose ordering → full-record resampling → windowing |
| `collate_windows` | Compatible windows | `(B, 12, T)` plus `(B, T)` mask and ordered public record IDs |
| `WaveformDataset` | Sample catalog entries | Load and prepare one reference when indexed |

Defaults are 500 Hz and ten seconds, giving `(12, 5000)` for one recording.
Times must land on the target sample grid. The half-open ten-second interval has
samples at 0 through 9.998 s; its last timestamp is not its nominal duration.
Units remain mV. There is no learned normalisation or clinical label output.

## Storage and calibration

WFDB parses the header; SciPy decodes the MATLAB `val` matrix. We accept only a
single format-16 MAT file with a 24-byte offset and twelve unique canonical lead names, no skew and
one sample per frame. The MAT matrix must match the header's channels and length;
we never guess a transpose. An explicit positive ADC gain and physical unit are
required, even where a general WFDB parser might supply defaults. Baselines follow
WFDB's convention: an explicit baseline takes precedence; otherwise the ADC-zero
field supplies it. The calculation is performed in float64 before tensor conversion.

Supported units are mV, uV/µV/μV and V. Lowercase header aliases `mv`, `uv`
and `v` are accepted; `MV` (megavolts) is not treated as millivolts. Per-channel conversion uses a `(12, 1)`
calibration vector to broadcast over time. Format-16 missing sentinel `-32768`,
nonfinite values, fractional/out-of-range ADC counts, missing files and malformed
lead sets fail. This is intentionally narrower than general WFDB support.

[WFDB header specification](https://physionet.org/physiotools/wag/header-5.htm),
[WFDB Python API](https://wfdb.readthedocs.io/en/latest/wfdb.html), and
[SciPy MAT reader](https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.loadmat.html)
provide the underlying format and library references.

## Resampling and boundaries

The exact rational target/source ratio sets SciPy's `resample_poly` up/down factors.
The package uses `axis=1`, `window=('kaiser', 5.0)` and `padtype='line'`. Ratios with
numerator or denominator above 10,000 are rejected to keep this small teaching API
bounded. Equal rates return a copy. No further bandpass or notch filter is applied.

Processing the full recording before cropping gives the filter observed context on
both sides of an interior window. At the true recording edges, linear extension is
an assumption. The result has a ceiling-rounded sample count when the rational
conversion does not divide the input length exactly. Interpolation is not new
measured information. Memory cost scales with the complete native recording.

[SciPy's polyphase resampling documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html)
describes the algorithm and extension options.

## Windows, flags and failure

A start time and duration select a fixed window after resampling. The default
`short_policy='pad'` appends zero mV on the right, with a false time mask there;
`'reject'` instead raises. The mask distinguishes supported recording duration
from appended padding, not good versus bad clinical signal. Resampled values are
derived from observed samples, and may include the filter's edge assumption.

Each retained exactly constant channel produces a `constant_lead:<name>` flag.
This flags an engineering observation without inventing a clinical rejection
threshold. Nothing is automatically repaired or silently dropped. Float32 overflow
fails rather than delivering infinite tensors. Missing leads are never synthesised.

The collator checks finite CPU float32 signals, consistent lengths/rates/units and
canonical lead order, and a correctly shaped boolean mask. It preserves example
order and identifiers. A subsequent algorithm would have to handle masks
explicitly; merely carrying a mask does not make a model padding-invariant.

## Validation is limited

The tests compare all bundled waveforms with WFDB's physical decoder. The two
readers still depend on the same acquisition metadata. Checksums verify byte
identity, not physiological truth. These tutorials do not validate clinical
annotations, lead placement, all forms of noise or use in patient care.
