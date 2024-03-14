/**
 * Copyright 2024 Google LLC
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

// Example.

import { Command } from 'commander';
import { logger } from '../utils/logger';

interface ExampleOptions {
  uppercase?: boolean;
}

/** Example command. Registered in cli.ts */
export const example = new Command('example')
  .option('-u, --uppercase', 'Uppercase the output', false)
  .action((options: ExampleOptions) => {
    const message = 'this is an example command';
    if (options.uppercase) {
      logger.warn(message.toUpperCase());
    } else {
      logger.info(message);
    }
  });
