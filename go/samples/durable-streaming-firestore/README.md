# Durable Streaming with Firestore

This sample demonstrates durable streaming using Firestore as the backend. Unlike in-memory streaming, Firestore-backed streams:

- **Survive server restarts** - Clients can reconnect to streams after server restarts
- **Work across instances** - Multiple server instances can serve the same stream
- **Auto-cleanup** - Completed streams are automatically deleted via Firestore TTL policies

## Prerequisites

1. **Firebase Project**: You need a Firebase/GCP project with Firestore enabled.

2. **Authentication**: Authenticate with your Google Cloud project:
   ```bash
   gcloud auth application-default login
   ```

3. **(Recommended) TTL Policy**: Configure a TTL policy on your Firestore collection for automatic cleanup of old streams. This requires setting a TTL on the `expiresAt` field:
   
   ```bash
   gcloud firestore fields ttls update expiresAt \
     --collection-group=genkit-streams \
     --enable-ttl \
     --project=YOUR_PROJECT_ID
   ```
   
   See: https://firebase.google.com/docs/firestore/ttl

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FIREBASE_PROJECT_ID` | Yes | - | Your Firebase/GCP project ID |
| `FIRESTORE_STREAMS_COLLECTION` | No | `genkit-streams` | Firestore collection for stream documents |

## Running the Sample

1. Set your project ID:
   ```bash
   export FIREBASE_PROJECT_ID=your-project-id
   ```

2. Start the server:
   ```bash
   go run .
   ```

## Testing

### Start a streaming request

```bash
curl -N -i -H "Accept: text/event-stream" \
     -d '{"data": 5}' \
     http://localhost:8080/countdown
```

Note the `X-Genkit-Stream-Id` header in the response - you'll need this to reconnect.

### Reconnect to an existing stream

Use the stream ID from the previous response:

```bash
curl -N -H "Accept: text/event-stream" \
     -H "X-Genkit-Stream-Id: <stream-id-from-above>" \
     -d '{"data": 5}' \
     http://localhost:8080/countdown
```

The subscription will:
- Replay any buffered chunks that were already sent
- Continue with live updates if the stream is still in progress
- Return all chunks plus the final result if the stream has already completed

### Test server restart resilience

1. Start a countdown with a high number:
   ```bash
   curl -N -i -H "Accept: text/event-stream" -d '{"data": 30}' http://localhost:8080/countdown
   ```

2. Copy the `X-Genkit-Stream-Id` header value

3. Stop the server (Ctrl+C)

4. Restart the server: `go run .`

5. Reconnect using the stream ID:
   ```bash
   curl -N -H "Accept: text/event-stream" -H "X-Genkit-Stream-Id: <id>" -d '{"data": 30}' http://localhost:8080/countdown
   ```

You'll receive all previously buffered chunks, demonstrating that the stream state persisted across the server restart.

## Configuration Options

The `FirestoreStreamManager` supports these options:

| Option | Default | Description |
|--------|---------|-------------|
| `WithCollection(name)` | (required) | Firestore collection for stream documents |
| `WithTimeout(duration)` | 60s | How long subscribers wait for new events before timeout |
| `WithTTL(duration)` | 5m | How long completed streams are retained before auto-deletion |

Example:
```go
streamManager, err := firebasex.NewFirestoreStreamManager(ctx, g,
    firebasex.WithCollection("my-streams"),
    firebasex.WithTimeout(2*time.Minute),
    firebasex.WithTTL(1*time.Hour),
)
```

## How It Works

1. When a streaming request arrives, a Firestore document is created with the stream ID
2. As the flow produces chunks, they're appended to the document's `stream` array
3. Subscribers use Firestore's real-time listeners to receive updates
4. When the flow completes, a final "done" entry is added with the output
5. The `expiresAt` field is set based on TTL, and Firestore automatically deletes the document

## License

```
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

