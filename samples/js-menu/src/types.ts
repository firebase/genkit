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

import * as z from 'zod';

// The data model for a restaurant menu

export const MenuItemSchema = z.object({
  title: z.string().describe('The name of the menu item'),
  description: z
    .string()
    .describe('Details including ingredients and preparation'),
  price: z.number().describe('Price in dollars'),
});

export type MenuItem = z.infer<typeof MenuItemSchema>;

// Input schema for a question about the menu

export const MenuQuestionInputSchema = z.object({
  question: z.string(),
});

// Output schema containing an answer to a question

export const AnswerOutputSchema = z.object({
  answer: z.string(),
});

// Input schema for a question about the menu
// where the menu is provided in JSON data.

export const DataMenuQuestionInputSchema = z.object({
  menuData: z.array(MenuItemSchema),
  question: z.string(),
});

// Input schema for a question about the menu
// where the menu is provided as unstructured text.

export const TextMenuQuestionInputSchema = z.object({
  menuText: z.string(),
  question: z.string(),
});

// Also export Typescript types for each of these Zod schemas
export type MenuQuestionInput = z.infer<typeof MenuQuestionInputSchema>;
export type AnswerOutput = z.infer<typeof AnswerOutputSchema>;
export type DataMenuPromptInput = z.infer<typeof DataMenuQuestionInputSchema>;
export type TextMenuQuestionInput = z.infer<typeof TextMenuQuestionInputSchema>;
