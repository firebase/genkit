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
- genkit-plugin-cloudflare-workers-ai
- genkit-plugin-deepseek
- genkit-plugin-evaluators
- genkit-plugin-huggingface
- genkit-plugin-mcp
- genkit-plugin-mistral
- genkit-plugin-microsoft-foundry
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
   - `publish_scope: all` (to publish all 21 packages)
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

**Via GitHub UI:**
1. Go to **Actions** → **Publish Python Package**
2. Select `publish_scope: single`
3. Select `project_type: plugins` (or `packages` for genkit core)
4. Select the specific `project_name`

**Via CLI:**
```bash
# Publish all packages
gh workflow run publish_python.yml -f publish_scope=all

# Publish just the core genkit package
gh workflow run publish_python.yml \
  -f publish_scope=single \
  -f project_type=packages \
  -f project_name=genkit

# Publish a specific plugin (3 parameters required)
gh workflow run publish_python.yml \
  -f publish_scope=single \
  -f project_type=plugins \
  -f project_name=anthropic

gh workflow run publish_python.yml \
  -f publish_scope=single \
  -f project_type=plugins \
  -f project_name=google-genai

gh workflow run publish_python.yml \
  -f publish_scope=single \
  -f project_type=plugins \
  -f project_name=vertex-ai
```

### Available Plugin Names for project_name

| Plugin Name | PyPI Package Name |
|-------------|-------------------|
| `anthropic` | genkit-plugin-anthropic |
| `aws` | genkit-plugin-aws |
| `amazon-bedrock` | genkit-plugin-amazon-bedrock |
| `azure` | genkit-plugin-azure |
| `cloudflare-workers-ai` | genkit-plugin-cloudflare-workers-ai |
| `compat-oai` | genkit-plugin-compat-oai |
| `deepseek` | genkit-plugin-deepseek |
| `dev-local-vectorstore` | genkit-plugin-dev-local-vectorstore |
| `evaluators` | genkit-plugin-evaluators |
| `firebase` | genkit-plugin-firebase |
| `flask` | genkit-plugin-flask |
| `google-cloud` | genkit-plugin-google-cloud |
| `google-genai` | genkit-plugin-google-genai |
| `huggingface` | genkit-plugin-huggingface |
| `mcp` | genkit-plugin-mcp |
| `mistral` | genkit-plugin-mistral |
| `microsoft-foundry` | genkit-plugin-microsoft-foundry |
| `observability` | genkit-plugin-observability |
| `ollama` | genkit-plugin-ollama |
| `vertex-ai` | genkit-plugin-vertex-ai |
| `xai` | genkit-plugin-xai |

### Monitoring Workflow Progress

```bash
# List recent publish workflow runs
gh run list --workflow=publish_python.yml --limit=5

# Watch a specific run in real-time
gh run watch <RUN_ID>

# View detailed job status
gh run view <RUN_ID> --json status,conclusion,jobs

# View failed job logs
gh run view <RUN_ID> --log-failed | head -100
```

### Retrying Failed Jobs

```bash
# Re-run all failed jobs from a specific run
gh run rerun <RUN_ID> --failed

# Or trigger a fresh workflow run
gh workflow run publish_python.yml -f publish_scope=<plugin-name>
```

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
pip install genkit-plugin-amazon-bedrock  # AWS Bedrock
pip install genkit-plugin-mistral         # Mistral AI
pip install genkit-plugin-deepseek        # DeepSeek
pip install genkit-plugin-xai             # xAI (Grok)
pip install genkit-plugin-huggingface     # Hugging Face
pip install genkit-plugin-cloudflare-workers-ai  # Cloudflare Workers AI + OTLP telemetry
pip install genkit-plugin-microsoft-foundry       # Azure AI Foundry

# Telemetry
pip install genkit-plugin-google-cloud    # GCP Cloud Trace
pip install genkit-plugin-aws             # AWS X-Ray
pip install genkit-plugin-azure           # Azure Application Insights
pip install genkit-plugin-observability   # Sentry, Honeycomb, Datadog

# Other
pip install genkit-plugin-firebase        # Firebase/Firestore
pip install genkit-plugin-evaluators      # Evaluation metrics
pip install genkit-plugin-flask           # Flask integration
pip install genkit-plugin-compat-oai      # OpenAI compatibility
pip install genkit-plugin-mcp             # Model Context Protocol
```

## Troubleshooting

### PyPI 500 Error: Trusted Publishing Exchange Failure

**Error:** `Trusted publishing exchange failure: Token request failed: the index produced an unexpected 500 response.`

**Cause:** This is a transient PyPI server error, not a configuration issue.

**Solution:**
1. Check PyPI status: https://status.python.org/
2. Wait 5-10 minutes
3. Retry the failed jobs:
   ```bash
   gh run rerun <RUN_ID> --failed
   ```

### PyPI 400 Error: Non-user Identities Cannot Create New Projects

**Error:** `400 Non-user identities cannot create new projects. This was probably caused by successfully using a pending publisher but specifying the project name incorrectly.`

**Cause:** The package doesn't exist on PyPI yet and needs Trusted Publisher setup.

**Solution for new packages:**
1. Go to https://pypi.org/manage/account/publishing/
2. Add a **Pending Publisher** for each new package:
   - **PyPI Project Name:** `genkit-plugin-<name>` (exact package name from pyproject.toml)
   - **Owner:** `firebase`
   - **Repository:** `genkit`
   - **Workflow name:** `publish_python.yml`
   - **Environment:** `pypi`
3. Retry the workflow

### Package Already Exists at This Version

**Error:** `File already exists`

**Cause:** The exact version was already uploaded to PyPI.

**Solution:**
- You cannot re-upload the same version to PyPI
- Either bump the version (e.g., 0.5.1) or verify the existing package is correct
- Use `--skip-existing` flag if publishing multiple packages and some already exist

### Authentication Failure

**Error:** `403 Forbidden` or `401 Unauthorized`

**Cause:** OIDC token exchange failed between GitHub and PyPI.

**Solution:**
1. Verify the GitHub environment `pypi` exists in repository settings
2. Verify Trusted Publisher is configured correctly on PyPI
3. Ensure workflow file path matches PyPI configuration exactly

### Manual Fallback: API Token Upload

If Trusted Publishing continues to fail:

```bash
cd py

# Build the package
uv build --package genkit-plugin-<name>

# Upload with API token (get token from https://pypi.org/manage/account/token/)
TWINE_USERNAME=__token__ TWINE_PASSWORD=<your-token> twine upload dist/*
```

**Note:** This is a fallback for emergencies. Prefer Trusted Publishing for security.
