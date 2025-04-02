# Flask hello example

## Setup environment

Use `gcloud auth application-default login` to connect to the VertexAI.

```bash
uv venv
source .venv/bin/activate
```

## Run the sample

TODO

```bash
genkit start -- flask --app src/hello_flask.py run
```

```bash
curl -X POST http://127.0.0.1:5000/chat -d '{"data": "banana"}' -H 'content-Type: application/json' -H 'accept: text/event-stream' -H 'Authorization: Pavel'
```