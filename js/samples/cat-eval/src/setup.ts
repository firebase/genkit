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

import { flow, runFlow } from '@genkit-ai/flow';
import * as z from 'zod';
import { indexPdf } from './pdf_rag';

const catFacts = ['./docs/sfspca-cat-adoption-handbook-2023.pdf'];

// genkit flow:run setup
// genkit flow:run setup '[\"your_awesome_pdf.pdf\", \"your_other_awesome_pdf.pdf\""]'
export const setup = flow(
  {
    name: 'setup',
    input: z.array(z.string()).optional(),
    output: z.void(),
  },
  async (documentArr) => {
    if (!documentArr) {
      documentArr = catFacts;
    } else {
      documentArr.concat(catFacts);
    }

    await Promise.all(
      documentArr.map(async (document) => {
        console.log(`Indexed ${document}`);
        return runFlow(indexPdf, document);
      })
    );
  }
);
