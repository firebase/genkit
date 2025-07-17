#!/bin/bash

# this script lets you bump and tag all JS packages (including plugins)
# js/scripts/bump_and_tag_cli.sh prerelease rc

set -e
set -x

RELEASE_TYPE=$1
PREID="${2:-rc}"

# import bump_version script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. $SCRIPT_DIR/bump_version.sh

COMMIT_MSG="chore: JS version bump$NEWLINE$NEWLINE"

# core packages
bump_version js/core @genkit-ai/core
bump_version js/ai @genkit-ai/ai
bump_version js/genkit genkit

# plugins
bump_version js/plugins/chroma genkitx-chromadb
bump_version js/plugins/dev-local-vectorstore @genkit-ai/dev-local-vectorstore
bump_version js/plugins/evaluators @genkit-ai/evaluator
bump_version js/plugins/firebase @genkit-ai/firebase
bump_version js/plugins/google-cloud @genkit-ai/google-cloud
bump_version js/plugins/googleai @genkit-ai/googleai
bump_version js/plugins/langchain genkitx-langchain
bump_version js/plugins/next @genkit-ai/next
bump_version js/plugins/ollama genkitx-ollama
bump_version js/plugins/pinecone genkitx-pinecone
bump_version js/plugins/vertexai @genkit-ai/vertexai
bump_version js/plugins/checks @genkit-ai/checks
bump_version js/plugins/mcp genkitx-mcp
bump_version js/plugins/express @genkit-ai/express
bump_version js/plugins/cloud-sql-pg genkitx-cloud-sql-pg

commit_and_tag
