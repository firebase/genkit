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

"""
Tool to review and test all Genkit flows in a sample's main.py.

Usage:
    python review_sample_flows.py <path_to_sample_directory>

Example:
    python review_sample_flows.py samples/google-genai-hello
"""

import argparse
import asyncio
import builtins
import importlib.util
import sys
import traceback
from pathlib import Path
from typing import Any

# Mock input to prevent blocking if the sample asks for API keys at top level
builtins.input = lambda prompt="": "dummy_value"


async def main() -> None:
    parser = argparse.ArgumentParser(description='Test all flows in a Genkit sample.')
    parser.add_argument('sample_dir', type=str, help='Path to the sample directory')
    parser.add_argument('--output', type=str, default='flow_review_results.txt', help='Output report file')
    args = parser.parse_args()

    sample_path = Path(args.sample_dir).resolve()
    if not sample_path.exists():
        print(f"Error: Directory not found: {sample_path}")
        sys.exit(1)

    # Assume the main entry point is at src/main.py or main.py
    main_py_path = sample_path / 'src' / 'main.py'
    if not main_py_path.exists():
        main_py_path = sample_path / 'main.py'
        if not main_py_path.exists():
            print(f"Error: Could not find src/main.py or main.py in {sample_path}")
            sys.exit(1)

    print(f"Testing flows in: {main_py_path}")
    
    # Add the source directory to sys.path so imports work
    src_dir = main_py_path.parent
    sys.path.insert(0, str(src_dir))

    # Import the module dynamically
    spec = importlib.util.spec_from_file_location("sample_main", main_py_path)
    if spec is None or spec.loader is None:
        print("Error: Could not load module spec.")
        sys.exit(1)
    
    module = importlib.util.module_from_spec(spec)
    sys.modules["sample_main"] = module
    
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Error executing module: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Find the Genkit instance
    ai_instance = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        # Check if it looks like a Genkit instance (has registry)
        if hasattr(attr, 'registry') and hasattr(attr, 'generate'):
             ai_instance = attr
             break
    
    if ai_instance is None:
        print("Error: Could not find 'ai' (Genkit instance) in the module.")
        sys.exit(1)

    print("Found Genkit instance. Discovering flows...")
    
    from genkit.core.action import ActionKind
    
    # List all flows
    registry = ai_instance.registry
    actions_map = registry.get_actions_by_kind(ActionKind.FLOW)
    
    # Track results for summary
    successful_flows = []
    failed_flows = []
    
    report_lines = []
    report_lines.append(f"Flow Review Report for {sample_path.name}")
    report_lines.append("=" * 60)
    report_lines.append("")
    
    # We'll add the summary after testing all flows
    detail_lines = []

    for flow_name, flow_action in actions_map.items():
        print(f"Testing flow: {flow_name}...")
        detail_lines.append(f"Flow: {flow_name}")
        detail_lines.append("-" * 30)
        
        try:
            input_data = generate_input(flow_action)
            detail_lines.append(f"Generated Input: {input_data}")
            
            # Run the flow
            result = await flow_action.arun(input_data)
            
            detail_lines.append("Status: SUCCESS")
            detail_lines.append(f"Output: {result.response}")
            successful_flows.append(flow_name)
        except Exception as e:
            detail_lines.append("Status: FAILED")
            detail_lines.append(f"Error: {e}")
            failed_flows.append(flow_name)
        
        detail_lines.append("")
        print(f"Finished {flow_name}.")

    # Add summary section
    total_flows = len(actions_map)
    success_count = len(successful_flows)
    failure_count = len(failed_flows)
    
    report_lines.append("SUMMARY")
    report_lines.append("=" * 60)
    report_lines.append(f"Total Flows: {total_flows}")
    report_lines.append(f"Successful: {success_count}")
    report_lines.append(f"Failed: {failure_count}")
    report_lines.append("")
    
    if failed_flows:
        report_lines.append("Failed Flows:")
        for flow in failed_flows:
            report_lines.append(f"  ✗ {flow}")
        report_lines.append("")
    
    if successful_flows:
        report_lines.append("Successful Flows:")
        for flow in successful_flows:
            report_lines.append(f"  ✓ {flow}")
        report_lines.append("")
    
    report_lines.append("=" * 60)
    report_lines.append("")
    report_lines.append("DETAILED RESULTS")
    report_lines.append("=" * 60)
    report_lines.append("")
    
    # Append detailed results
    report_lines.extend(detail_lines)

    # Write report
    with open(args.output, 'w') as f:
        f.write('\n'.join(report_lines))
    
    print(f"Review complete. Report saved to {args.output}")

def generate_input(flow_action: Any) -> Any:
    """Generates heuristic input for a flow based on its schema."""
    schema = flow_action.input_schema
    if not schema:
        return None
    
    return generate_from_json_schema(schema)

def generate_from_json_schema(schema: dict[str, Any]) -> Any:
    """Simplistic JSON schema input generator."""
    type_ = schema.get('type')
    
    if 'default' in schema:
        return schema['default']

    if type_ == 'string':
        return "test_string"
    elif type_ == 'integer':
        return 42
    elif type_ == 'number':
        return 3.14
    elif type_ == 'boolean':
        return True
    elif type_ == 'object':
        properties = schema.get('properties', {})
        result = {}
        for prop_name, prop_schema in properties.items():
            result[prop_name] = generate_from_json_schema(prop_schema)
        return result
    elif type_ == 'array':
        items_schema = schema.get('items', {})
        return [generate_from_json_schema(items_schema)]
    
    return None

if __name__ == "__main__":
    asyncio.run(main())
