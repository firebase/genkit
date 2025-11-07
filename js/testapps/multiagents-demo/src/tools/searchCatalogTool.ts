import { z } from 'genkit';
import { mockCatalog } from '../data/mockCatalog';
import { ai } from '../config/genkit';

export const searchCatalogTool = ai.defineTool(
  {
    name: 'searchCatalog',
    description: 'Search for products by name, category, or keyword',
    inputSchema: z.object({
      query: z
        .string()
        .describe('Search query (product name, category, or keyword)'),
    }),
  },
  async (input) => {
    const query = input.query.toLowerCase();
    const results = mockCatalog.filter(
      (item) =>
        item.name.toLowerCase().includes(query) ||
        item.category.toLowerCase().includes(query)
    );
    return {
      success: true,
      results,
      count: results.length,
    };
  }
);

