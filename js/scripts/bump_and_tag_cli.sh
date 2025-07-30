#!/bin/bash
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

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
