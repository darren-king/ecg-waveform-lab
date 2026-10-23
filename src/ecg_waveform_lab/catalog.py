"""Portable references and integrity checks for the bundled public sample."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class SampleRecord:
    record_id: str
    cohort: str
    header_path: Path
    signal_path: Path
    sample_rate_hz: float
    duration_seconds: float
    selection_reason: str


def project_root(start=None):
    """Find the source checkout from its root or a notebook subdirectory."""
    current = Path.cwd() if start is None else Path(start)
    current = current.resolve()
    for candidate in (current, *current.parents):
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "data/sample_manifest.json").is_file()
        ):
            return candidate
    raise FileNotFoundError("Start inside the ecg-waveform-lab source checkout")


def _local_path(data_root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Sample paths must be relative to the data directory")
    resolved = (data_root / path).resolve()
    if not resolved.is_relative_to(data_root.resolve()):
        raise ValueError("Sample path escapes the data directory")
    return resolved


def load_catalog(root=None):
    root = project_root() if root is None else Path(root)
    data_root = root / "data"
    manifest = json.loads((data_root / "sample_manifest.json").read_text())
    return [
        SampleRecord(
            item["record_id"], item["cohort"],
            _local_path(data_root, item["header_path"]),
            _local_path(data_root, item["signal_path"]),
            item["sample_rate_hz"], item["duration_seconds"],
            item["selection_reason"],
        )
        for item in manifest["records"]
    ]


def sha256_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_sample(root=None):
    """Verify local files against the retained official checksum excerpt.

    This offline check detects local changes. Acquisition separately authenticated
    the complete official checksum list against its pinned SHA-256 over HTTPS.
    """
    root = project_root() if root is None else Path(root)
    data_root = root / "data"
    manifest = json.loads((data_root / "sample_manifest.json").read_text())
    published = {}
    for line in (data_root / "SHA256SUMS.selected.txt").read_text().splitlines():
        digest, relative = line.split(maxsplit=1)
        published[relative] = digest
    expected_names = {"LICENSE.txt"}
    checked = 0
    for item in manifest["records"]:
        for kind in ("header", "signal"):
            original = item[f"original_{kind}_path"]
            expected_names.add(original)
            path = _local_path(data_root, item[f"{kind}_path"])
            expected = item[f"{kind}_sha256"]
            if published.get(original) != expected or sha256_file(path) != expected:
                raise ValueError("Bundled sample checksum mismatch")
            if path.stat().st_size != item[f"{kind}_bytes"]:
                raise ValueError("Bundled sample byte size mismatch")
            checked += 1
    licence = data_root / "LICENSE-CC-BY-4.0.txt"
    if (
        sha256_file(licence) != manifest["license_sha256"]
        or published["LICENSE.txt"] != manifest["license_sha256"]
        or set(published) != expected_names
    ):
        raise ValueError("Licence or published checksum excerpt mismatch")
    return {"recordings": len(manifest["records"]), "native_files_verified": checked}
