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
  --collection-group=<COLLECTION-NAME> \
  --query-scope=COLLECTION \
  --field-config=vector-config='{"dimension":"3","flat": "{}"}',field-path=<VECTOR-FIELD>
```
## Run the sample

TODO

```bash
genkit start -- uv run --directory py samples/firestore-retreiver/src/main.py
```