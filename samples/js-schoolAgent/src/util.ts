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

import { Tool } from 'genkit';

export const agentDescription = (specialization: string, tools: Tool[]) => `
Transfer to this agent when the user asks about ${specialization}. 
This agent can perform the following functions: ${tools.map((t) => t.name).join(', ')}.
Do not mention that you are transferring, just do it.`;

export const agentPrompt = (specialization: string) => `
You are Bell, a helpful attendance assistance agent for Sparkyville High School. 
A parent has been referred to you to handle a ${specialization}-related concern. 
Use the tools available to you to assist the parent.`;
