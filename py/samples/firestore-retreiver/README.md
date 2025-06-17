# Hello world

## Setup environment

```bash
uv venv
source .venv/bin/activate
```

## Create a index to be able to retrieve
```
gcloud firestore indexes composite create \
  --project=<FIREBASE-PROJECT>\
  --collection-group=films \
  --query-scope=COLLECTION \
  --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=embedding
```
## Run the sample

TODO

```bash
genkit start -- uv run --directory py samples/firestore-retreiver/src/main.py
```