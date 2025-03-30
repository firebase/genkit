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

"""Base error classes and utilities for Genkit."""

import traceback
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from genkit.core.status_types import StatusCodes, StatusName, http_status_code


class GenkitReflectionApiDetailsWireFormat(BaseModel):
    """Wire format for HTTP error details."""

    model_config = ConfigDict(extra='allow', populate_by_name=True)

    stack: str | None = None
    trace_id: str | None = Field(None, alias='traceId')


class GenkitReflectionApiErrorWireFormat(BaseModel):
    """Wire format for HTTP errors."""

    details: GenkitReflectionApiDetailsWireFormat | None = None
    message: str
    code: int = StatusCodes.INTERNAL.value

    model_config = {
        'frozen': True,
        'validate_assignment': True,
        'extra': 'forbid',
        'populate_by_name': True,
    }


class HttpErrorWireFormat(BaseModel):
    """Wire format for HTTP error details."""

    model_config = ConfigDict(extra='allow', populate_by_name=True)

    details: Any
    message: str
    status: str = StatusCodes.INTERNAL.name


class GenkitError(Exception):
    """Base error class for Genkit errors."""

    def __init__(
        self,
        *,
        message: str,
        status: StatusName | None = None,
        cause: Exception | None = None,
        details: Any = None,
        trace_id: str | None = None,
        source: str | None = None,
    ) -> None:
        """Initialize a GenkitError.

        Args:
            status: The status name for this error.
            message: The error message.
            detail: Optional detail information.
            source: Optional source of the error.
        """
        source_prefix = f'{source}: ' if source else ''
        super().__init__(f'{source_prefix}{status}: {message}')
        self.original_message = message

        self.status = status
        if not self.status and isinstance(cause, GenkitError):
            self.status = cause.status

        if not self.status:
            self.status = 'INTERNAL'

        self.http_code = http_status_code(self.status)

        if not details:
            details = {}
        if 'stack' not in details:
            details['stack'] = get_error_stack(cause if cause else self)
        if 'trace_id' not in details and trace_id:
            details['trace_id'] = trace_id

        self.details = details
        self.source = source
        self.trace_id = trace_id
        self.cause = cause

    def to_callable_serializable(self) -> HttpErrorWireFormat:
        """Returns a JSON-serializable representation of this object.

        Returns:
            An HttpErrorWireFormat model instance.
        """
        # This error type is used by 3P authors with the field "details",
        # but the actual Callable protocol value is "details"
        return HttpErrorWireFormat(
            details=self.details,
            status=StatusCodes[self.status].name,
            message=repr(self.cause) if self.cause else self.original_message,
        )

    def to_serializable(self) -> GenkitReflectionApiErrorWireFormat:
        """Returns a JSON-serializable representation of this object.

        Returns:
            An HttpErrorWireFormat model instance.
        """
        # This error type is used by 3P authors with the field "details",
        # but the actual Callable protocol value is "details"
        return GenkitReflectionApiErrorWireFormat(
            details=self.details,
            code=StatusCodes[self.status].value,
            message=repr(self.cause) if self.cause else self.original_message,
        )


class UnstableApiError(GenkitError):
    """Error raised when using unstable APIs from a more stable instance."""

    def __init__(self, level: str = 'beta', message: str | None = None) -> None:
        """Initialize an UnstableApiError.

        Args:
            level: The stability level required.
            message: Optional message describing which feature is not allowed.
        """
        msg_prefix = f'{message} ' if message else ''
        super().__init__(
            status='FAILED_PRECONDITION',
            message=f"{msg_prefix}This API requires '{level}' stability level.\n\n"
            f'To use this feature, initialize Genkit using `from genkit.{level} import genkit`.',
        )


class UserFacingError(GenkitError):
    """Error class for issues to be returned to users.

    Using this error allows a web framework handler (e.g. FastAPI, Flask) to know it
    is safe to return the message in a request. Other kinds of errors will
    result in a generic 500 message to avoid the possibility of internal
    exceptions being leaked to attackers.
    """

    def __init__(self, status: StatusName, message: str, details: Any = None) -> None:
        """Initialize a UserFacingError.

        Args:
            status: The status name for this error.
            message: The error message.
            details: Optional details to include.
        """
        super().__init__(status=status, message=message, details=details)


def get_http_status(error: Any) -> int:
    """Get the HTTP status code for an error.

    Args:
        error: The error to get the status code for.

    Returns:
        The HTTP status code (500 for non-Genkit errors).
    """
    if isinstance(error, GenkitError):
        return error.http_code
    return 500


def get_reflection_json(error: Any) -> GenkitReflectionApiErrorWireFormat:
    """Get the JSON representation of an error for callable responses.

    Args:
        error: The error to convert to JSON.

    Returns:
        An HttpErrorWireFormat model instance.
    """
    if isinstance(error, GenkitError):
        return error.to_serializable()
    return GenkitReflectionApiErrorWireFormat(
        message=str(error),
        code=StatusCodes.INTERNAL.value,
        details={'stack': get_error_stack(error)},
    )


def get_callable_json(error: Any) -> HttpErrorWireFormat:
    """Get the JSON representation of an error for callable responses.

    Args:
        error: The error to convert to JSON.

    Returns:
        An HttpErrorWireFormat model instance.
    """
    if isinstance(error, GenkitError):
        return error.to_callable_serializable()
    return HttpErrorWireFormat(
        message=str(error),
        status=StatusCodes.INTERNAL.name,
        details={'stack': get_error_stack(error)},
    )


def get_error_message(error: Any) -> str:
    """Extract error message from an error object.

    Args:
        error: The error to get the message from.

    Returns:
        The error message string.
    """
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def get_error_stack(error: Exception) -> str | None:
    """Extract stack trace from an error object.

    Args:
        error: The error to get the stack trace from.

    Returns:
        The stack trace string if available.
    """
    if isinstance(error, Exception):
        return ''.join(traceback.format_tb(error.__traceback__))
    return None
