/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { RuntimeManager } from '@genkit-ai/tools-common/manager';
import { startDevProcessManager, startManager } from '../utils/manager-utils';

/** Lazy loader for RuntimeManager to defer `.genkit/` creation. */
export function lazyLoadManager(projectRoot: string) {
  let manager: RuntimeManager | undefined;
  return {
    async getManager() {
      if (!manager) {
        manager = await startManager(projectRoot, true /* manageHealth */);
      }
      return manager;
    },
    async initManagerWithDevProcess(command: string, args: string[]) {
      if (manager) {
        await manager.processManager?.kill();
      }
      const devManager = await startDevProcessManager(
        projectRoot,
        command,
        args
      );
      manager = devManager.manager;
      return manager;
    },
  };
}
