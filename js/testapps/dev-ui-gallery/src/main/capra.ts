import { z } from 'genkit';
import { ai } from '../genkit';
/**
 * Schema for a feature analysis with confidence and reasoning
 */
export const FeatureAnalysisSchema = z.object({
  reasoning: z
    .string()
    .describe(
      'Explanation of why this feature was determined to be needed or not needed'
    ),
  confidence: z
    .enum(['low', 'medium', 'high'])
    .describe('Confidence level in the analysis'),
  // This must be the last field to allow CoT reasoning.
  value: z.boolean().describe('Whether the feature is needed'),
});

/**
 * Schema for the input to the context analysis flow
 */
export const ContextAnalysisInputSchema = z.object({
  userInput: z.string().optional().describe('The latest request ƒrom the user'),
  proposal: z
    .string()
    .describe('The initial app proposal to analyze for context requirements'),
  history: z
    .string()
    .optional()
    .describe('The interaction history between the user and the model.'),
});

/**
 * Schema for the output of the context analysis flow
 */
export const ContextAnalysisOutputSchema = z.object({
  camera: FeatureAnalysisSchema.optional().describe(
    'Analysis of camera/image capture functionality requirements'
  ),
  database: FeatureAnalysisSchema.optional().describe(
    'Analysis of database/data persistence requirements'
  ),
  externalAPIs: FeatureAnalysisSchema.optional().describe(
    'Analysis of external API calls requirements'
  ),
  isProposalMentioned: z
    .object({
      reasoning: z.string().describe('Reasoning of your analysis'),
      confidence: z
        .enum(['low', 'medium', 'high'])
        .describe('Confidence level in the analysis'),
      // This must be the last field to allow CoT reasoning.
      value: z.boolean().describe('The final result of the analysis'),
    })
    .describe(
      'Analysis of whether the userInput contains the word "app proposal" or "blueprint", or a synonyms.' +
        'VERY IMPORTANT: Any implicit mention does NOT count.'
    )
    .optional(),
  isPersistenceMentioned: z
    .object({
      reasoning: z.string().describe('Reasoning of your analysis'),
      confidence: z
        .enum(['low', 'medium', 'high'])
        .describe('Confidence level in the analysis'),
      // This must be the last field to allow CoT reasoning.
      value: z.boolean().describe('The final result of the analysis'),
    })
    .describe(
      'Analysis of whether the userInput contains the word "database" or "firestore", or a synonyms.' +
        'VERY IMPORTANT: Any implicit mention does NOT count.'
    )
    .optional(),
});

export type ContextAnalysisInput = z.infer<typeof ContextAnalysisInputSchema>;
export type ContextAnalysisOutput = z.infer<typeof ContextAnalysisOutputSchema>;

ai.defineSchema('ContextAnalysisInputSchema', ContextAnalysisInputSchema);
ai.defineSchema('ContextAnalysisOutputSchema', ContextAnalysisOutputSchema);
