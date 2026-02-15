# Overview

The Genkit Python AI SDK publishes packages to PyPI so they can be installed
with any Python package manager (`pip`, `uv`, etc.).

## Publishing with ReleaseKit (current)

The primary publishing mechanism is **ReleaseKit**, an internal release
orchestration tool. It automates the full release lifecycle:

* Version bumping across all packages (core + 22 plugins + samples)
* Changelog generation from conventional commits
* Dependency-graph-aware publish ordering with retries
* SBOM generation

The automated workflow is at `.github/workflows/releasekit-uv.yml`. See
[`py/tools/releasekit/README.md`](../../../tools/releasekit/README.md) for
full documentation.

## Legacy manual workflow

The older manual workflow at `.github/workflows/publish_python.yml` is still
available as a fallback. It accepts two inputs:

* Type of project to build (Package or Plugin)
* Name of project (e.g. `genkit`)

It validates that the new version is greater than the current PyPI version,
builds with `uv`, validates the wheel with `twine`, and publishes using
`pypa/gh-action-pypi-publish@release/v1` with trusted publishers.
