#!/bin/bash

# Check if generated Go code is up to date
cd go/core
go run ../internal/cmd/jsonschemagen -outdir .. -config schemas.config ../../genkit-tools/genkit-schema.json ai

# Check if git detects changes to the generated file
if git diff --quiet ../ai/gen.go; then
    exit 0
else
    echo "::error::Generated Go code is out of date. Please run:"
    echo "::error::cd go/core && go run ../internal/cmd/jsonschemagen -outdir .. -config schemas.config ../../genkit-tools/genkit-schema.json ai"
    exit 1
fi 