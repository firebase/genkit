# Azure Telemetry Hello Sample

This sample demonstrates Azure Application Insights telemetry integration with Genkit.

## Prerequisites

1. An Azure account with Application Insights resource
2. Your Application Insights connection string

## Setup

### 1. Get your Application Insights connection string

From the Azure Portal:
1. Go to your Application Insights resource
2. Click on "Overview" 
3. Copy the "Connection String"

### 2. Set environment variables

```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=..."
export GOOGLE_GENAI_API_KEY="your-google-ai-key"
```

## Running the Sample

```bash
# From the sample directory
./run.sh
```

## Testing with the DevUI

1. Open http://localhost:4000 in your browser
2. Navigate to the "say_hello" flow
3. Enter a name and run the flow
4. View traces in Azure Portal → Application Insights → Transaction search

## What This Sample Demonstrates

- Azure Application Insights trace export
- PII redaction for model inputs/outputs
- Trace correlation in Application Insights
- Integration with Genkit flows
