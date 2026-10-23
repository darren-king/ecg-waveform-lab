"""Small synthetic tests plus an offline check of every bundled public example."""

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy.io import savemat
import torch
from torch.utils.data import DataLoader
import wfdb

from ecg_waveform_lab import (
    CANONICAL_LEADS, WaveformDataset, calibrate, collate_windows, load_catalog,
    make_window, prepare_ecg, read_native, reorder_leads, resample_signal,
    verify_sample,
)


ROOT = Path(__file__).resolve().parents[1]


def synthetic_file(directory, lead_order=CANONICAL_LEADS, units="mV"):
    """Known ADC values in a temporary MAT v4 file, with explicit calibration."""
    rate = 1000
    time = np.arange(12000) / rate
    gains = np.arange(12) * 20 + 800
    baselines = np.arange(12) * 3 + 32
    voltage = np.empty((12, time.size))
    for channel in range(12):
        voltage[channel] = 0.3 * np.sin(2 * np.pi * 3 * time + channel / 12)
    digital = np.rint(voltage * gains[:, None] + baselines[:, None]).astype(np.int16)
    order = [CANONICAL_LEADS.index(lead) for lead in lead_order]
    reordered = digital[order]
    signal_path = directory / "fixture.mat"
    header_path = directory / "fixture.hea"
    savemat(signal_path, {"val": reordered}, format="4")
    lines = [f"fixture 12 {rate} {time.size}"]
    for channel, original in enumerate(order):
        gain = gains[original]
        if units == "uV":
            gain = gain / 1000
        checksum = int(reordered[channel].astype(np.int64).sum()) % 65536
        lines.append(
            f"fixture.mat 16+24 {gain}({baselines[original]})/{units} "
            f"16 0 {reordered[channel, 0]} {checksum} 0 {lead_order[channel]}"
        )
    header_path.write_text("\n".join(lines) + "\n")
    expected = (digital.astype(float) - baselines[:, None]) / gains[:, None]
    return header_path, digital, expected


class SignalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.header, self.digital, self.expected = synthetic_file(self.directory)

    def test_decode_shape_calibration_and_wfdb_reference(self):
        native = read_native(self.header)
        np.testing.assert_array_equal(native.digital, self.digital)
        self.assertEqual(native.millivolts.shape, (12, 12000))
        self.assertEqual(native.sample_rate_hz, 1000)
        np.testing.assert_allclose(native.millivolts, self.expected, atol=1e-12)
        reference = wfdb.rdrecord(str(self.header.with_suffix(""))).p_signal.T
        np.testing.assert_allclose(native.millivolts, reference, atol=1e-12)

    def test_microvolt_conversion_uses_each_channels_gain(self):
        header, _, expected = synthetic_file(self.directory, units="uV")
        np.testing.assert_allclose(read_native(header).millivolts, expected, atol=1e-12)

    def test_canonical_order_restores_a_permutation(self):
        order = tuple(reversed(CANONICAL_LEADS))
        header, _, expected = synthetic_file(self.directory, lead_order=order)
        native = read_native(header)
        actual = reorder_leads(native.millivolts, native.lead_names)
        np.testing.assert_allclose(actual, expected, atol=1e-12)
        prepared = prepare_ecg(native)
        self.assertIn("leads_reordered", prepared.flags)

    def test_missing_duplicate_and_unknown_leads_are_not_reconstructed(self):
        for names in (
            CANONICAL_LEADS[:-1],
            ("II",) + CANONICAL_LEADS[1:],
            ("other",) + CANONICAL_LEADS[1:],
        ):
            with self.assertRaises(ValueError):
                reorder_leads(self.expected, names)

    def test_calibration_rejects_bad_gain_units_and_shape(self):
        gain = np.ones(12) * 1000
        baseline = np.zeros(12)
        for bad_gain in (np.zeros(12), np.full(12, np.nan), np.ones(11)):
            with self.assertRaises(ValueError):
                calibrate(self.digital, bad_gain, baseline, ["mV"] * 12)
        for bad_unit in ("unknown", "MV", None):
            with self.assertRaises(ValueError):
                calibrate(self.digital, gain, baseline, [bad_unit] * 12)
        with self.assertRaises(ValueError):
            calibrate(self.digital, gain, np.full(12, np.inf), ["mV"] * 12)

    def test_missing_signal_file_fails(self):
        (self.directory / "fixture.mat").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            read_native(self.header)

    def test_invalid_or_missing_signal_values_fail(self):
        for value in (np.nan, np.inf, -32768, 40000, 0.25):
            signal = self.digital.astype(float)
            signal[0, 0] = value
            savemat(self.directory / "fixture.mat", {"val": signal}, format="4")
            with self.assertRaises(ValueError):
                read_native(self.header)
        savemat(self.directory / "fixture.mat", {"different": self.digital}, format="4")
        with self.assertRaisesRegex(ValueError, "no val"):
            read_native(self.header)

    def test_header_shape_and_implicit_gain_are_not_silently_repaired(self):
        original = self.header.read_text()
        self.header.write_text(original.replace("1000 12000", "1000 12001"))
        with self.assertRaisesRegex(ValueError, "shape"):
            read_native(self.header)
        self.header.write_text(original.replace("800(32)/mV", "0(32)/mV"))
        with self.assertRaisesRegex(ValueError, "gain"):
            read_native(self.header)

    def test_polyphase_filter_suppresses_a_component_above_new_nyquist(self):
        time = np.arange(3000) / 1000
        low = np.sin(2 * np.pi * 25 * time)
        high = np.sin(2 * np.pi * 350 * time)
        signal = np.tile(low + high, (12, 1))
        filtered = resample_signal(signal, 1000, 500)
        desired = low[::2]
        interior = slice(100, -100)
        filtered_error = np.sqrt(np.mean((filtered[0, interior] - desired[interior])**2))
        naive_error = np.sqrt(np.mean((signal[0, ::2] - desired)**2))
        self.assertLess(filtered_error, 0.01)
        self.assertGreater(naive_error, 0.5)

    def test_rational_resampling_and_identity_rate(self):
        time = np.arange(771) / 257
        signal = np.tile(np.sin(2 * np.pi * 5 * time), (12, 1))
        actual = resample_signal(signal, 257, 500)
        self.assertEqual(actual.shape, (12, 1500))
        expected = np.sin(2 * np.pi * 5 * np.arange(1500) / 500)
        np.testing.assert_allclose(actual[0, 100:-100], expected[100:-100], atol=0.003)
        identity = resample_signal(signal, 257, 257)
        np.testing.assert_array_equal(identity, signal)
        self.assertFalse(np.shares_memory(identity, signal))

    def test_ten_second_window_and_nonzero_start(self):
        native = read_native(self.header)
        prepared = prepare_ecg(native)
        self.assertEqual(tuple(prepared.waveform.shape), (12, 5000))
        self.assertEqual(prepared.waveform.dtype, torch.float32)
        self.assertTrue(prepared.valid_time_mask.all())
        resampled = resample_signal(native.millivolts, 1000, 500)
        shifted = make_window(resampled, 500, duration_seconds=2, start_seconds=1)
        np.testing.assert_allclose(shifted.waveform.numpy(), resampled[:, 500:1500], atol=1e-7)

    def test_short_window_padding_and_rejection(self):
        signal = np.tile(np.arange(3000, dtype=float), (12, 1))
        window = make_window(signal, 500)
        self.assertEqual(window.valid_time_mask.sum().item(), 3000)
        self.assertTrue((window.waveform[:, 3000:] == 0).all())
        self.assertFalse(window.valid_time_mask[3000:].any())
        with self.assertRaises(ValueError):
            make_window(signal, 500, short_policy="reject")

    def test_invalid_time_grid_rates_nonfinite_and_float32_overflow(self):
        for rate in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                resample_signal(self.expected, rate, 500)
        for changes in (
            {"start_seconds": 0.0001}, {"duration_seconds": 0},
            {"start_seconds": 100}, {"short_policy": "guess"},
        ):
            with self.assertRaises(ValueError):
                make_window(self.expected, 500, **changes)
        for value in (float("nan"), float("inf"), 1e100):
            with self.assertRaises(ValueError):
                make_window(np.full((12, 6000), value), 500)

    def test_constant_lead_is_flagged_without_silent_repair(self):
        signal = self.expected.copy()
        signal[1] = 0
        window = make_window(signal, 1000)
        self.assertIn("constant_lead:II", window.flags)
        self.assertTrue((window.waveform[1] == 0).all())

    def test_batch_alignment_and_incompatible_units(self):
        first = prepare_ecg(read_native(self.header))
        second = replace(first, record_id="another", waveform=first.waveform + 1)
        batch = collate_windows([first, second])
        self.assertEqual(tuple(batch["waveform"].shape), (2, 12, 5000))
        self.assertEqual(tuple(batch["valid_time_mask"].shape), (2, 5000))
        self.assertEqual(batch["record_ids"], ["fixture", "another"])
        torch.testing.assert_close(batch["waveform"][1], second.waveform)
        for bad in (
            replace(second, units="V"), replace(second, sample_rate_hz=250),
            replace(second, waveform=second.waveform.double()),
            replace(second, valid_time_mask=second.valid_time_mask.float()),
        ):
            with self.assertRaises(ValueError):
                collate_windows([first, bad])
        with self.assertRaises(ValueError):
            collate_windows([])


class BundledSampleTests(unittest.TestCase):
    def test_all_native_files_match_the_official_checksum_excerpt(self):
        self.assertEqual(verify_sample(ROOT), {
            "recordings": 12, "native_files_verified": 24,
        })

    def test_every_bundled_record_decodes_and_matches_wfdb_physical_values(self):
        for record in load_catalog(ROOT):
            with self.subTest(record=record.record_id):
                native = read_native(record.header_path)
                self.assertEqual(native.sample_rate_hz, record.sample_rate_hz)
                reference = wfdb.rdrecord(str(record.header_path.with_suffix("")))
                np.testing.assert_allclose(native.millivolts, reference.p_signal.T, atol=1e-10)
                self.assertEqual(tuple(prepare_ecg(native).waveform.shape), (12, 5000))

    def test_public_dataset_and_dataloader(self):
        records = load_catalog(ROOT)[:3]
        loader = DataLoader(
            WaveformDataset(records), batch_size=3, num_workers=0,
            shuffle=False, collate_fn=collate_windows,
        )
        batch = next(iter(loader))
        self.assertEqual(tuple(batch["waveform"].shape), (3, 12, 5000))
        self.assertEqual(batch["record_ids"], [record.record_id for record in records])
        self.assertTrue(torch.isfinite(batch["waveform"]).all())


if __name__ == "__main__":
    unittest.main()
