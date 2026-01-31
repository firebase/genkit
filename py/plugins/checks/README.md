# Genkit Checks Plugin

Google Checks AI Safety plugin for Genkit - provides guardrails and content
safety evaluation for AI-generated content.

## Overview

The Checks plugin integrates with the
[Google Checks AI Safety API](https://developers.google.com/checks) to provide:

- **Content Safety Evaluation**: Evaluate AI outputs against safety policies
- **Model Middleware**: Block unsafe content automatically during generation
- **Configurable Policies**: Choose which safety policies to enforce

## Installation

```bash
pip install genkit-plugin-checks
```

## Quick Start

```python
from genkit.ai import Genkit
from genkit.plugins.checks import Checks, ChecksMetricType

# Initialize Genkit with the Checks plugin
ai = Genkit(plugins=[
    Checks(
        project_id='your-gcp-project',
        evaluation={
            'metrics': [
                ChecksMetricType.DANGEROUS_CONTENT,
                ChecksMetricType.HARASSMENT,
                ChecksMetricType.HATE_SPEECH,
            ]
        }
    )
])

# Use as middleware to automatically block unsafe content
response = await ai.generate(
    model='googleai/gemini-2.0-flash',
    prompt='Tell me about AI safety',
    use=[checks_middleware(metrics=[ChecksMetricType.DANGEROUS_CONTENT])],
)
```

## Supported Metrics

| Metric | Description |
|--------|-------------|
| `DANGEROUS_CONTENT` | Harmful goods, services, or activities |
| `PII_SOLICITING_RECITING` | Personal information disclosure |
| `HARASSMENT` | Malicious, intimidating, or abusive content |
| `SEXUALLY_EXPLICIT` | Sexually explicit content |
| `HATE_SPEECH` | Violence, hatred, or discrimination |
| `MEDICAL_INFO` | Harmful health advice |
| `VIOLENCE_AND_GORE` | Gratuitous violence or gore |
| `OBSCENITY_AND_PROFANITY` | Vulgar or offensive language |

## Configuration

### Plugin Options

```python
Checks(
    # GCP project with Checks API quota
    project_id='your-gcp-project',

    # Optional: Custom Google Auth configuration
    google_auth_options={'credentials_file': '/path/to/creds.json'},

    # Configure evaluation metrics
    evaluation={
        'metrics': [
            ChecksMetricType.DANGEROUS_CONTENT,
            # Or with custom threshold
            {'type': ChecksMetricType.HARASSMENT, 'threshold': 0.8},
        ]
    }
)
```

### Middleware Usage

```python
from genkit.plugins.checks import checks_middleware, ChecksMetricType

# Apply middleware to specific generations
response = await ai.generate(
    model='googleai/gemini-2.0-flash',
    prompt='Your prompt',
    use=[
        checks_middleware(
            metrics=[
                ChecksMetricType.DANGEROUS_CONTENT,
                ChecksMetricType.HATE_SPEECH,
            ],
            auth_options={'project_id': 'your-project'},
        )
    ],
)
```

## Authentication

The plugin uses Google Cloud authentication. Set up credentials via:

1. **Environment variable**: `GOOGLE_APPLICATION_CREDENTIALS`
2. **Service account JSON**: `GCLOUD_SERVICE_ACCOUNT_CREDS` environment variable
3. **Default credentials**: Automatic in GCP environments

## Requirements

- Python 3.12+
- Google Cloud project with Checks API enabled
- Appropriate IAM permissions for Checks API

## Cross-Language Parity

This plugin maintains API parity with the JavaScript Genkit Checks plugin:
- JS: `@genkit-ai/checks`

## License

Apache 2.0 - See LICENSE file
