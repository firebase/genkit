import { GenerateRequest } from 'genkit';
import { attendanceAgent } from './attendanceAgent';
import { getUpcomingHolidays, userContext } from './data';
import { ai, env } from './genkit';
import { searchEvents, searchPolicies } from './tools.js';
import { AgentState } from './types';

async function systemMessage(state: AgentState): Promise<string> {
  return `You are Bell, a helpful assistant that provides information to parents of Sparkyville High School students. Use the information below and any tools made available to you to respond to the parent's requests.
  
=== Frequently Asked Questions

- Classes begin at 8am, students are dismissed at 3:30pm
- Parking permits are issued on a first-come first-serve basis beginning Aug 1

${userContext(state)}

=== Upcoming School Holidays

${JSON.stringify(await getUpcomingHolidays())}
`;
}

export const infoAgent = ai.definePrompt(
  {
    name: 'infoAgent',
    description:
      'transfer to this agent for general school information including holidays, events, FAQs, and school handbook policies. do not mention you are transferring, just do it',
    tools: [searchEvents, searchPolicies, attendanceAgent],
  },
  async () => {
    return {
      messages: [
        {
          role: 'system',
          content: [{ text: await systemMessage(env.currentSession.state) }],
        },
      ],
    } as GenerateRequest;
  }
);
