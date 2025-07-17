#!/bin/bash

# this script lets you bump and tag all CLI packages
# js/scripts/bump_and_tag_cli.sh prerelease rc

set -e
set -x

RELEASE_TYPE=$1
PREID="${2:-rc}"

if [[ -z "$RELEASE_TYPE" ]]
then
  echo "release type (first arg) not set"
  exit 1
fi

# import bump_version script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. $SCRIPT_DIR/bump_version.sh

COMMIT_MSG="chore: CLI version bump$NEWLINE$NEWLINE"

bump_version genkit-tools/common @genkit-ai/tools-common tools-common-v
bump_version genkit-tools/telemetry-server @genkit-ai/telemetry-server telemetry-server-v
bump_version genkit-tools/cli genkit-cli

echo TAGS "${TAGS[*]}"

commit_and_tag
