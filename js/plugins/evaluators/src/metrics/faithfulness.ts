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

import { generate } from '@genkit-ai/ai';
import { BaseDataPoint, Score } from '@genkit-ai/ai/evaluator';
import { extractJson } from '@genkit-ai/ai/extract';
import { ModelArgument } from '@genkit-ai/ai/model';
import Handlebars from 'handlebars';
import * as z from 'zod';

const LONG_FORM_ANSWER_PROMPT = `Create one or more statements from each sentence in the given answer. 
Here are some examples:

question: 
Who was  Albert Einstein and what is he best known for?
answer: 
He was a German-born theoretical physicist, widely acknowledged to be one of the greatest and most influential physicists of all time. He was best known for developing the theory of relativity, he also made important contributions to the development of the theory of quantum mechanics.
statements in json:
{
  "statements": [
    "Albert Einstein, a German-born theoretical physicist, is renowned for being one of the most influential physicists in history.",
    "Albert Einstein was best known for his theory of relativity.",
    "Einstein's contributions significantly advanced the field of quantum mechanics",
    "Recognized globally, Einstein's work has profoundly impacted the scientific community",
    "Einstein's groundbreaking theories continue to shape our understanding of physics today.",
  ]
}

question: 
Cadmium Chloride is slightly soluble in this chemical, it is also called what?
answer: 
alcohol
statements in json:
{
  "statements": [
      "Cadmium Chloride is slightly soluble in alcohol."
  ]
}

question: 
Were Hitler and Benito Mussolini of the same nationality?
answer: 
Sorry, I can't provide answer to that question.
statements in json:
{
  "statements": []
}

Now provide your analysis for the following inputs. DO NOT PROVIDE ANY MORE EXAMPLES. Your response must be a valid JSON like you see above.

question:
{{question}}
answer: 
{{answer}}
statements in json:
`;

const NLI_STATEMENTS_MESSAGE = `Your task is to judge the faithfulness of a series of statements based on a given context. For each statement you must return verdict as 1 if the statement can be verified based on the context or 0 if the statement can not be verified based on the context.
Here are some examples:

Context:
John is a student at XYZ University. He is pursuing a degree in Computer Science. He is enrolled in several courses this semester, including Data Structures, Algorithms, and Database Management. John is a diligent student and spends a significant amount of time studying and completing assignments. He often stays late in the library to work on his projects.
statement: John is majoring in Biology.
statement: John is taking a course on Artificial Intelligence. 
statement: John is a dedicated student. 
statement: John has a part-time job.
Answer:
[
  {
      "statement": "John is majoring in Biology.",
      "reason": "John's major is explicitly mentioned as Computer Science. There is no information suggesting he is majoring in Biology.",
      "verdict": 0
  },
  {
      "statement": "John is taking a course on Artificial Intelligence.",
      "reason": "The context mentions the courses John is currently enrolled in, and Artificial Intelligence is not mentioned. Therefore, it cannot be deduced that John is taking a course on AI.",
      "verdict": 0
  },
  {
      "statement": "John is a dedicated student.",
      "reason": "The context states that he spends a significant amount of time studying and completing assignments. Additionally, it mentions that he often stays late in the library to work on his projects, which implies dedication.",
      "verdict": 1
  },
  {
      "statement": "John has a part-time job.",
      "reason": "There is no information given in the context about John having a part-time job.",
      "verdict": 0
  }
]

Context:
Photosynthesis is a process used by plants, algae, and certain bacteria to convert light energy into chemical energy.
statement: Albert Einstein was a genius.
Answer:
[
  {
      "statement": "Albert Einstein was a genius.",
      "reason": "The context and statement are unrelated"
      "verdict": 0
  }
]

Now provide your analysis for the following inputs. DO NOT PROVIDE ANY MORE EXAMPLES. Your response must be a valid JSON array like you see above.

Context:
{{context}}
{{statements}}
Answer:
`;
const LongFormResponseSchema = z.object({ statements: z.array(z.string()) });
type LongFormResponse = z.infer<typeof LongFormResponseSchema>;

const NliResponseBaseSchema = z.object({
  statement: z.string(),
  reason: z.string(),
  verdict: z.union([z.literal(0), z.literal(1)]),
});

type NliResponseBase = z.infer<typeof NliResponseBaseSchema>;

/**
 *
 */
export async function faithfulnessScore<
  CustomModelOptions extends z.ZodTypeAny,
>(
  judgeLlm: ModelArgument<CustomModelOptions>,
  dataPoint: BaseDataPoint,
  judgeConfig?: CustomModelOptions
): Promise<Score> {
  try {
    const { input, output, context } = dataPoint;
    if (!context?.length) {
      throw new Error('Context was not provided');
    }
    if (!output) {
      throw new Error('Output was not provided');
    }
    const longFormTemplate = Handlebars.compile(LONG_FORM_ANSWER_PROMPT);
    const longFormPrompt = longFormTemplate({
      question: input,
      answer: output,
    });
    const longFormResponse = await generate({
      model: judgeLlm,
      config: judgeConfig,
      prompt: longFormPrompt,
    });
    const parsedLongFormResponse = extractJson<LongFormResponse>(
      longFormResponse.text()
    );
    let statements = parsedLongFormResponse?.statements ?? [];
    if (statements.length === 0) {
      throw new Error('No statements returned');
    }
    const allStatements = statements.map((s) => `statement: ${s}`).join('\n');
    const allContext = context.join('\n');
    const nliTemplate = Handlebars.compile(NLI_STATEMENTS_MESSAGE);
    const nliPrompt = nliTemplate({
      context: allContext,
      statements: allStatements,
    });
    const response = await generate({
      model: judgeLlm,
      prompt: nliPrompt,
    });
    const parsedResponse = extractJson<
      Array<NliResponseBase> | NliResponseBase
    >(response.text());
    return nliResponseToScore(parsedResponse);
  } catch (err) {
    console.debug(
      `Genkit faithfulness evaluation failed with error ${err} for sample ${JSON.stringify(
        dataPoint
      )}`
    );
    throw err;
  }
}

function nliResponseToScore(
  input: NliResponseBase[] | NliResponseBase | null
): Score {
  if (!input) {
    throw new Error(`Evaluator response empty`);
  }
  let responses: NliResponseBase[];
  responses = Array.isArray(input) ? input : [input];
  const faithfulStatements = responses.reduce((total, resp) => {
    return total + resp.verdict;
  }, 0);
  return {
    score: faithfulStatements / responses.length,
    details: { reasoning: responses.map((r) => r.reason).join('; ') },
  };
}
