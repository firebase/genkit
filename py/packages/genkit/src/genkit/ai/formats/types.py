# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Format definition classes."""

import abc
from collections.abc import Callable
from typing import Any

from genkit.ai.model import (
    GenerateResponseChunkWrapper,
    MessageWrapper,
)
from genkit.core.typing import (
    OutputConfig,
)

type MessageParser[T] = Callable[[MessageWrapper], T]
type ChunkParser[T] = Callable[[GenerateResponseChunkWrapper], T]


class FormatterConfig(OutputConfig):
    """Configuration for formatters."""

    default_instructions: bool | None = None


class Formatter[O, CO]:
    """Base class for formatters."""

    def __init__(
        self,
        message_parser: MessageParser[O],
        chunk_parser: ChunkParser[CO],
        instructions: str | None,
    ):
        """Initializes a Formatter.

        Args:
            message_parser: A callable that parses a Message into type O.
            chunk_parser: A callable that parses a GenerateResponseChunkWrapper into type CO.
            instructions: Optional instructions for the formatter.
        """
        self.instructions = instructions
        self.__message_parser = message_parser
        self.__chunk_parser = chunk_parser

    def parse_message(self, message: MessageWrapper) -> O:
        """Parses a message.

        Args:
            message: The message to parse.

        Returns:
            The parsed message.
        """
        return self.__message_parser(message)

    def parse_chunk(self, chunk: GenerateResponseChunkWrapper) -> O:
        """Parses a chunk.

        Args:
            chunk: The chunk to parse.

        Returns:
            The parsed chunk.
        """
        return self.__chunk_parser(chunk)


class FormatDef:
    """Format definitions."""

    def __init__(self, name: str, config: FormatterConfig):
        """Initializes a FormatDef.

        Args:
            name: The name of the format.
            config: The configuration for the format.
        """
        self.name = name
        self.config = config
        pass

    @abc.abstractmethod
    def handle(self, schema: dict[str, Any] | None) -> Formatter:
        """Handles the format.

        Args:
            schema: Optional schema for the format.

        Returns:
            A Formatter instance.
        """
        pass

    def __call__(self, schema: dict[str, Any] | None) -> Formatter:
        """Calls the handle method.

        Args:
            schema: Optional schema for the format.

        Returns:
            A Formatter instance.
        """
        return self.handle(schema)
