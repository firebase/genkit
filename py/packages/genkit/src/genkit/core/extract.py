# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import json5
from partial_json_parser import loads


def parse_partial_json(json_string: str):
    """
    Parses partially complete JSON string.
    """
    return loads(json_string)


def extract_json(text: str, throw_on_bad_json: bool = True):
    """
    Extracts JSON from string with lenient parsing rules to improve likelihood of successful extraction.
    """
    opening_char = None
    closing_char = None
    start_pos = None
    nesting_count = 0
    in_string = False
    escape_next = False

    for i in range(len(text)):
        char = text[i].replace('\u00a0', ' ')

        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if not opening_char and (char == '{' or char == '['):
            # Look for opening character
            opening_char = char
            closing_char = '}' if char == '{' else ']'
            start_pos = i
            nesting_count += 1
        elif char == opening_char:
            # Increment nesting for matching opening character
            nesting_count += 1
        elif char == closing_char:
            # Decrement nesting for matching closing character
            nesting_count -= 1
            if not nesting_count:
                # Reached end of target element
                return json5.loads(text[start_pos or 0 : i + 1])
    if start_pos is not None and nesting_count > 0:
        # If an incomplete JSON structure is detected
        try:
            # Parse the incomplete JSON structure using partial-json for lenient parsing
            return parse_partial_json(text[start_pos:])
        except:
            # If parsing fails, throw an error
            if throw_on_bad_json:
                raise ValueError(
                    f'Invalid JSON extracted from model output: {text}'
                )
            return None

    if throw_on_bad_json:
        raise ValueError(f'Invalid JSON extracted from model output: {text}')
    return None


class ExtractItemsResult:
    """Result of array item extraction."""

    def __init__(self, items: list, cursor: int):
        self.items = items
        self.cursor = cursor


def extract_items(text: str, cursor: int = 0) -> ExtractItemsResult:
    """
    Extracts complete objects from the first array found in the text.
    Processes text from the cursor position and returns both complete items
    and the new cursor position.
    """
    items = []
    current_cursor = cursor

    # Find the first array start if we haven't already processed any text
    if cursor == 0:
        array_start = text.find('[')
        if array_start == -1:
            return {'items': [], 'cursor': len(text)}
        current_cursor = array_start + 1

    object_start = -1
    brace_count = 0
    in_string = False
    escape_next = False

    # Process the text from the cursor position
    for i in range(current_cursor, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == '{':
            if brace_count == 0:
                object_start = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and object_start != -1:
                try:
                    obj = json5.loads(text[object_start : i + 1])
                    items.append(obj)
                    current_cursor = i + 1
                    object_start = -1
                except:
                    # If parsing fails, continue
                    pass
        elif char == ']' and brace_count == 0:
            # End of array
            break

    return ExtractItemsResult(items=items, cursor=current_cursor)
