#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# Generate Python gRPC stubs from the proto definition.
#
# Usage:
#   ./scripts/generate_proto.sh
#
# Generates into src/generated/:
#   genkit_sample_pb2.py       — Protobuf message classes
#   genkit_sample_pb2_grpc.py  — gRPC service stubs
#   genkit_sample_pb2.pyi      — Type stubs for editors

set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="src/generated"
mkdir -p "$OUT_DIR"

echo "Generating Python gRPC stubs from protos/genkit_sample.proto..."

uv run python -m grpc_tools.protoc \
  -I protos \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  --pyi_out="$OUT_DIR" \
  protos/genkit_sample.proto

# Fix the import path in the generated gRPC stub.
# protoc generates `import genkit_sample_pb2 as ...` but we need a relative import
# since the file lives inside the src.generated package.
if [[ "$(uname)" == "Darwin" ]]; then
  sed -i '' 's/^import genkit_sample_pb2 as/from . import genkit_sample_pb2 as/' \
    "$OUT_DIR/genkit_sample_pb2_grpc.py"
else
  sed -i 's/^import genkit_sample_pb2 as/from . import genkit_sample_pb2 as/' \
    "$OUT_DIR/genkit_sample_pb2_grpc.py"
fi

# Create __init__.py if it doesn't exist.
if [[ ! -f "$OUT_DIR/__init__.py" ]]; then
  cat > "$OUT_DIR/__init__.py" << 'PYEOF'
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Generated gRPC/protobuf stubs — do not edit by hand.

Regenerate with::

    ./scripts/generate_proto.sh
"""
PYEOF
fi

echo "Generated stubs in $OUT_DIR/:"
ls -la "$OUT_DIR/"
echo "Done."
