"""Small, explicit signal operations for the bundled Challenge MAT recordings.

The module reads local files only. Header parsing is delegated to WFDB, MAT
container decoding to SciPy, and sample-rate conversion to SciPy's polyphase FIR.
Diagnosis/demographic comments are never used as signal-processing inputs.
"""

from dataclasses import dataclass, replace
from fractions import Fraction
import math
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from scipy.signal import resample_poly
import torch
from torch.utils.data import Dataset
import wfdb


CANONICAL_LEADS = (
    "I", "II", "III", "aVR", "aVL", "aVF",
    "V1", "V2", "V3", "V4", "V5", "V6",
)


@dataclass(frozen=True)
class NativeECG:
    record_id: str
    digital: np.ndarray
    millivolts: np.ndarray
    sample_rate_hz: float
    lead_names: tuple[str, ...]
    gain: np.ndarray
    baseline: np.ndarray
    units: tuple[str, ...]


@dataclass(frozen=True)
class ECGWindow:
    waveform: torch.Tensor
    valid_time_mask: torch.Tensor
    record_id: str
    sample_rate_hz: float
    start_seconds: float
    flags: tuple[str, ...]
    lead_names: tuple[str, ...] = CANONICAL_LEADS
    units: str = "mV"


def _rate(value):
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Sampling rate must be finite and positive")
    return float(value)


def _signal_array(signal):
    values = np.asarray(signal, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] != 12 or values.shape[1] < 2:
        raise ValueError("Expected twelve channels and at least two samples")
    if not np.isfinite(values).all():
        raise ValueError("Signal contains NaN or infinity")
    return values


def canonical_indices(lead_names):
    """Accept case differences only; never invent missing leads or guess aliases."""
    names = [name.upper() for name in lead_names]
    expected = [name.upper() for name in CANONICAL_LEADS]
    if len(names) != 12 or len(set(names)) != 12 or set(names) != set(expected):
        raise ValueError("Twelve unique canonical ECG leads are required")
    return [names.index(name) for name in expected]


def calibrate(digital, gain, baseline, units):
    """Convert each channel's ADC counts to mV using its stated calibration.

    physical_mV = (digital - baseline) / gain * unit_to_mV.
    Gain is ADC units per stated physical unit; baseline is not a fitted mean.
    """
    digital = _signal_array(digital)
    gain = np.asarray(gain, dtype=np.float64)
    baseline = np.asarray(baseline, dtype=np.float64)
    if gain.shape != (12,) or baseline.shape != (12,) or len(units) != 12:
        raise ValueError("One calibration value is required per channel")
    if not np.isfinite(gain).all() or (gain <= 0).any():
        raise ValueError("ADC gains must be finite and strictly positive")
    if not np.isfinite(baseline).all():
        raise ValueError("ADC baselines must be finite")
    unit_scale = {
        "mV": 1.0, "mv": 1.0, "uV": 0.001, "uv": 0.001,
        "V": 1000.0, "v": 1000.0,
    }
    if any(not isinstance(unit, str) for unit in units):
        raise ValueError("Explicit physical unit strings are required")
    names = [unit.replace("µ", "u").replace("μ", "u") for unit in units]
    if any(unit not in unit_scale for unit in names):
        raise ValueError("Supported physical units are mV, uV and V")
    scale = np.array([unit_scale[unit] for unit in names])
    shifted = digital - baseline[:, None]
    physical = shifted / gain[:, None]
    return _signal_array(physical * scale[:, None])


