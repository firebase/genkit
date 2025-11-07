import { mockCatalog } from '../data/mockCatalog';
import { ai } from '../config/genkit';

export const fetchCatalogTool = ai.defineTool(
  {
    name: 'fetchCatalog',
    description:
      'Fetches the complete product catalog with all available items',
  },
  async () => {
    return {
      success: true,
      catalog: mockCatalog,
      totalItems: mockCatalog.length,
    };
  }
);

