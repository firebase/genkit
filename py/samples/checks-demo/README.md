# Google Checks AI Safety Demo

This sample demonstrates how to use the **Google Checks** AI safety plugin for
content moderation in Genkit applications.

## What is Google Checks?

[Google Checks](https://checks.google.com/ai-safety) is an AI safety platform
that provides:

- **Guardrails API**: Real-time content classification for policy violations
- **Automated Adversarial Testing**: Offline evaluation of your model's safety

> **Note**: The Guardrails API is currently in private preview. To request quota,
> fill out [this form](https://docs.google.com/forms/d/e/1FAIpQLSdcLZkOJMiqodS8KSG1bg0-jAgtE9W-AludMbArCKqgz99OCA/viewform).

## Supported Policies

| Policy | Description |
|--------|-------------|
| `DANGEROUS_CONTENT` | Content that could cause real-world harm |
| `PII_SOLICITING_RECITING` | Personally identifiable information |
| `HARASSMENT` | Bullying or abusive content |
| `SEXUALLY_EXPLICIT` | Adult or sexual content |
| `HATE_SPEECH` | Content targeting protected groups |
| `MEDICAL_INFO` | Medical advice or diagnoses |
| `VIOLENCE_AND_GORE` | Violent or graphic content |
| `OBSCENITY_AND_PROFANITY` | Vulgar language |

## Features Demonstrated

1. **Middleware Usage**: Apply Checks as middleware in `ai.generate()` calls
2. **Evaluator Configuration**: Set up Checks evaluators for offline testing
3. **Custom Thresholds**: Fine-tune sensitivity per policy

## Prerequisites

1. **Google Cloud Project** with Checks API quota
2. **API Key** for Google AI (Gemini models)
3. **Application Default Credentials** or service account for Checks API

```bash
# Set up credentials
export GEMINI_API_KEY="your-api-key"
export GCLOUD_PROJECT="your-project-id"

# Optional: Service account credentials
export GCLOUD_SERVICE_ACCOUNT_CREDS='{"type":"service_account",...}'
```

## Running the Demo

```bash
./run.sh
```

Then open the Dev UI at http://localhost:4000 and run the flows.

## Testing Safety Policies

1. **Benign Input**: "Write a poem about nature"
   - Should pass all safety checks

2. **Potentially Unsafe Input**: Test with edge cases to see how policies trigger
   - Adjust thresholds based on your application needs

## Tuning Thresholds

Lower thresholds = more restrictive (blocks more content)
Higher thresholds = more permissive (allows more content)

```python
# Very restrictive - blocks even slightly violent content
ChecksMetricConfig(type=ChecksMetricType.VIOLENCE_AND_GORE, threshold=0.01)

# Very permissive - only blocks clearly dangerous content
ChecksMetricConfig(type=ChecksMetricType.DANGEROUS_CONTENT, threshold=0.99)
```

## Related Documentation

- [Checks AI Safety](https://checks.google.com/ai-safety)
- [Genkit Documentation](https://genkit.dev/docs/)
- [JS Checks Plugin](../../js/plugins/checks/README.md)
