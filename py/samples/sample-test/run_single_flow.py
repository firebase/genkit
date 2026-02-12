#!/usr/bin/env python3
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

# pyrefly: ignore-file

"""Helper script to run a single Genkit flow in isolation.

This script is called by review_sample_flows.py to execute each flow in a
separate subprocess, avoiding event loop conflicts and enabling proper
async execution.

Usage:
    python run_single_flow.py <sample_dir> <flow_name> [--input <json_string>]

Output:
    JSON object with 'success', 'result', and 'error' fields
"""

import argparse
import asyncio
import importlib.util
import json
import logging
import sys
import traceback
from pathlib import Path
from typing import Any

from genkit.core.action import ActionKind


def format_output(output: Any) -> Any:  # noqa: ANN401 - intentional use of Any for arbitrary flow outputs
    """Format flow output for serialization.

    Args:
        output: The flow output to format

    Returns:
        Serializable representation
    """
    from genkit.types import Media

    # Handle None
    if output is None:
        return None

    # Handle Media objects
    if isinstance(output, Media):
        url = output.url or ''
        if len(url) > 500:
            url = f'{url[:100]}...{url[-50:]}'
        return {
            'type': 'Media',
            'url': url,
            'url_length': len(output.url or ''),
            'content_type': output.content_type,
        }

    # Handle Pydantic models
    if hasattr(output, 'model_dump'):
        try:
            return output.model_dump()
        except Exception:  # noqa: S110 - intentional fallback if model_dump fails
            pass

    # Handle dicts/lists
    if isinstance(output, (dict, list)):
        return output

    # Default: convert to string
    return str(output)


async def run_flow(sample_dir: str, flow_name: str, input_data: Any) -> dict[str, Any]:  # noqa: ANN401 - intentional use of Any for arbitrary flow outputs
    """Run a single flow and return result.

    Args:
        sample_dir: Path to sample directory
        flow_name: Name of flow to run
        input_data: Input data for the flow

    Returns:
        Dict with 'success', 'result', 'error' fields
    """
    result: dict[str, Any] = {
        'success': False,
        'result': None,
        'error': None,
    }

    try:
        # Import the sample module
        sample_path = Path(sample_dir).resolve()
        main_py = sample_path / 'src' / 'main.py'
        if not main_py.exists():
            main_py = sample_path / 'main.py'

            result['error'] = f'No main.py found in {sample_path}'
            return result

        # Add the py/ root directory to sys.path so 'samples.shared' imports work
        # sample_path is .../py/samples/sample-name
        sys.path.insert(0, str(sample_path.parent.parent))

        # Add the sample's src/ directory to sys.path for relative imports
        # (e.g., 'from case_01 import prompts' in framework-restaurant-demo)
        if main_py.parent.name == 'src':
            sys.path.insert(0, str(main_py.parent))

        # Load the module

        spec = importlib.util.spec_from_file_location('sample_main', main_py)
        if not spec or not spec.loader:
            result['error'] = 'Failed to load sample module'
            return result

        module = importlib.util.module_from_spec(spec)
        sys.modules['sample_main'] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            result['error'] = f'Failed to import sample: {e}'
            return result

        # Find the Genkit instance
        ai_instance = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, '__class__') and attr.__class__.__name__ == 'Genkit':
                ai_instance = attr
                break

        if not ai_instance:
            result['error'] = 'No Genkit instance found in sample'
            return result

        # Get the flow action from registry
        try:
            registry = ai_instance.registry
            actions_map = await registry.resolve_actions_by_kind(ActionKind.FLOW)

            if flow_name not in actions_map:
                result['error'] = f"Flow '{flow_name}' not found in registry"
                return result

            flow_action = actions_map[flow_name]
        except Exception as e:
            result['error'] = f"Failed to retrieve flow '{flow_name}': {e}"
            return result

        # Run the flow - use arun() in async context
        try:
            # Convert dict input to Pydantic model if an input schema is defined
            validated_input = input_data
            if isinstance(input_data, dict) and hasattr(flow_action, 'input_type') and flow_action.input_type:
                try:
                    # Use the Action's Pydantic TypeAdapter to validate and convert the input
                    validated_input = flow_action.input_type.validate_python(input_data)
                except Exception:  # noqa: S110 - intentional fallback if validation fails
                    # If validation fails, we try with the original dict
                    pass

            # Always use arun() since we're in an async context
            flow_result = await flow_action.arun(validated_input)

            # Extract response
            response_obj = flow_result.response

            # Format output
            formatted_output = format_output(response_obj)

            result['success'] = True
            result['result'] = formatted_output

        except Exception as e:
            # pyrefly: ignore[unbound-name] - traceback is imported at top of file
            result['error'] = f'Flow execution failed: {e}\n{traceback.format_exc()}'

    except Exception as e:
        result['error'] = f'Unexpected error: {e}'

    return result


def main() -> None:
    """Run a single flow and output JSON result."""
    parser = argparse.ArgumentParser(description='Run a single Genkit flow.')
    parser.add_argument('sample_dir', type=str, help='Path to sample directory')
    parser.add_argument('flow_name', type=str, help='Name of flow to run')
    parser.add_argument('--input', type=str, default='null', help='JSON string of input data')
    args = parser.parse_args()

    # Suppress verbose logging
    logging.basicConfig(level=logging.ERROR)
    logging.getLogger('genkit').setLevel(logging.ERROR)
    logging.getLogger('google').setLevel(logging.ERROR)

    # Parse input
    try:
        input_data = json.loads(args.input)
    except json.JSONDecodeError:
        return

    # Run flow in async context
    # We do NOT redirect stdout so that logs/prints from the flow are visible
    try:
        asyncio.run(run_flow(args.sample_dir, args.flow_name, input_data))
    except Exception:
        # pyrefly: ignore[unbound-name] - traceback is imported at top of file
        traceback.print_exc()
        return

    # Print result with markers so the caller can extract it from stdout


if __name__ == '__main__':
    main()
