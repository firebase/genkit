import { devLocalRetrieverRef } from '@genkit-ai/dev-local-vectorstore';
import { EXAMPLE_EVENTS } from './data.js';
import { ai, z } from './genkit.js';

export const searchEvents = ai.defineTool(
  {
    name: 'searchEvents',
    description:
      'use this tool to search for upcoming school-wide, club, and activity events',
    inputSchema: z.object({
      activity: z
        .string()
        .optional()
        .describe('if looking for a particular activity, provide it here'),
      grade: z
        .number()
        .optional()
        .describe('restrict searched events to a particular grade level'),
    }),
  },
  async ({ activity, grade }) => {
    return EXAMPLE_EVENTS.filter(
      (e) => !grade || e.grades.includes(grade)
    ).filter(
      (e) => !activity || e.activity?.toLowerCase() === activity?.toLowerCase()
    );
  }
);

const retriever = devLocalRetrieverRef('school-handbook');
export const searchPolicies = ai.defineTool(
  {
    name: 'searchPolicies',
    description:
      'use this tool to research school policies such as academic, student life, and medical policies',
    inputSchema: z.object({
      query: z.string().describe('a semantic text query'),
    }),
    outputSchema: z.array(z.string()),
  },
  async ({ query }) => {
    const docs = await ai.retrieve({
      retriever,
      query,
      options: { k: 5 },
    });
    return docs.map((d) => d.text);
  }
);
