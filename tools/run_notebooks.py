"""Execute each tutorial in a fresh kernel from this interpreter's environment.

Sources are never overwritten. Outputs and optional plot previews stay ignored.
The temporary kernelspec is local to this run, not installed in the user's account.
"""

import base64
import json
import os
from pathlib import Path
import sys
import tempfile

from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]


def main():
    (ROOT / ".cache").mkdir(exist_ok=True)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
    os.environ["IPYTHONDIR"] = str(ROOT / ".cache/ipython")
    os.environ["JUPYTER_RUNTIME_DIR"] = str(ROOT / ".cache/jupyter")
    (ROOT / "outputs").mkdir(exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="notebooks-", dir=ROOT / "outputs"))
    print("Executed copies:", destination.relative_to(ROOT), flush=True)
    results = []
    with tempfile.TemporaryDirectory(prefix="ecg-lab-kernel-") as directory:
        kernels = Path(directory)
        kernel = kernels / "ecg-waveform-lab"
        kernel.mkdir()
        (kernel / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "ECG Waveform Lab (current environment)",
            "language": "python",
        }))
        for source in sorted((ROOT / "notebooks").glob("*.ipynb")):
            notebook = nbformat.read(source, as_version=4)
            nbformat.validate(notebook)
            manager = KernelManager(
                kernel_name="ecg-waveform-lab",
                kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernels)]),
            )
            client = NotebookClient(
                notebook,
                km=manager,
                timeout=300,
                resources={"metadata": {"path": str(ROOT)}},
                allow_errors=False,
            )
            print("Executing", source.name, flush=True)
            try:
                client.execute()
            finally:
                if manager.has_kernel:
                    manager.shutdown_kernel(now=True)
            figures = 0
            for cell in notebook.cells:
                for output in cell.get("outputs", []):
                    png = output.get("data", {}).get("image/png")
                    if png:
                        figures += 1
                        name = f"{source.stem}-figure-{figures}.png"
                        (destination / name).write_bytes(base64.b64decode(png))
            nbformat.write(notebook, destination / source.name)
            result = {
                "notebook": source.name,
                "code_cells": sum(cell.cell_type == "code" for cell in notebook.cells),
                "figures": figures,
                "status": "pass",
            }
            results.append(result)
            print(json.dumps(result), flush=True)
    (destination / "summary.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
