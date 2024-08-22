#!/usr/bin/env node
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

import { spawnSync } from 'child_process';
import { join } from 'path';

// Resolve the path to the genkit.js file
const genkitPath = join(__dirname, 'genkit.js');

// Execute the genkit script with "init" as the argument
const result = spawnSync('node', [genkitPath, 'init'], { stdio: 'inherit' });

process.exit(result.status ?? 1);
