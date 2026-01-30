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

"""Tests for PostgresEngine."""

import pytest

from genkit.plugins.cloud_sql_pg import Column, IpAddressTypes


class TestColumn:
    """Tests for Column class."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        col = Column(name='test_col', data_type='TEXT')
        assert col.name == 'test_col'
        assert col.data_type == 'TEXT'
        assert col.nullable is True

    def test_non_nullable_column(self) -> None:
        """Test non-nullable column."""
        col = Column(name='required_col', data_type='INT', nullable=False)
        assert col.name == 'required_col'
        assert col.data_type == 'INT'
        assert col.nullable is False

    def test_invalid_name_type(self) -> None:
        """Test that invalid name type raises error."""
        with pytest.raises(TypeError, match='Column name must be a string'):
            Column(name=123, data_type='TEXT')  # type: ignore[arg-type]

    def test_invalid_data_type_type(self) -> None:
        """Test that invalid data_type type raises error."""
        with pytest.raises(TypeError, match='Column data_type must be a string'):
            Column(name='test', data_type=123)  # type: ignore[arg-type]


class TestIpAddressTypes:
    """Tests for IpAddressTypes enum."""

    def test_public_value(self) -> None:
        """Test PUBLIC value."""
        assert IpAddressTypes.PUBLIC.value == 'PUBLIC'

    def test_private_value(self) -> None:
        """Test PRIVATE value."""
        assert IpAddressTypes.PRIVATE.value == 'PRIVATE'

    def test_to_ip_types_public(self) -> None:
        """Test conversion to Cloud SQL IPTypes for PUBLIC."""
        from google.cloud.sql.connector import IPTypes

        ip_type = IpAddressTypes.PUBLIC.to_ip_types()
        assert ip_type == IPTypes.PUBLIC

    def test_to_ip_types_private(self) -> None:
        """Test conversion to Cloud SQL IPTypes for PRIVATE."""
        from google.cloud.sql.connector import IPTypes

        ip_type = IpAddressTypes.PRIVATE.to_ip_types()
        assert ip_type == IPTypes.PRIVATE


class TestPostgresEngineValidation:
    """Tests for PostgresEngine validation (without actual DB connection)."""

    @pytest.mark.asyncio
    async def test_from_instance_requires_both_user_and_password(self) -> None:
        """Test that from_instance requires both user and password or neither."""
        from genkit.plugins.cloud_sql_pg import PostgresEngine

        # Only user provided
        with pytest.raises(ValueError, match="Only one of 'user' or 'password'"):
            await PostgresEngine.from_instance(
                project_id='test-project',
                region='us-central1',
                instance='test-instance',
                database='test-db',
                user='test-user',
            )

        # Only password provided
        with pytest.raises(ValueError, match="Only one of 'user' or 'password'"):
            await PostgresEngine.from_instance(
                project_id='test-project',
                region='us-central1',
                instance='test-instance',
                database='test-db',
                password='test-password',
            )

    @pytest.mark.asyncio
    async def test_from_connection_string_requires_asyncpg(self) -> None:
        """Test that from_connection_string requires asyncpg driver."""
        from genkit.plugins.cloud_sql_pg import PostgresEngine

        with pytest.raises(ValueError, match="must start with 'postgresql\\+asyncpg://'"):
            await PostgresEngine.from_connection_string('postgresql://user:pass@host/db')

        with pytest.raises(ValueError, match="must start with 'postgresql\\+asyncpg://'"):
            await PostgresEngine.from_connection_string('mysql://user:pass@host/db')
