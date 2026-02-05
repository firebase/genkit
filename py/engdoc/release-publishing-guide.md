# Python SDK Release and Publishing Guide

This guide documents the complete process for releasing and publishing the Genkit Python SDK.

## Pre-Release Requirements

### 1. Version Verification

All packages must have the same version (`0.5.0` for this release):

```bash
# Check all package versions
grep "^version = " packages/*/pyproject.toml plugins/*/pyproject.toml | sort
```

### 2. Documentation Requirements

| Requirement | Location | Status |
|-------------|----------|--------|
| CHANGELOG.md updated | `py/CHANGELOG.md` | ✅ |
| PR description created | `py/.github/PR_DESCRIPTION_0.5.0.md` | ✅ |
| Blog article written | `py/engdoc/blog-genkit-python-0.5.0.md` | ✅ |
| Release validation passed | `./bin/validate_release_docs` | ✅ |

### 3. Code Quality Requirements

```bash
# All checks must pass
cd py && ./bin/lint           # Linting and type checks
cd py && uv run pytest .      # All tests pass
cd py && ./bin/validate_release_docs  # Release doc validation
```

### 4. PyPI Package Status

**Existing packages (update from v0.4.0 to v0.5.0):**
- genkit
- genkit-plugin-compat-oai
- genkit-plugin-dev-local-vectorstore
- genkit-plugin-firebase
- genkit-plugin-flask
- genkit-plugin-google-cloud
- genkit-plugin-google-genai
- genkit-plugin-ollama
- genkit-plugin-vertex-ai

**New packages (first publish at v0.5.0):**
- genkit-plugin-anthropic
- genkit-plugin-aws
- genkit-plugin-amazon-bedrock
- genkit-plugin-azure
- genkit-plugin-cf
- genkit-plugin-cloudflare-workers-ai
- genkit-plugin-deepseek
- genkit-plugin-evaluators
- genkit-plugin-huggingface
- genkit-plugin-mcp
- genkit-plugin-mistral
- genkit-plugin-msfoundry
- genkit-plugin-observability
- genkit-plugin-xai

### 5. GitHub Environment Configuration

Ensure the `pypi_github_publishing` environment is configured in GitHub repository settings with:
- PyPI trusted publishing enabled
- Required reviewers (if applicable)

## Release Process

### Step 1: Merge the Release PR

After PR approval:
```bash
# Merge the PR (use squash or merge commit as appropriate)
gh pr merge 4417 --squash
```

### Step 2: Create a GitHub Release

```bash
# Create and push a tag
git checkout main
git pull origin main
git tag -a py/v0.5.0 -m "Genkit Python SDK v0.5.0"
git push origin py/v0.5.0
```

Then create a GitHub release:
1. Go to https://github.com/firebase/genkit/releases/new
2. Select tag: `py/v0.5.0`
3. Title: `Genkit Python SDK v0.5.0`
4. Copy release notes from `py/CHANGELOG.md`
5. Publish release

### Step 3: Publish to PyPI

1. Go to **Actions** → **Publish Python Package**
2. Click **Run workflow**
3. Select:
   - `publish_scope: all` (to publish all 23 packages)
4. Click **Run workflow**
5. Monitor the workflow - it will build and publish all packages in parallel

### Step 4: Verify Publication

After workflow completes:
```bash
# Verify packages on PyPI
for pkg in genkit genkit-plugin-google-genai genkit-plugin-anthropic; do
  pip index versions $pkg | head -1
done
```

Or check on PyPI directly:
- https://pypi.org/project/genkit/
- https://pypi.org/project/genkit-plugin-google-genai/

### Step 5: Post-Release Verification

```bash
# Test installation in a fresh environment
python -m venv /tmp/genkit-test
source /tmp/genkit-test/bin/activate
pip install genkit genkit-plugin-google-genai
python -c "from genkit.ai import Genkit; print('Success!')"
```

## Troubleshooting

### Package Already Exists at This Version

If a package was partially published:
```bash
# Check the version on PyPI
curl -s "https://pypi.org/pypi/genkit/json" | jq -r '.info.version'
```

You cannot re-upload the same version. Either:
1. Bump the version (e.g., 0.5.1)
2. Delete the release on PyPI (only within 24 hours)

### Trusted Publishing Fails

Ensure the GitHub environment `pypi_github_publishing` is configured with:
1. Go to repository Settings → Environments
2. Create/edit `pypi_github_publishing`
3. Configure trusted publisher on PyPI for each package

### Individual Package Publish

To publish a single package:
1. Go to **Actions** → **Publish Python Package**
2. Select `publish_scope: single`
3. Select `project_type: plugins` (or `packages` for genkit core)
4. Select the specific `project_name`

## Package Installation Reference

After release, users install packages with:

```bash
# Core package (required)
pip install genkit

# Model providers
pip install genkit-plugin-google-genai    # Google AI (Gemini)
pip install genkit-plugin-anthropic       # Anthropic (Claude)
pip install genkit-plugin-ollama          # Ollama (local models)
pip install genkit-plugin-vertex-ai       # Vertex AI
pip install genkit-plugin-amazon-bedrock     # AWS Bedrock
pip install genkit-plugin-mistral         # Mistral AI
pip install genkit-plugin-deepseek        # DeepSeek
pip install genkit-plugin-xai             # xAI (Grok)
pip install genkit-plugin-huggingface     # Hugging Face
pip install genkit-plugin-cloudflare-workers-ai           # Cloudflare Workers AI
pip install genkit-plugin-msfoundry       # Azure OpenAI

# Telemetry
pip install genkit-plugin-google-cloud    # GCP Cloud Trace
pip install genkit-plugin-aws             # AWS X-Ray
pip install genkit-plugin-observability   # Sentry, Honeycomb, Datadog

# Other
pip install genkit-plugin-firebase        # Firebase/Firestore
pip install genkit-plugin-evaluators      # Evaluation metrics
pip install genkit-plugin-flask           # Flask integration
pip install genkit-plugin-compat-oai      # OpenAI compatibility
pip install genkit-plugin-mcp             # Model Context Protocol
```
