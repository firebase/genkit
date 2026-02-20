#!/usr/bin/env python3
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

"""Fix package metadata for all Genkit Python packages.

Adds missing keywords and project.urls to all plugin pyproject.toml files.
"""

import re
from pathlib import Path

# Standard keywords for all Genkit packages
BASE_KEYWORDS = [
    'genkit',
    'ai',
    'llm',
    'machine-learning',
    'artificial-intelligence',
    'generative-ai',
]

# Plugin-specific keywords
PLUGIN_KEYWORDS = {
    'anthropic': ['anthropic', 'claude'],
    'amazon-bedrock': ['aws', 'bedrock', 'amazon'],
    'aws': ['aws', 'amazon', 'xray', 'telemetry'],
    'azure': ['azure', 'microsoft', 'application-insights', 'telemetry'],
    'cloudflare-workers-ai': ['cloudflare', 'workers-ai', 'otlp', 'telemetry'],
    'compat-oai': ['openai', 'openai-compatible'],
    'deepseek': ['deepseek'],
    'dev-local-vectorstore': ['vector-store', 'embeddings', 'local'],
    'evaluators': ['evaluation', 'metrics', 'ragas'],
    'firebase': ['firebase', 'google', 'firestore', 'telemetry'],
    'flask': ['flask', 'web', 'server'],
    'google-cloud': ['google-cloud', 'gcp', 'cloud-trace', 'telemetry'],
    'google-genai': ['google', 'gemini', 'vertex-ai', 'imagen'],
    'huggingface': ['huggingface', 'transformers', 'inference-api'],
    'mcp': ['mcp', 'model-context-protocol'],
    'mistral': ['mistral', 'mistral-ai'],
    'microsoft-foundry': ['azure', 'microsoft', 'azure-openai', 'foundry'],
    'observability': ['observability', 'telemetry', 'sentry', 'honeycomb', 'datadog'],
    'ollama': ['ollama', 'local', 'self-hosted'],
    'vertex-ai': ['google', 'vertex-ai', 'model-garden'],
    'xai': ['xai', 'grok', 'elon-musk'],
}

# Standard project URLs
PROJECT_URLS = """
[project.urls]
"Bug Tracker" = "https://github.com/firebase/genkit/issues"
"Documentation" = "https://firebase.google.com/docs/genkit"
"Homepage" = "https://github.com/firebase/genkit"
"Repository" = "https://github.com/firebase/genkit/tree/main/py"
"""


def get_plugin_name(pyproject_path: Path) -> str:
    """Extract plugin name from directory path."""
    return pyproject_path.parent.name


def add_keywords(content: str, plugin_name: str) -> str:
    """Add keywords to pyproject.toml content if missing."""
    if 'keywords' in content:
        return content

    # Build keywords list
    keywords = BASE_KEYWORDS.copy()
    if plugin_name in PLUGIN_KEYWORDS:
        keywords.extend(PLUGIN_KEYWORDS[plugin_name])

    # Format keywords
    keywords_str = 'keywords = [\n'
    for kw in keywords:
        keywords_str += f'  "{kw}",\n'
    keywords_str += ']\n'

    # Insert after license line
    content = re.sub(
        r'(license\s*=\s*"[^"]+"\n)',
        r'\1' + keywords_str,
        content,
    )

    return content


def add_project_urls(content: str) -> str:
    """Add project.urls to pyproject.toml content if missing."""
    if '[project.urls]' in content:
        return content

    # Insert before [build-system]
    content = re.sub(
        r'(\[build-system\])',
        PROJECT_URLS.strip() + '\n\n' + r'\1',
        content,
    )

    return content


def fix_pyproject(pyproject_path: Path) -> bool:
    """Fix a single pyproject.toml file."""
    plugin_name = get_plugin_name(pyproject_path)
    content = pyproject_path.read_text()
    original_content = content

    content = add_keywords(content, plugin_name)
    content = add_project_urls(content)

    if content != original_content:
        pyproject_path.write_text(content)
        return True
    return False


def main() -> None:
    """Fix all plugin pyproject.toml files."""
    py_dir = Path(__file__).parent.parent
    plugins_dir = py_dir / 'plugins'

    updated = 0
    for pyproject_path in plugins_dir.glob('*/pyproject.toml'):
        if fix_pyproject(pyproject_path):
            updated += 1

    # Also fix core package
    core_pyproject = py_dir / 'packages' / 'genkit' / 'pyproject.toml'
    if core_pyproject.exists():
        content = core_pyproject.read_text()
        if '[project.urls]' not in content:
            content = add_project_urls(content)
            # Add keywords for core package
            if 'keywords' not in content:
                keywords = [*BASE_KEYWORDS, 'framework', 'sdk']
                keywords_str = 'keywords = [\n'
                for kw in keywords:
                    keywords_str += f'  "{kw}",\n'
                keywords_str += ']\n'
                content = re.sub(
                    r'(license\s*=\s*"[^"]+"\n)',
                    r'\1' + keywords_str,
                    content,
                )
            core_pyproject.write_text(content)
            updated += 1


if __name__ == '__main__':
    main()
