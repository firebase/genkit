# Overview

The Genkit Python AI SDK publishes some packages to PYPI in order to be able to
use them as python packages using any python package manager.

In order to generate a new version of any package or plugin, a CI with github
actions has been created.

## CI to release new PYPI versions

The github action located on `.github/workflows/publish_python.yml` has two
inputs:

* Type of project to build. E.g. Package or Plugin
* Name of project. E.g. genkit

The process is separated in two steps. The first one make validations over the
project to build. Mainly, the project's new version to publish must be greater
that the current one. This step also builds with uv the package and validates
the wheel with twine.

The last step uses an action `pypa/gh-action-pypi-publish@release/v1` to publish
the package with trusted publishers. See
(gh-action-pypi-publish)\[https://github.com/pypa/gh-action-pypi-publish]
