# Copyright 2026 Google LLC
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

"""Shared authentication utilities for the Checks plugin.

This module provides common authentication logic used by both the Checks
plugin and middleware components.
"""

import json
import os
from typing import Any

from google.auth import default as default_credentials
from google.auth.credentials import Credentials
from google.oauth2 import service_account

# OAuth scopes required for Checks API
CLOUD_PLATFORM_OAUTH_SCOPE = 'https://www.googleapis.com/auth/cloud-platform'
CHECKS_OAUTH_SCOPE = 'https://www.googleapis.com/auth/checks'

_DEFAULT_SCOPES = [CLOUD_PLATFORM_OAUTH_SCOPE, CHECKS_OAUTH_SCOPE]


def initialize_credentials(
    auth_options: dict[str, Any] | None = None,
    scopes: list[str] | None = None,
) -> tuple[Credentials, str | None]:
    """Initialize Google Cloud credentials for the Checks API.

    Credentials are loaded in the following order of precedence:
    1. GCLOUD_SERVICE_ACCOUNT_CREDS environment variable (JSON string)
    2. auth_options.credentials_file (service account file path)
    3. Default application credentials

    Args:
        auth_options: Optional authentication options including:
            - credentials_file: Path to service account JSON file
            - project_id: GCP project ID
        scopes: OAuth scopes to request. Defaults to cloud-platform and checks scopes.

    Returns:
        Tuple of (credentials, project_id). project_id may be None if not
        provided in options and not available from default credentials.

    Raises:
        ValueError: If credentials cannot be established.
    """
    if scopes is None:
        scopes = _DEFAULT_SCOPES

    # Check for service account credentials in environment
    if os.environ.get('GCLOUD_SERVICE_ACCOUNT_CREDS'):
        creds_data = json.loads(os.environ['GCLOUD_SERVICE_ACCOUNT_CREDS'])
        credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=scopes,
        )
        project_id = auth_options.get('project_id') if auth_options else None
        return credentials, project_id

    # Use credentials file if provided
    if auth_options and auth_options.get('credentials_file'):
        credentials = service_account.Credentials.from_service_account_file(
            auth_options['credentials_file'],
            scopes=scopes,
        )
        project_id = auth_options.get('project_id')
        return credentials, project_id

    # Fall back to default credentials
    credentials, default_project = default_credentials(scopes=scopes)
    project_id = (auth_options or {}).get('project_id') or default_project
    return credentials, project_id


__all__ = [
    'CHECKS_OAUTH_SCOPE',
    'CLOUD_PLATFORM_OAUTH_SCOPE',
    'initialize_credentials',
]
