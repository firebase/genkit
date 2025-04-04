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
    session.run(
        'uv',
        'run',
        '--active',
        'pytest',
        # '-v', # Adding verbosity drops coverage for some reason...
        '.',
        'packages',
        'plugins',
        'samples',
        *session.posargs,  # Pass any positional arguments from nox command line.
        external=True,  # pytest is an external command.
    )


@nox.session
def lint(session: nox.Session):
    """Run linters."""
    session.log('Running linters')
    session.log('Running ruff format check')
    session.run('uv', 'run', 'ruff', 'format', '--check', '.', external=True)
    session.log('Running ruff checks')
    session.run('uv', 'run', 'ruff', 'check', '--preview', '--unsafe-fixes', '--fix', '.', external=True)
    # session.log("Running mypy checks") # mypy has many errors currently
    # session.run("mypy", external=True)


@nox.session
def codegen(session: nox.Session):
    """Generate code artifacts (e.g., typing.py)."""
    session.log('Running code generation')
    session.run_always(
        'uv',
        'pip',
        'install',
        '-e',
        '.[dev]',  # Need datamodel-code-generator from dev deps.
        external=True,
        silent=True,
    )
    session.run('bash', './bin/generate_schema_typing', external=True)


@nox.session
def codegen_check(session: nox.Session):
    """Check if generated code is up-to-date (for CI)."""
    session.log('Checking generated code')
    session.run_always(
        'uv',
        'pip',
        'install',
        '-e',
        '.[dev]',
        external=True,
        silent=True,
    )
    session.run('bash', './bin/generate_schema_typing', '--ci', external=True)
