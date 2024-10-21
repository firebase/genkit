import { GenerateRequest } from 'genkit';
import { ai, z } from './genkit';
import { searchEvents, searchPolicies } from './tools.js';

const StateSchema = z.object({
  parentId: z.number(),
  parentName: z.string(),
  students: z.array(
    z.object({
      id: z.number(),
      name: z.string(),
      grade: z.number(),
      activities: z.array(z.string()),
    })
  ),
  holidays: z.array(
    z.object({
      holiday: z.string(),
      date: z.string(),
    })
  ),
});

export const bell = ai.defineEnvironment({
  name: 'agentEnv',
  stateSchema: StateSchema,
});

function systemMessage(state: z.infer<typeof StateSchema>): string {
  return `You are a helpful assistant that provides information to parents of Sparkyville High School students.
  
=== Frequently Asked Questions

- Classes begin at 8am, students are dismissed at 3:30pm
- Parking permits are issued on a first-come first-serve basis beginning Aug 1

=== User Context

- The current parent user is '${state?.parentName}'
- The current date and time is: ${new Date().toString()}

=== Registered students of the current user

${JSON.stringify(state?.students)}

=== Upcoming School Holidays

${JSON.stringify(state?.holidays)}
`;
}

export const infoAgent = ai.definePrompt(
  {
    name: 'infoAgent',
    description:
      'use this agent for general school information including holidays, events, FAQs, and school handbook policies',
    tools: [searchEvents, searchPolicies],
  },
  async () => {
    return {
      messages: [
        {
          role: 'system',
          content: [{ text: systemMessage(bell.currentSession.state) }],
        },
      ],
    } as GenerateRequest;
  }
);
