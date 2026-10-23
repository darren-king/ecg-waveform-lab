"""Explicit maintainer-only download of a small, checksum-verified public sample.

Normal installation, tests and notebooks never call this network-enabled tool.
No existing destination file is overwritten. Only the pinned public release is used.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import random
import urllib.request


BASE_URL = "https://physionet.org/files/challenge-2021/1.0.3/"
CHECKSUM_SHA256 = "f29c2609343c38734f3a3d62be4a9052ca56a9e560e7ad2efc2118563fca2473"
SEED = 20261023
STRATA = [
    ("cpsc_2018", "short", 1, "Shorter than ten seconds: explicit right padding"),
    ("cpsc_2018", "long", 3, "Longer than ten seconds: choose a time window"),
    ("ptb", "any", 3, "1000 Hz: anti-aliased downsampling to 500 Hz"),
    ("ptb-xl", "any", 4, "500 Hz ten-second native decoding and batching"),
    ("st_petersburg_incart", "any", 1, "257 Hz: rational 500/257 resampling"),
]


def digest(content):
    return hashlib.sha256(content).hexdigest()


def fetch(relative, cache):
    """Cache only public release bytes; callers always verify hashes before use."""
    path = cache / relative
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(
        BASE_URL + relative, headers={"User-Agent": "ecg-waveform-lab/0.1"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def write_new_or_identical(path, payload):
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("Refusing to overwrite a different existing file")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def acquire(root):
    cache = root / ".cache/acquisition"
    checksums = fetch("SHA256SUMS.txt", cache)
    if digest(checksums) != CHECKSUM_SHA256:
        raise ValueError("Official checksum manifest differs from the pinned release")
    entries = {}
    original_lines = {}
    for line in checksums.decode("utf-8").splitlines(keepends=True):
        checksum, relative = line.split(maxsplit=1)
        relative = relative.strip()
        entries[relative] = checksum
        original_lines[relative] = line

    selected = []
    used = set()
    for cohort, kind, count, reason in STRATA:
        candidates = sorted(
            name for name in entries
            if name.startswith(f"training/{cohort}/") and name.endswith(".hea")
        )
        random.Random(f"{SEED}:{cohort}:{kind}").shuffle(candidates)
        chosen = 0
        inspected = 0
        for header_path in candidates:
            if header_path in used:
                continue
            header_bytes = fetch(header_path, cache)
            if digest(header_bytes) != entries[header_path]:
                raise ValueError("Official header checksum mismatch")
            lines = header_bytes.decode("utf-8").splitlines()
            fields = lines[0].split()
            channels, rate, samples = int(fields[1]), float(fields[2]), int(fields[3])
            duration = samples / rate
            inspected += 1
            eligible = channels == 12
            if kind == "short":
                eligible = eligible and 5 <= duration < 10
            elif kind == "long":
                eligible = eligible and 10 < duration <= 60
            if not eligible:
                continue
            filenames = {line.split()[0] for line in lines[1:channels + 1]}
            if len(filenames) != 1:
                raise ValueError("This sample expects one native MAT file per header")
            filename = filenames.pop()
            if PurePosixPath(filename).name != filename or not filename.endswith(".mat"):
                raise ValueError("Unexpected public waveform filename")
            signal_path = str(PurePosixPath(header_path).parent / filename)
            if signal_path not in entries:
                raise ValueError("Declared signal missing from published checksums")
            signal_bytes = fetch(signal_path, cache)
            if digest(signal_bytes) != entries[signal_path]:
                raise ValueError("Official waveform checksum mismatch")
            if len(signal_bytes) > 16 * 1024**2:
                raise ValueError("Selected native waveform exceeds the sample size cap")
            for relative, payload in (
                (header_path, header_bytes), (signal_path, signal_bytes)
            ):
                write_new_or_identical(root / "data/sample" / relative, payload)
            selected.append({
                "cohort": cohort,
                "record_id": PurePosixPath(header_path).stem,
                "original_header_path": header_path,
                "original_signal_path": signal_path,
                "header_path": "sample/" + header_path,
                "signal_path": "sample/" + signal_path,
                "header_sha256": entries[header_path],
                "signal_sha256": entries[signal_path],
                "header_bytes": len(header_bytes),
                "signal_bytes": len(signal_bytes),
                "sample_rate_hz": rate,
                "samples_per_lead": samples,
                "duration_seconds": duration,
                "selection_reason": reason,
            })
            used.add(header_path)
            chosen += 1
            if chosen == count:
                break
        if chosen != count:
            raise ValueError("Not enough records meeting a documented sample stratum")
        print(f"Selected {chosen} {cohort} / {kind}; inspected {inspected} headers", flush=True)

    licence = fetch("LICENSE.txt", cache)
    if digest(licence) != entries["LICENSE.txt"]:
        raise ValueError("Published licence checksum mismatch")
    write_new_or_identical(root / "data/LICENSE-CC-BY-4.0.txt", licence)
    manifest = {
        "release": "PhysioNet/CinC Challenge 2021 v1.0.3",
        "release_url": "https://physionet.org/content/challenge-2021/1.0.3/",
        "download_base_url": BASE_URL,
        "license": "CC-BY-4.0",
        "seed": SEED,
        "selection_algorithm": "Python 3.12 Random(str(seed)+':'+cohort+':'+kind), shuffle sorted official header paths; first qualifying records per stratum",
        "checksum_manifest_url": BASE_URL + "SHA256SUMS.txt",
        "checksum_manifest_sha256": CHECKSUM_SHA256,
        "license_sha256": entries["LICENSE.txt"],
        "modifications": "None: headers and MAT files are byte-for-byte release files",
        "records": selected,
    }
    write_new_or_identical(
        root / "data/sample_manifest.json",
        (json.dumps(manifest, indent=2) + "\n").encode(),
    )
    included = {"LICENSE.txt"}
    for record in selected:
        included.update((record["original_header_path"], record["original_signal_path"]))
    excerpt = "".join(original_lines[name] for name in sorted(included))
    write_new_or_identical(root / "data/SHA256SUMS.selected.txt", excerpt.encode())
    total = sum(item["header_bytes"] + item["signal_bytes"] for item in selected)
    print(f"Verified {len(selected)} public recordings; {total:,} native-file bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-public-sample", action="store_true", required=True)
    arguments = parser.parse_args()
    acquire(Path(__file__).resolve().parents[1])
