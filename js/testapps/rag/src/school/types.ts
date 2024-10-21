import { z } from 'genkit';

export const AgentStateSchema = z.object({
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
});
export type AgentState = z.infer<typeof AgentStateSchema>;
