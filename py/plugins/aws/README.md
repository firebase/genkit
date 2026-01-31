# Genkit AWS Plugin

AWS observability integration for Genkit, enabling telemetry export to AWS X-Ray
(distributed tracing) and CloudWatch (metrics/logs).

## Installation

```bash
pip install genkit-plugin-aws
```

## Quick Start

```python
from genkit.plugins.aws import add_aws_telemetry

# Enable AWS X-Ray telemetry (uses AWS_REGION env var)
add_aws_telemetry()

# Or with explicit region
add_aws_telemetry(region='us-west-2')
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | AWS region for X-Ray endpoint (required) |
| `AWS_DEFAULT_REGION` | Fallback region if `AWS_REGION` not set |
| `AWS_ACCESS_KEY_ID` | AWS access key (or use IAM role) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (or use IAM role) |

### Options

```python
add_aws_telemetry(
    region='us-west-2',          # AWS region (or use AWS_REGION env var)
    log_input_and_output=False,  # Set True to disable PII redaction
    force_dev_export=True,       # Export even in dev environment
    disable_traces=False,        # Set True to disable tracing
)
```

## IAM Permissions

The following IAM permissions are required:

### For Traces (X-Ray)

Attach the `AWSXrayWriteOnlyPolicy` managed policy, or create a custom policy:

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

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AWS Plugin                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  Plugin Entry Point (__init__.py)                                       │
│  └── add_aws_telemetry() - Enable X-Ray/CloudWatch export               │
├─────────────────────────────────────────────────────────────────────────┤
│  telemetry/tracing.py - Distributed Tracing                             │
│  ├── AWS X-Ray OTLP exporter configuration                              │
│  ├── SigV4 authentication for AWS endpoints                             │
│  ├── AwsXRayIdGenerator for X-Ray-compatible trace IDs                  │
│  └── OpenTelemetry integration                                          │
└─────────────────────────────────────────────────────────────────────────┘

Data Flow:
┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐
│ Genkit App   │───►│ OpenTelemetry│───►│ AWS Observability    │
│ (actions,    │    │ SDK + ADOT   │    │ (X-Ray, CloudWatch)  │
│  flows)      │    └──────────────┘    └──────────────────────┘
└──────────────┘
```

## AWS Documentation

- [AWS X-Ray](https://docs.aws.amazon.com/xray/)
- [CloudWatch OTLP Endpoints](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OTLPEndpoint.html)
- [ADOT Python Getting Started](https://aws-otel.github.io/docs/getting-started/python-sdk)

## License

Apache-2.0
