# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Base error classes and utilities for Genkit."""

from typing import Any

from genkit.core.registry import Registry
from genkit.core.status_types import StatusName, http_status_code
from pydantic import BaseModel
from typing_extensions import TypeVar


class HttpErrorWireFormat(BaseModel):
    """Wire format for HTTP errors."""

    details: Any = None
    message: str
    status: StatusName

    model_config = {
        'frozen': True,
        'validate_assignment': True,
        'extra': 'forbid',
        'populate_by_name': True,
    }


class GenkitError(Exception):
    """Base error class for Genkit errors."""

    def __init__(
        self,
        *,
        status: StatusName,
        message: str,
        detail: Any = None,
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
        self.code = http_status_code(status)
        self.status = status
        self.detail = detail
        self.source = source

    def to_serializable(self) -> HttpErrorWireFormat:
        """Returns a JSON-serializable representation of this object.

        Returns:
            An HttpErrorWireFormat model instance.
        """
        # This error type is used by 3P authors with the field "detail",
        # but the actual Callable protocol value is "details"
        return HttpErrorWireFormat(
            details=self.detail,
            status=self.status,
            message=self.original_message,
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

    def __init__(
        self, status: StatusName, message: str, details: Any = None
    ) -> None:
        """Initialize a UserFacingError.

        Args:
            status: The status name for this error.
            message: The error message.
            details: Optional details to include.
        """
        super().__init__(status=status, message=message, detail=details)


def get_http_status(error: Any) -> int:
    """Get the HTTP status code for an error.

    Args:
        error: The error to get the status code for.

    Returns:
        The HTTP status code (500 for non-Genkit errors).
    """
    if isinstance(error, GenkitError):
        return error.code
    return 500


def get_callable_json(error: Any) -> HttpErrorWireFormat:
    """Get the JSON representation of an error for callable responses.

    Args:
        error: The error to convert to JSON.

    Returns:
        An HttpErrorWireFormat model instance.
    """
    if isinstance(error, GenkitError):
        return error.to_serializable()
    return HttpErrorWireFormat(
        message='Internal Error',
        status='INTERNAL',
        details=str(error),
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
        return str(error)
    return None


T = TypeVar('T')


def assert_unstable(
    registry: Registry, level: str = 'beta', message: str | None = None
) -> None:
    """Assert that a feature is allowed at the current stability level.

    Args:
        registry: The registry instance to check stability against.
        level: The maximum stability channel allowed.
        message: Optional message describing which feature is not allowed.

    Raises:
        UnstableApiError: If the feature is not allowed at the current stability
        level.
    """
    if level == 'beta' and registry.api_stability == 'stable':
        raise UnstableApiError(level, message)
