# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import nox

# Define the Python versions you want to test against
PYTHON_VERSIONS = ['3.10', '3.11', '3.12', '3.13']

# Set default backend to uv if available, otherwise virtualenv
nox.options.default_venv_backend = 'uv|virtualenv'
# Define default sessions to run when 'nox' is called without arguments
nox.options.sessions = ['tests', 'lint']


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session):
    """Run the test suite across specified Python versions."""
    session.log(f'Running tests on Python {session.python}')

    # Install all workspace packages in editable mode along with dev dependencies
    # Assumes nox is run from the 'py' directory.
    session.run_always(
        'uv',
        'pip',
        'install',
        # Explicitly install testing tools
        'pytest',
        'pytest-cov',
        'pytest-asyncio',
        'pytest-mock',
        # Install workspace packages in editable mode
        '-e',
        '.',
        external=True,  # Indicate uv is an external command
    )

    # Verify installed packages (for debugging)
    session.log('Listing installed packages...')
    session.run('uv', 'pip', 'list', external=True)

    # Run pytest with coverage
    # Rely on addopts in pyproject.toml for --cov
    # Paths are relative to the 'py' directory where nox is run.
    session.run(
        'pytest',
        # Removed explicit --cov args, rely on pyproject.toml addopts = ["--cov"]
        # Removed --cov-config, coverage settings are in the default pyproject.toml
        # Removed '--cov-report=term-missing', rely on pyproject.toml
        'packages',  # Specify path for pytest test discovery
        'plugins',  # Specify path for pytest test discovery
        'samples',  # Specify path for pytest test discovery
        *session.posargs,  # Pass any positional arguments from nox command line
        external=True,  # Indicate pytest is an external command
    )


@nox.session
def lint(session: nox.Session):
    """Run linters."""
    session.log('Running linters')
    # Assumes nox is run from the 'py' directory.
    session.run_always(
        'uv',
        'pip',
        'install',
        # Explicitly install linting tools
        'ruff',
        # Install workspace packages in editable mode
        '-e',
        '.',
        external=True,
        silent=True,
    )

    session.log('Running ruff format check')
    session.run('ruff', 'format', '--check', '.', external=True)  # Target current dir (py)
    session.log('Running ruff checks')
    session.run('ruff', 'check', '.', external=True)  # Target current dir (py)
    # session.log("Running mypy checks") # mypy has many errors currently
    # session.run("mypy", external=True)


@nox.session
def codegen(session: nox.Session):
    """Generate code artifacts (e.g., typing.py)."""
    session.log('Running code generation')
    # Assumes nox is run from the 'py' directory.
    session.run_always(
        'uv',
        'pip',
        'install',
        '-e',
        '.[dev]',  # Need datamodel-code-generator from dev deps
        external=True,
        silent=True,
    )
    # Run script relative to current dir (py)
    session.run('bash', './bin/generate_schema_typing', external=True)


@nox.session
def codegen_check(session: nox.Session):
    """Check if generated code is up-to-date (for CI)."""
    session.log('Checking generated code')
    # Assumes nox is run from the 'py' directory.
    session.run_always(
        'uv',
        'pip',
        'install',
        '-e',
        '.[dev]',
        external=True,
        silent=True,
    )
    # Run script relative to current dir (py)
    session.run('bash', './bin/generate_schema_typing', '--ci', external=True)
