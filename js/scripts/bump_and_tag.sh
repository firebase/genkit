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
