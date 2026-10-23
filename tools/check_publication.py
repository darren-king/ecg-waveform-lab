"""Read-only review of the files intended for this small public repository."""

import ast
import json
from pathlib import Path
import re

from ecg_waveform_lab import verify_sample


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", ".cache", "outputs", "__pycache__", ".ipynb_checkpoints"}
LOCAL_PATH = re.compile(r"/(?:Users|private|home)/|(?:^|[\s\"'(=])[A-Za-z]:\\")
SECRET = re.compile(
    r"AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)
PRIVATE_NAMES = (
    "mi" + "mic", "Experiment" + "_001", "clinical" + "_targets",
    "unified" + "_split_manifest", "phase1" + "_clinical_review",
)


def candidate_files(directory=ROOT):
    for path in sorted(directory.iterdir()):
        if path.name in EXCLUDED:
            continue
        if path.is_symlink():
            raise ValueError("Publication candidates must not contain symlinks")
        if path.is_dir():
            yield from candidate_files(path)
        else:
            yield path


def main():
    failures = []
    total_bytes = 0
    files = list(candidate_files())
    manifest = json.loads((ROOT / "data/sample_manifest.json").read_text())
    native_paths = {
        "data/" + record[field]
        for record in manifest["records"]
        for field in ("header_path", "signal_path")
    }
    actual_native = {
        str(path.relative_to(ROOT))
        for path in files if path.is_relative_to(ROOT / "data/sample")
    }
    if native_paths != actual_native:
        failures.append("Bundled files differ from the public sample manifest")
    for path in files:
        relative = str(path.relative_to(ROOT))
        payload = path.read_bytes()
        total_bytes += len(payload)
        if len(payload) > 16 * 1024**2:
            failures.append(f"File exceeds 16 MiB: {relative}")
        if relative in native_paths and path.suffix == ".mat":
            continue  # Its exact public-release hash is checked below.
        try:
            source = payload.decode("utf-8")
        except UnicodeDecodeError:
            failures.append(f"Unexpected binary: {relative}")
            continue
        if LOCAL_PATH.search(source) or SECRET.search(source):
            failures.append(f"Local path or credential-like text: {relative}")
        if any(name.lower() in source.lower() for name in PRIVATE_NAMES):
            failures.append(f"Private research reference: {relative}")
        if path.name.startswith(".env"):
            failures.append(f"Environment secret file: {relative}")
        if path.suffix == ".py":
            ast.parse(source, filename=relative)
        if path.suffix == ".ipynb":
            notebook = json.loads(source)
            for cell in notebook["cells"]:
                if cell["cell_type"] == "code":
                    ast.parse("".join(cell["source"]), filename=relative)
                    if cell.get("outputs") or cell.get("execution_count") is not None:
                        failures.append(f"Notebook source outputs not cleared: {relative}")
    if total_bytes > 30 * 1024**2:
        failures.append("Candidate repository exceeds 30 MiB")
    result = verify_sample(ROOT)
    result.update(candidate_files=len(files), candidate_bytes=total_bytes)
    if failures:
        raise SystemExit("\n".join(failures))
    print(json.dumps(result, indent=2))
    print("Publication checks passed; manual review is still required before publishing.")


if __name__ == "__main__":
    main()
