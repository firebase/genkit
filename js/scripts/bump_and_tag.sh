#!/bin/bash

# this script lets you bump and tag a specifific package
# js/scripts/bump_and_tag.sh genkit-tools/cli genkit-cli prerelease rc

set -e
set -x

PACKAGE_PATH=$1
PACKAGE_NAME=$2
RELEASE_TYPE=$3
PREID="${4:-rc}"

# import bump_version script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. $SCRIPT_DIR/bump_version.sh

COMMIT_MSG="chore: $PACKAGE_NAME version bump$NEWLINE$NEWLINE"

bump_version $PACKAGE_PATH $PACKAGE_NAME

commit_and_tag