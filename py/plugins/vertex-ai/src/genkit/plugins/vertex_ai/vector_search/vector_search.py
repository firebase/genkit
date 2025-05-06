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

from functools import partial
from typing import Any

import structlog
from google.auth.credentials import Credentials
from google.cloud import aiplatform_v1, storage
from google.genai.types import HttpOptions, HttpOptionsDict, Operation

from genkit.ai import GENKIT_CLIENT_HEADER, GenkitRegistry, Plugin
from genkit.plugins.vertex_ai import vertexai_name
from genkit.plugins.vertex_ai.models.retriever import (
    DocRetriever,
    RetrieverOptionsSchema,
)
from genkit.plugins.vertex_ai.models.vectorstore import IndexConfig

logger = structlog.get_logger(__name__)


class VertexAIVectorSearch(Plugin):
    """A plugin for integrating VertexAI Vector Search.

    This class registers VertexAI Vector Stores within a registry,
    and allows interaction to retrieve similar documents.
    """

    name: str = 'vertexAIVectorSearch'

    def __init__(
        self,
        retriever: DocRetriever,
        retriever_extra_args: dict[str, Any] | None = None,
        credentials: Credentials | None = None,
        project: str | None = None,
        location: str | None = 'us-central1',
        embedder: str | None = None,
        embedder_options: dict[str, Any] | None = None,
        http_options: HttpOptions | HttpOptionsDict | None = None,
    ) -> None:
        """Initializes the VertexAIVectorSearch plugin.

        Args:
            retriever: The DocRetriever class to use for retrieving documents.
            retriever_extra_args: Optional dictionary of extra arguments to pass to the
                retriever's constructor.
            credentials: Optional Google Cloud credentials to use. If not provided,
                the default application credentials will be used.
            project: Optional Google Cloud project ID. If not provided, it will be
                inferred from the credentials.
            location: Optional Google Cloud location (region). Defaults to
                'us-central1'.
            embedder: Optional identifier for the embedding model to use.
            embedder_options: Optional dictionary of options to pass to the embedding
                model.
            http_options: Optional HTTP options for API requests.
        """
        http_options = _inject_attribution_headers(http_options=http_options)

        self.project = project
        self.location = location

        self.embedder = embedder
        self.embedder_options = embedder_options

        self.retriever_cls = retriever
        self.retriever_extra_args = retriever_extra_args or {}

        self._storage_client = storage.Client(
            project=self.project,
            credentials=credentials,
            extra_headers=http_options.headers,
        )
        self._index_client = aiplatform_v1.IndexServiceAsyncClient(
            credentials=credentials,
        )
        self._endpoint_client = aiplatform_v1.IndexEndpointServiceAsyncClient(credentials=credentials)

        self._match_service_client_generator = partial(
            aiplatform_v1.MatchServiceAsyncClient,
            credentials=credentials,
        )

    async def create_index(
        self,
        display_name: str,
        description: str | None,
        index_config: IndexConfig | None = None,
        contents_delta_uri: str | None = None,
    ) -> None:
        """Creates a Vertex AI Vector Search index.

        Args:
            display_name: The display name for the index.
            description: Optional description of the index.
            index_config: Optional configuration for the index. If not provided, a
                default configuration is used.
            contents_delta_uri: Optional URI of the Cloud Storage location for the
                contents delta.
        """
        if not index_config:
            index_config = IndexConfig()

        index = aiplatform_v1.Index()
        index.display_name = display_name
        index.description = description
        index.metadata = {
            'config': index_config.model_dump(),
            'contentsDeltaUri': contents_delta_uri,
            'index_update_method': 'STREAM_UPDATE'  # TODO: Add the other 2
        }

        request = aiplatform_v1.CreateIndexRequest(
            parent=self.index_location_path,
            index=index,
        )

        operation = await self._index_client.create_index(request=request)

        logger.debug(await operation.result())

    async def deploy_index(self, index_name: str, endpoint_name: str) -> None:
        """Deploys an index to an endpoint.

        Args:
            index_name: The name of the index to deploy.
            endpoint_name: The name of the endpoint to deploy the index to.
        """
        deployed_index = aiplatform_v1.DeployedIndex()
        deployed_index.id = index_name
        deployed_index.index = self.get_index_path(index_name=index_name)

        request = aiplatform_v1.DeployIndexRequest(
            index_endpoint=endpoint_name,
            deployed_index=deployed_index,
        )

        operation = self._endpoint_client.deploy_index(request=request)

        logger.debug(await operation.result())

    def upload_jsonl_file(self, local_path: str, bucket_name: str, destination_location: str) -> Operation:
        """Uploads a JSONL file to Cloud Storage.

        Args:
            local_path: The local path to the JSONL file.
            bucket_name: The name of the Cloud Storage bucket.
            destination_location: The destination path within the bucket.

        Returns:
            The upload operation.
        """
        bucket = self._storage_client.bucket(bucket_name=bucket_name)
        blob = bucket.blob(destination_location)
        blob.upload_from_filename(local_path)

    def get_index_path(self, index_name: str) -> str:
        """Gets the full resource path of an index.

        Args:
            index_name: The name of the index.

        Returns:
            The full resource path of the index.
        """
        return self._index_client.index_path(project=self.project, location=self.location, index=index_name)

    @property
    def index_location_path(self) -> str:
        """Gets the resource path of the index location.

        Returns:
            The resource path of the index location.
        """
        return self._index_client.common_location_path(project=self.project, location=self.location)

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize plugin with the retriver specified.

        Register actions with the registry making them available for use in the Genkit framework.

        Args:
            ai: The registry to register actions with.
        """
        retriever = self.retriever_cls(
            ai=ai,
            name=self.name,
            match_service_client_generator=self._match_service_client_generator,
            embedder=self.embedder,
            embedder_options=self.embedder_options,
            **self.retriever_extra_args,
        )

        return ai.define_retriever(
            name=vertexai_name(self.name),
            config_schema=RetrieverOptionsSchema,
            fn=retriever.retrieve,
        )


def _inject_attribution_headers(http_options) -> HttpOptions:
    """Adds genkit client info to the appropriate http headers."""
    if not http_options:
        http_options = HttpOptions()
    else:
        if isinstance(http_options, dict):
            http_options = HttpOptions(**http_options)

    if not http_options.headers:
        http_options.headers = {}

    if 'x-goog-api-client' not in http_options.headers:
        http_options.headers['x-goog-api-client'] = GENKIT_CLIENT_HEADER
    else:
        http_options.headers['x-goog-api-client'] += f' {GENKIT_CLIENT_HEADER}'

    if 'user-agent' not in http_options.headers:
        http_options.headers['user-agent'] = GENKIT_CLIENT_HEADER
    else:
        http_options.headers['user-agent'] += f' {GENKIT_CLIENT_HEADER}'

    return http_options
