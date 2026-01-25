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

"""Entry point for the menu AI sample."""

# Import all of the example prompts and flows to ensure they are registered
import asyncio

# Import case modules to register flows and prompts with the ai instance
from .case_01 import prompts as case_01_prompts  # noqa: F401
from .case_02 import (
    flows as case_02_flows,  # noqa: F401
    prompts as case_02_prompts,  # noqa: F401
    tools as case_02_tools,  # noqa: F401
)
from .case_03 import (
    flows as case_03_flows,  # noqa: F401
    prompts as case_03_prompts,  # noqa: F401
)
from .case_04 import (
    flows as case_04_flows,  # noqa: F401
    prompts as case_04_prompts,  # noqa: F401
)
from .case_05 import (
    flows as case_05_flows,  # noqa: F401
    prompts as case_05_prompts,  # noqa: F401
)
from .menu_ai import ai

print('All prompts and flows loaded, use the Developer UI to test them out')


async def main():
    """Keep alive for Dev UI."""
    print('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
