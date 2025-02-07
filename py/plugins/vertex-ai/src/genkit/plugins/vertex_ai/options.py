# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Common options for plugin configuration."""
import dataclasses
import json
import logging
import os

import google.oauth2.credentials as oauth2_creds
from google.auth import credentials as auth_credentials

from genkit.core.schemas import ModelInfo
from genkit.plugins.vertex_ai import constants as const

LOG = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class PluginOptions:
    project_id: str | None = None
    location: str | None = None
    google_auth: auth_credentials.Credentials | None = None
    models: list[str | ModelInfo] = dataclasses.field(default_factory=list)


def get_project_from_firebase_config() -> str  | None:
    config = os.getenv(const.FIREBASE_CONFIG)
    if config:
        try:
            project_id = json.loads(config)['projectId']
            return project_id
        except json.JSONDecodeError:
            LOG.error('Invalid JSON syntax in %s environment variable',
                      const.FIREBASE_CONFIG)
        except KeyError:
            LOG.error('projectId key is not in %s environment variable',
                      const.FIREBASE_CONFIG)

    return None


def get_plugin_parameters(options: PluginOptions | None):
    project_id = options.project_id
    if not project_id:
        # The project_id retrieval order:
        # - defined in a code
        # - defined in GOOGLE_CLOUD_PROJECT env variable
        # - defined in firebase config variable
        # - defined by gcloud auth application-default login
        #   (by VertexAI Python library)
        project_id = (os.getenv(const.GCLOUD_PROJECT)
                      or get_project_from_firebase_config())

    location = (options.location
                or os.getenv(const.GCLOUD_LOCATION)
                or const.DEFAULT_REGION)

    credentials = options.google_auth

    sa_env = os.getenv(const.GCLOUD_SERVICE_ACCOUNT_CREDS)
    if not credentials and sa_env:
        # Credentials from oauth2 inherit from auth module credentials
        credentials = oauth2_creds.Credentials.from_authorized_user_file(
            sa_env, scopes=[const.GCLOUD_PLATFORM_OAUTH_SCOPE])

    return project_id, location, credentials
