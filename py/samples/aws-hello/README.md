# AWS Telemetry Demo

This sample demonstrates how to export telemetry (traces) from Genkit to AWS X-Ray
using the AWS plugin.

## Prerequisites

1. **AWS Credentials**: Configure via environment variables, credentials file, or IAM role
2. **AWS Region**: Set `AWS_REGION` environment variable
3. **IAM Permissions**: Attach `AWSXrayWriteOnlyPolicy` to your role/user
4. **Google AI API Key**: Set `GOOGLE_GENAI_API_KEY` (or use any other model provider)

## Quick Start

```bash
# Set required environment variables
export AWS_REGION=us-west-2
export GOOGLE_GENAI_API_KEY=your-api-key

# Run the demo
./run.sh
```

## Viewing Traces

1. Open the Dev UI (typically at http://localhost:4000)
2. Run the `hello_world` or `multi_step_demo` flow
3. View traces in AWS X-Ray Console:
   https://console.aws.amazon.com/xray/home

Traces typically appear within 1-2 minutes.

## Flows

### `hello_world`

A simple flow that generates text. Demonstrates basic tracing.

### `multi_step_demo`

A multi-step flow with nested model calls. Shows how nested operations
appear as child spans in X-Ray.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_REGION` | Yes | AWS region for X-Ray endpoint |
| `AWS_ACCESS_KEY_ID` | No* | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | No* | AWS secret key |
| `AWS_PROFILE` | No* | AWS profile from credentials file |
| `GOOGLE_GENAI_API_KEY` | Yes | Google AI API key |

*At least one form of AWS credentials is required.

## IAM Policy

Ensure your IAM role/user has the `AWSXrayWriteOnlyPolicy` managed policy, or:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords"
            ],
            "Resource": "*"
        }
    ]
}
```

## Documentation

- [AWS X-Ray](https://docs.aws.amazon.com/xray/)
- [Genkit Observability](https://genkit.dev/docs/observability)
