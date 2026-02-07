# Sample Test Utilities

Internal testing utilities for Genkit samples. These scripts help developers
verify that sample flows are working correctly.

## Scripts

### `review_sample_flows.py`

Reviews and tests all flows in a sample's `main.py`.

```bash
# Test all flows in a sample
cd py
uv run samples/sample-test/review_sample_flows.py samples/provider-google-genai-hello

# Specify custom output file
uv run samples/sample-test/review_sample_flows.py samples/provider-google-genai-hello --output results.txt
```

### `run_single_flow.py`

Runs a single flow from a sample. Used internally by `review_sample_flows.py`.

```bash
cd py
uv run samples/sample-test/run_single_flow.py samples/provider-google-genai-hello flow_name --input '{"key": "value"}'
```

## Output

The review script generates a report file with:
- Summary of successful/failed flows
- Detailed input/output for each flow
- Error messages and tracebacks for failures
