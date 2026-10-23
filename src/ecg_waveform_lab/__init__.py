"""Educational ECG signal engineering; local public data, CPU tensors, no labels."""

from .catalog import load_catalog, project_root, verify_sample
from .signal import (
    CANONICAL_LEADS,
    ECGWindow,
    NativeECG,
    WaveformDataset,
    calibrate,
    canonical_indices,
    collate_windows,
    make_window,
    prepare_ecg,
    read_native,
    reorder_leads,
    resample_signal,
)

__all__ = [
    "CANONICAL_LEADS", "ECGWindow", "NativeECG", "WaveformDataset",
    "calibrate", "canonical_indices", "collate_windows", "load_catalog",
    "make_window", "prepare_ecg", "project_root", "read_native",
    "reorder_leads", "resample_signal", "verify_sample",
]
