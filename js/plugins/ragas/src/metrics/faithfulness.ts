import Handlebars from 'handlebars';
import { generate } from '@google-genkit/ai/generate';
import { Dataset } from '@google-genkit/ai/evaluators';
import { ModelAction, ModelReference } from '@google-genkit/ai/model';
import { RagasDataPointZodType } from '../types';
import * as z from 'zod';

const LONG_FORM_ANSWER_PROMPT = `Create one or more statements from each sentence in the given answer. Here are some examples:

question: Who was  Albert Einstein and what is he best known for?
answer: He was a German-born theoretical physicist, widely acknowledged to be one of the greatest and most influential physicists of all time. He was best known for developing the theory of relativity, he also made important contributions to the development of the theory of quantum mechanics.
statements in json:
{
  "statements": [
      "Albert Einstein was born in Germany.",
      "Albert Einstein was best known for his theory of relativity."
  ]
}

question: Cadmium Chloride is slightly soluble in this chemical, it is also called what?
answer: alcohol
statements in json:
{
  "statements": [
      "Cadmium Chloride is slightly soluble in alcohol."
  ]
}

question: Were Hitler and Benito Mussolini of the same nationality?
answer: Sorry, I can't provide answer to that question.
statements in json:
{
  "statements": []
}

Now provide your analysis for the following inputs. DO NOT PROVIDER ANY MORE EXAMPLES. Your response must be a valid JSON like you see above.

question:{{question}}
answer: {{answer}}
statements in json:
`;

const NLI_STATEMENTS_MESSAGE = `Given a context and a set of statements, provide a structured and detailed response indicating whether the statement can be inferred from the context. You should only use "Yes" or "No" as verdict. Here are some examples:

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
      "verdict": "No"
  },
  {
      "statement": "John is taking a course on Artificial Intelligence.",
      "reason": "The context mentions the courses John is currently enrolled in, and Artificial Intelligence is not mentioned. Therefore, it cannot be deduced that John is taking a course on AI.",
      "verdict": "No"
  },
  {
      "statement": "John is a dedicated student.",
      "reason": "The context states that he spends a significant amount of time studying and completing assignments. Additionally, it mentions that he often stays late in the library to work on his projects, which implies dedication.",
      "verdict": "Yes"
  },
  {
      "statement": "John has a part-time job.",
      "reason": "There is no information given in the context about John having a part-time job.",
      "verdict": "No"
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
      "verdict": "No"
  }
]

Context:
Albert Einstein was a German-born theoretical physicist who is widely held to be one of the greatest and most influential scientists of all time.
statement: Nil
Answer:
[
  {
      "statement": "Nil",
      "reason": "The statement is invalid",
      "verdict": "No"
  }
]

Now provide your analysis for the following inputs. DO NOT PROVIDER ANY MORE EXAMPLES. Your response must be a valid JSON array like you see above.

Context:
{{context}}
{{statements}}
Answer:
`;

const NliResponseBaseSchema = z.object({
  statement: z.string(),
  reason: z.string(),
  verdict: z.enum(['Yes', 'No']),
});

type NliResponseBase = z.infer<typeof NliResponseBaseSchema>;

const NliResponseSchema = z
  .array(NliResponseBaseSchema)
  .or(NliResponseBaseSchema);

/**
 *
 */
export async function faithfulnessScore<
  CustomModelOptions extends z.ZodTypeAny
>(
  judgeLlm:
    | ModelAction<CustomModelOptions>
    | ModelReference<CustomModelOptions>,
  dataset: Dataset<RagasDataPointZodType>
) {
  const scores = [] as Array<number>;
  for (const d of dataset) {
    console.debug('sample: ', JSON.stringify(d));
    const { input, output, context } = { ...d };
    if (!context) {
      throw new Error('context required');
    }
    if (!output) {
      throw new Error('output required');
    }
    const longFormTemplate = Handlebars.compile(LONG_FORM_ANSWER_PROMPT);
    const longFormPrompt = longFormTemplate({
      question: input,
      answer: output,
    });
    const longFormResponse = await generate({
      model: judgeLlm,
      prompt: longFormPrompt,
      output: {
        format: 'json',
        schema: z.object({ statements: z.array(z.string()) }),
      },
    });

    console.debug('longform', longFormResponse.output());
    let statements = longFormResponse.output()?.statements ?? [];
    statements = statements.length > 0 ? statements : ['Nil'];
    const all_statements = statements.map((s) => `statement: ${s}`).join('\n');
    const allContext = context.join('\n');
    const nliTemplate = Handlebars.compile(NLI_STATEMENTS_MESSAGE);
    const nliPrompt = nliTemplate({
      context: allContext,
      statements: all_statements,
    });
    const response = await generate({
      model: judgeLlm,
      prompt: nliPrompt,
      output: {
        format: 'json',
        schema: NliResponseSchema,
      },
    });
    console.debug('nli', response.output());
    scores.push(nliResponseToScore(response.output()));
  }
  return scores;
}

function nliResponseToScore(input: NliResponseBase[] | NliResponseBase | null) {
  if (!input) return 0;
  let responses: NliResponseBase[];
  responses = Array.isArray(input) ? input : [input];
  const faithful_statements = responses
    .map((entry) => (entry.verdict === 'Yes' ? 1 : 0) as number)
    .reduce((total, curr) => {
      return total + curr;
    }, 0);
  const num_statements = responses.length;
  return num_statements > 0 ? faithful_statements / num_statements : 0;
}
