# Firebase Telemetry Setup Guide for Genkit Go

This demo showcases Firebase AI Monitoring capabilities that you can leverage with a 1-line code snippet:

```go
import "github.com/firebase/genkit/go/plugins/firebase"

g, err := genkit.Init(ctx, genkit.WithPlugins(
    firebase.FirebaseTelemetry(), // 🔥 Zero-config telemetry!
    &googlegenai.GoogleAI{},
))
```

This demo showcases an HTTP server already instrumented with Firebase Telemetry.

## Prerequisites
- Go 1.24+ installed
- Firebase project with Google Cloud APIs enabled
- Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

## Step 1: Set Environment Variables

```bash
# Set your Firebase project ID (replace with your actual project)
export FIREBASE_PROJECT_ID="PROJECT_ID"

# Set your real Gemini API key (replace with your actual key)
export GEMINI_API_KEY="GEMINI_API_KEY"

# Enable Firebase monitoring
export ENABLE_FIREBASE_MONITORING=true

# Set to production mode for simpler API
export GENKIT_ENV=prod
```

## Step 2: Run Simple Demo

```bash
# Navigate to simple demo
cd simple

# Start the simple joke flow server
go run simple_joke.go

# Wait for startup (you should see):
# - "Firebase monitoring enabled"
# - "Telemetry modules initialized modules=5"
# - "Server starting on http://127.0.0.1:3400"
```

## Step 3: Test the API

```bash
# Test with different topics
curl -X POST http://localhost:3400/jokeFlow \
  -H 'Content-Type: application/json' \
  -d '{"data": "cats"}'

curl -X POST http://localhost:3400/jokeFlow \
  -H 'Content-Type: application/json' \
  -d '{"data": "programming"}'
```

## Step 4: Run Kitchen Sink Demo

```bash
# Stop the simple server
pkill -f simple_joke

# Navigate to kitchen sink demo
cd ../kitchen_sink

# Start the kitchen sink demo
go run kitchen_sink.go

# This provides various telemetry scenarios:
# - Multimodal image analysis (imageFlow)
# - Tool calls and web search (textFlow)
# - Batch processing flows (batchFlow)
```

## Step 5: Test Kitchen Sink APIs

```bash
# Test image analysis (multimodal AI) 🖼️
curl -X POST http://localhost:3400/imageFlow \
  -H 'Content-Type: application/json' \
  -d '{"data": {"imageUrl": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png", "prompt": "What company logo is this?"}}'

# Expected response: Detailed analysis of the Google logo with colors and structure

# Test text with tools (web search) 💬
curl -X POST http://localhost:3400/textFlow \
  -H 'Content-Type: application/json' \
  -d '{"data": "machine learning"}'

# Test batch processing 📦
curl -X POST http://localhost:3400/batchFlow \
  -H 'Content-Type: application/json' \
  -d '{"data": ["AI", "robotics", "quantum"]}'
```

## Step 6: Verify in Google Cloud Console

**✅ What Works:**
- **Cloud Trace** - Shows actual request traces and spans
- **Cloud Logging** - Shows telemetry processing logs (working!)
- **Cloud Monitoring** - Shows aggregated metrics  
- **Local Logs** - Application logs also appear in terminal

### Cloud Trace
1. Go to [Cloud Trace](https://console.cloud.google.com/traces/list?project=PROJECT_ID)
2. Look for traces with names like:
   - `jokeFlow` (simple joke flow)
   - `imageFlow` (multimodal image analysis)
   - `textFlow` (AI with tool calls)
   - `batchFlow` (batch processing multiple topics)

### Cloud Logging  
1. Go to [Cloud Logging](https://console.cloud.google.com/logs/query?project=PROJECT_ID)
2. Use these working queries based on the actual log structure:

```
# All telemetry processing logs
jsonPayload.msg:"Telemetry.Tick"

# Generate telemetry specifically
jsonPayload.msg:"GenerateTelemetry.Tick"

# Feature telemetry specifically  
jsonPayload.msg:"FeatureTelemetry.Tick"

# Spans being processed (not skipped)
jsonPayload.msg:"Processing span"

# Spans being skipped (normal behavior)
jsonPayload.msg:"Skipping span"

# See spans with genkit names
jsonPayload."genkit:name"!=""

# All Genkit-related logs
jsonPayload.msg:"Telemetry"
```

### Cloud Monitoring
1. Go to [Cloud Monitoring](https://console.cloud.google.com/monitoring?project=PROJECT_ID)
2. Look for metrics starting with `genkit/`:
   - `genkit/feature/requests`
   - `genkit/generate/requests`
   - `genkit/action/requests`

## What You Should See

After running both demos, you should see:

1. **Complete request traces** showing flow → AI generation → tool calls
2. **Structured logs** with Genkit metadata
3. **Real-time metrics** for all operations