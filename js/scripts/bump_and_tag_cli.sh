#!/bin/bash

# this script lets you bump and tag all CLI packages
# js/scripts/bump_and_tag_cli.sh prerelease rc

set -e
set -x

RELEASE_TYPE=$1
PREID="${2:-rc}"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# import bump_version script
. $SCRIPT_DIR/bump_version.sh

COMMIT_MSG="chore: CLI version bump$NEWLINE$NEWLINE"

bump_version genkit-tools/common @genkit-ai/tools-common
bump_version genkit-tools/telemetry-server @genkit-ai/tools-common
bump_version genkit-tools/cli genkit-cli

commit_and_tag