def read_native(header_path):
    """Read one local, single-file format-16 Challenge MAT record in native order.

    No remote WFDB directory is accepted. No comments, targets or demographic
    fields are returned. The deliberately narrow format support is explicit.
    """
    header_path = Path(header_path)
    if header_path.suffix != ".hea" or not header_path.is_file():
        raise ValueError("An existing local .hea file is required")
    lines = header_path.read_text(encoding="utf-8").splitlines()
    header = wfdb.rdheader(str(header_path.with_suffix("")))
    if not isinstance(header, wfdb.Record) or header.n_sig != 12:
        raise ValueError("Only single-segment twelve-lead records are supported")
    canonical_indices(header.sig_name)
    _rate(header.fs)
    if (
        header.fmt != ["16"] * 12
        or any(value not in (None, 1) for value in header.samps_per_frame)
        or any(value not in (None, 0) for value in header.skew)
        or header.byte_offset != [24] * 12
        or len(set(header.file_name)) != 1
    ):
        raise ValueError("Only one format-16 MAT file without skew is supported")
    # WFDB supplies defaults for some missing calibration fields. Teaching this
    # conversion requires explicit gain and units instead of those defaults.
    for line in lines[1:13]:
        fields = line.split()
        if len(fields) < 3 or "/" not in fields[2]:
            raise ValueError("Explicit ADC gain and physical units are required")
        gain_text = fields[2].split("/", 1)[0].split("(", 1)[0]
        if not gain_text or not math.isfinite(float(gain_text)) or float(gain_text) <= 0:
            raise ValueError("An explicit positive ADC gain is required")
    filename = header.file_name[0]
    if Path(filename).name != filename or not filename.endswith(".mat"):
        raise ValueError("Expected a MAT filename in the same directory as the header")
    signal_path = header_path.parent / filename
    if not signal_path.is_file():
        raise ValueError("The declared MAT signal file is missing")
    contents = loadmat(signal_path, variable_names=["val"])
    if "val" not in contents:
        raise ValueError("The MAT file has no val signal matrix")
    digital = np.asarray(contents["val"])
    if digital.shape != (12, header.sig_len):
        raise ValueError("MAT signal shape disagrees with the header")
    values = _signal_array(digital)
    if (
        not np.equal(values, np.rint(values)).all()
        or (values < -32768).any()
        or (values > 32767).any()
        or (values == -32768).any()
    ):
        raise ValueError("Invalid format-16 ADC counts or missing-sample sentinel")
    gain = np.asarray(header.adc_gain, dtype=np.float64)
    baseline = np.asarray(header.baseline, dtype=np.float64)
    units = tuple(header.units)
    millivolts = calibrate(values, gain, baseline, units)
    return NativeECG(
        header_path.stem, digital.copy(), millivolts, float(header.fs),
        tuple(header.sig_name), gain, baseline, units,
    )


def reorder_leads(signal, lead_names):
    """Return channels in canonical order, without changing their voltage values."""
    return _signal_array(signal)[canonical_indices(lead_names), :].copy()


def resample_signal(signal, source_hz, target_hz):
    """Resample the complete recording, before windowing, with a polyphase FIR.

    Linear extension models the two recording boundaries. The Kaiser-window
    parameter is fixed at 5.0; no additional notch/bandpass filter is applied.
    Very large rational factors are outside this small educational API.
    """
    values = _signal_array(signal)
    source_hz = _rate(source_hz)
    target_hz = _rate(target_hz)
    ratio = Fraction(str(target_hz)) / Fraction(str(source_hz))
    if max(ratio.numerator, ratio.denominator) > 10000:
        raise ValueError("Resampling ratio is too large for this educational API")
    if ratio == 1:
        return values.copy()
    result = resample_poly(
        values, ratio.numerator, ratio.denominator, axis=1,
        window=("kaiser", 5.0), padtype="line",
    )
    return _signal_array(result)


def _grid_index(seconds, rate):
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Times must be finite and nonnegative")
    exact = seconds * rate
    rounded = round(exact)
    if not math.isclose(exact, rounded, rel_tol=0, abs_tol=1e-7):
        raise ValueError("Time must align with the requested sampling grid")
    return rounded


