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

# Import all of the example prompts and flows to ensure they are registered
import case_01.prompts
import case_02.flows
import case_02.prompts
import case_02.tools
import case_03.flows
import case_03.prompts
import case_04.flows
import case_04.prompts
import case_05.flows
import case_05.prompts
from menu_ai import ai

if __name__ == '__main__':
    ai.run_main()
