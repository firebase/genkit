# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests parameter assignment that is set to the Vertex AI."""
import json

from genkit.plugins.vertex_ai import constants as const
from genkit.plugins.vertex_ai.options import (
    PluginOptions,
    get_plugin_parameters,
)

GCLOUD_ENV_PROJECT_ID = 'gcp_project_id'
GCLOUD_ENV_REGION = 'asia-east1'
SAMPLE_FIREBASE_CONFIG = {'projectId': 'firebase_gcp_project_id'}


def test_empty_location():
    options = PluginOptions()
    _, location, _ = get_plugin_parameters(options)
    assert location == const.DEFAULT_REGION


def test_specific_location():
    region = 'asia-east2'
    options = PluginOptions(location=region)
    _, location, _ = get_plugin_parameters(options)
    assert location == region


def test_location_from_env(monkeypatch):
    monkeypatch.setenv(const.GCLOUD_LOCATION, GCLOUD_ENV_REGION)

    options = PluginOptions()
    _, location, _ = get_plugin_parameters(options)
    assert location == GCLOUD_ENV_REGION


def test_location_priority(monkeypatch):
    monkeypatch.setenv(const.GCLOUD_LOCATION, GCLOUD_ENV_REGION)

    region = 'asia-east2'
    options = PluginOptions(location=region)
    _, location, _ = get_plugin_parameters(options)

    assert location == region


def test_no_project_id():
    options = PluginOptions()
    project_id, _, _ = get_plugin_parameters(options)
    assert not project_id


def test_specific_project_id():
    expected_project_id = 'parameter-project-id'
    options = PluginOptions(project_id=expected_project_id)
    project_id, _, _ = get_plugin_parameters(options)
    assert project_id == expected_project_id


def test_project_id_from_env(monkeypatch):
    monkeypatch.setenv(const.GCLOUD_PROJECT, GCLOUD_ENV_PROJECT_ID)

    options = PluginOptions()
    project_id, _, _ = get_plugin_parameters(options)
    assert project_id == GCLOUD_ENV_PROJECT_ID


def test_project_id_from_firebase_config(monkeypatch):
    monkeypatch.setenv(const.FIREBASE_CONFIG,
                       json.dumps(SAMPLE_FIREBASE_CONFIG))
    options = PluginOptions()
    project_id, _, _ = get_plugin_parameters(options)
    assert project_id == SAMPLE_FIREBASE_CONFIG['projectId']


def test_project_id_env_priority(monkeypatch):
    monkeypatch.setenv(const.FIREBASE_CONFIG,
                       json.dumps(SAMPLE_FIREBASE_CONFIG))
    monkeypatch.setenv(const.GCLOUD_PROJECT, GCLOUD_ENV_PROJECT_ID)

    options = PluginOptions()
    project_id, _, _ = get_plugin_parameters(options)
    assert project_id == GCLOUD_ENV_PROJECT_ID


def test_project_id_parameter_priority(monkeypatch):
    monkeypatch.setenv(const.FIREBASE_CONFIG,
                       json.dumps(SAMPLE_FIREBASE_CONFIG))
    monkeypatch.setenv(const.GCLOUD_PROJECT, GCLOUD_ENV_PROJECT_ID)

    expected_project_id = 'parameter-project-id'
    options = PluginOptions(project_id=expected_project_id)
    project_id, _, _ = get_plugin_parameters(options)
    assert project_id == expected_project_id