def make_window(
    millivolts, sample_rate_hz, duration_seconds=10.0, start_seconds=0.0,
    short_policy="pad", record_id="synthetic",
):
    """Window canonical voltages and explicitly mark any right-padded samples.

    Exact constant channels are flagged, not silently fixed or clinically judged.
    No lead is reconstructed, no amplitude is clipped, and no mean is subtracted.
    """
    values = _signal_array(millivolts)
    rate = _rate(sample_rate_hz)
    size = _grid_index(duration_seconds, rate)
    start = _grid_index(start_seconds, rate)
    if size < 2 or start >= values.shape[1]:
        raise ValueError("Window must contain samples and start inside the recording")
    if short_policy not in ("pad", "reject"):
        raise ValueError("short_policy must be 'pad' or 'reject'")
    observed = values[:, start:start + size]
    available = observed.shape[1]
    if available < size and short_policy == "reject":
        raise ValueError("The requested window extends beyond the measured recording")
    output = np.zeros((12, size), dtype=np.float32)
    with np.errstate(over="ignore"):
        output[:, :available] = observed
    if not np.isfinite(output).all():
        raise ValueError("Signal cannot be represented as finite float32")
    flags = []
    if available < size:
        flags.append("right_zero_padded")
    if start > 0 or start + size < values.shape[1]:
        flags.append("window_selected")
    for index in np.flatnonzero(np.ptp(observed, axis=1) == 0):
        flags.append(f"constant_lead:{CANONICAL_LEADS[index]}")
    return ECGWindow(
        torch.from_numpy(output), torch.arange(size) < available,
        record_id, rate, float(start_seconds), tuple(flags),
    )


def prepare_ecg(
    native, sample_rate_hz=500, duration_seconds=10.0, start_seconds=0.0,
    short_policy="pad",
):
    """Compose the same public stages used individually in the notebooks."""
    ordered = reorder_leads(native.millivolts, native.lead_names)
    resampled = resample_signal(ordered, native.sample_rate_hz, sample_rate_hz)
    window = make_window(
        resampled, sample_rate_hz, duration_seconds, start_seconds,
        short_policy, native.record_id,
    )
    flags = list(window.flags)
    if native.sample_rate_hz != sample_rate_hz:
        flags.append("resampled")
    if native.lead_names != CANONICAL_LEADS:
        flags.append("leads_reordered")
    return replace(window, flags=tuple(flags))


def collate_windows(windows):
    """Stack compatible windows while preserving identities and observed-time masks."""
    if not windows:
        raise ValueError("Cannot form an empty batch")
    first = windows[0]
    for window in windows:
        if (
            window.waveform.shape != first.waveform.shape
            or window.waveform.ndim != 2
            or window.waveform.shape[0] != 12
            or window.waveform.dtype != torch.float32
            or window.waveform.device.type != "cpu"
            or not torch.isfinite(window.waveform).all()
            or window.valid_time_mask.shape != (window.waveform.shape[1],)
            or window.valid_time_mask.dtype != torch.bool
            or window.lead_names != CANONICAL_LEADS
            or window.units != "mV"
            or window.sample_rate_hz != first.sample_rate_hz
        ):
            raise ValueError("Windows disagree in shape, rate, units, leads or validity")
    return {
        "waveform": torch.stack([window.waveform for window in windows]),
        "valid_time_mask": torch.stack([window.valid_time_mask for window in windows]),
        "record_ids": [window.record_id for window in windows],
        "flags": [window.flags for window in windows],
        "sample_rate_hz": first.sample_rate_hz,
        "lead_names": CANONICAL_LEADS,
        "units": "mV",
    }


class WaveformDataset(Dataset):
    """Local sample references only; indexing decodes, prepares and returns one ECG."""

    def __init__(self, records, sample_rate_hz=500, duration_seconds=10.0):
        self.records = tuple(records)
        self.sample_rate_hz = sample_rate_hz
        self.duration_seconds = duration_seconds

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        native = read_native(self.records[index].header_path)
        return prepare_ecg(native, self.sample_rate_hz, self.duration_seconds)
