# Flask hello example

## Setup environment

Use `gcloud auth application-default login` to connect to the VertexAI.

## Run the sample

TODO

```bash
genkit start -- uv run flask --app src/flask_hello.py run
```

```bash
curl -X POST http://127.0.0.1:5000/chat -d '{"data": "banana"}' -H 'content-Type: application/json' -H 'accept: text/event-stream' -H 'Authorization: Pavel'
```
