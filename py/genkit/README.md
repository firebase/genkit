Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install --upgrade pip
python3.11 -m pip install -e ".[dev]"
```

Regen model objects

```bash
datamodel-codegen  --input ../../genkit-tools/genkit-schema.json --input-file-type jsonschema --output src/genkit/types.py --collapse-root-models
```
