# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Server infrastruture.

This module exposes functionality used by the Genkit application veneer
to start multiple servers, viz.:

- Reflection API server.
- Flows server.

Each of these servers runs in its own thread with its own event loop.

The reflection API server is started only in dev mode, which is enabled by the
setting the environment variable `GENKIT_ENV` to `dev`. By default,
the reflection API server binds and listens on (localhost, 3100).

The flows server is the production servers that exposes flows and
actions over HTTP.

"""

import atexit
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI


@dataclass
class ServerSpec:
    """ServerSpec encapsulates the scheme, host and port information for a
    server to bind to and listen on."""

    port: int
    scheme: str = 'http'
    host: str = 'localhost'

    @property
    def url(self) -> str:
        """URL evaluates to the host base URL given the server specs."""
        return f'{self.scheme}://{self.host}:{self.port}'


@dataclass
class AppSpec:
    """AppSpec encapsulates information about an application and associated host
    and port information for its server to listen on."""

    app: FastAPI
    server: ServerSpec


def run_app(app_spec: AppSpec) -> None:
    """Convenience wrapper to run an application server.

    Args:
        app_spec: The application server to start running.

    Returns:
        None.
    """
    uvicorn.run(
        app_spec.app, host=app_spec.server.host, port=app_spec.server.port
    )


def start_apps(app_specs: list[AppSpec]) -> None:
    """Starts a set of application servers using threading.

    Args:
        specs: A list of application server specs.

    Returns:
        None.
    """
    if not app_specs:
        raise ValueError('No servers to start.')

    threads = []

    for app_spec in app_specs:
        t = threading.Thread(target=run_app, args=(app_spec,))
        t.daemon = True  # Make thread exit when main program exits
        threads.append(t)

    for t in threads:
        t.start()

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print('Shutting down servers...')
        # Threads will be terminated when main program exits
        print('Servers shut down.')


def create_runtime(
    runtime_dir: str, reflection_server_spec: ServerSpec
) -> Path:
    """Create a runtime configuration for use with the genkit CLI.

    The runtime information is stored in the form of a timestamped JSON file.
    Note that the file will be cleaned up as soon as the program terminates.

    Args:
        runtime_dir: The directory to store the runtime file in.
        reflection_server_spec: The server specification for the reflection
        server.

    Returns:
        A path object representing the created runtime metadata file.
    """
    if not os.path.exists(runtime_dir):
        os.makedirs(runtime_dir)

    current_datetime = datetime.now()
    runtime_file_name = f'{current_datetime.isoformat()}.json'
    runtime_file_path = Path(os.path.join(runtime_dir, runtime_file_name))
    metadata = json.dumps(
        {
            'id': f'{os.getpid()}',
            'pid': os.getpid(),
            'reflectionServerUrl': reflection_server_spec.url,
            'timestamp': f'{current_datetime.isoformat()}',
        }
    )
    runtime_file_path.write_text(metadata, encoding='utf-8')
    atexit.register(lambda: os.remove(runtime_file_path))
    return runtime_file_path


def is_dev_environment() -> bool:
    """Returns True if the current environment is a development environment.

    Returns:
        True if the current environment is a development environment.
    """
    return os.getenv('GENKIT_ENV') == 'dev'
