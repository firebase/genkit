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


"""Flask Plugin for Genkit.

This plugin provides Flask integration for Genkit, enabling you to expose
Genkit flows as HTTP endpoints in a Flask application.

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         Flask Plugin                                    │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  Plugin Entry Point (__init__.py)                                       │
    │  └── genkit_flask_handler() - Create Flask route handler                │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  handler.py - Request Handler                                           │
    │  ├── genkit_flask_handler() - Factory for Flask handlers                │
    │  ├── Request parsing and validation                                     │
    │  └── Response serialization                                             │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        Request Flow                                     │
    │                                                                         │
    │  HTTP Request ──► Flask Route ──► genkit_flask_handler ──► Genkit Flow  │
    │                                                                         │
    │  HTTP Response ◄── Flask Route ◄── Handler ◄── Flow Result              │
    └─────────────────────────────────────────────────────────────────────────┘

Example:
    ```python
    from flask import Flask
    from genkit import Genkit
    from genkit.plugins.flask import genkit_flask_handler

    app = Flask(__name__)
    ai = Genkit(...)


    @ai.flow()
    async def my_flow(prompt: str) -> str:
        response = await ai.generate(prompt=prompt)
        return response.text


    # Expose flow as HTTP endpoint
    @app.route('/api/flow', methods=['POST'])
    def handle_flow():
        return genkit_flask_handler(ai, my_flow)
    ```

Caveats:
    - Requires Flask to be installed
    - Async flows are run synchronously in Flask (use async frameworks for better performance)
    - For production, consider using the async-native Genkit server

See Also:
    - Flask documentation: https://flask.palletsprojects.com/
    - Genkit documentation: https://genkit.dev/
"""

from .handler import genkit_flask_handler


def package_name() -> str:
    """Get the package name for the Flask plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.flask'


__all__ = ['package_name', genkit_flask_handler.__name__]
