# Development and publication notes

This package and its notebook prose were written for this standalone educational
repository. The implementation uses documented public NumPy, SciPy, WFDB and
PyTorch APIs; no internal production module, classifier, research target policy or
Git history was copied. Earlier tutorials informed the learning objectives, not a
requirement to reuse their implementation. Third-party libraries are dependencies,
not vendored source.

## Contribution checks

1. Work in the declared environment: `uv sync --locked`.
2. Keep each notebook independently executable and explain operations before code.
3. Use the package for actual signal transformations. Label any illustrative math
   or synthetic perturbation clearly, and expose meaningful intermediate values.
4. Run `uv run --frozen python -m unittest discover -s tests -v`.
5. Run `uv run --frozen python tools/run_notebooks.py`; inspect its local plots.
6. Clear source notebook outputs before staging. Preserve all bundled native bytes.
7. Run `uv run --frozen python tools/check_publication.py` and review the Git diff.

The publication check is a bounded aid, not a guarantee that arbitrary future
content is safe. It verifies the public bundle, rejects unexpected binaries and
large files, checks text for local paths and common credential patterns, checks
notebook outputs, and excludes local environments/caches/executed copies from the
candidate file set. Manually review changes and licensing before publishing.

## Boundaries

Do not add private datasets, patient linkage tables, external research artifacts,
clinical targets or a training pipeline. Keep experimental teaching calculations
in memory. Invalid input should fail visibly, not be silently repaired or replaced.
Any change to resampling, boundary assumptions, units or padding must be explained
in the signal contract and tested with synthetic signals.

MIT covers original code and tutorial prose. CC BY 4.0 covers the bundled public
release data and carries through to data-derived plots. Keep source credit and
modification notices. Review that licensing choice and attribution before the
first public release; no remote or publication is configured by these files.
