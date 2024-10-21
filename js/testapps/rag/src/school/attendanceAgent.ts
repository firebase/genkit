import { userContext } from './data';
import { ai, env } from './genkit';
import { reportAbsence, reportTardy } from './tools';
import { AgentState } from './types';

function systemMessage(state: AgentState) {
  return `You are Bell, a helpful attendance assistance agent for Sparkyville High School. A parent has been referred to you to handle an attendance-related concern. Use the tools available to you to assist the parent.

- Parents may only report absences for their own students.
- If you are unclear about any of the fields required to report an absence or tardy, request clarification before using the tool.
- If the parent asks about anything other than attendance-related concerns that you can handle, transfer to the info agent.

${userContext(state)}`;
}

export const attendanceAgent = ai.definePrompt(
  {
    name: 'attendanceAgent',
    description:
      'transfer to this agent when the user asks questions about attendance-related concerns like tardies or absences. do not mention that you are transferring, just do it',
    tools: [reportAbsence, reportTardy],
  },
  async () => {
    const state = env.currentSession.state;
    return {
      messages: [{ role: 'system', content: [{ text: systemMessage(state) }] }],
    };
  }
);
