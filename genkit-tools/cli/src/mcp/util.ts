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

/** Genkit Runtime manager specifically for the MCP server. Allows lazy
 * initialization and dev process manangement. */
export class McpRuntimeManager {
  private manager: RuntimeManager | undefined;

  constructor(private projectRoot: string) {}

  async getManager() {
    if (!this.manager) {
      this.manager = await startManager(
        this.projectRoot,
        true /* manageHealth */
      );
    }
    return this.manager;
  }

  async getManagerWithDevProcess(command: string, args: string[]) {
    if (this.manager) {
      await this.manager.stop();
    }
    const devManager = await startDevProcessManager(
      this.projectRoot,
      command,
      args
    );
    this.manager = devManager.manager;
    return this.manager;
  }

  async kill() {
    if (this.manager) {
      await this.manager.stop();
    }
  }
}
