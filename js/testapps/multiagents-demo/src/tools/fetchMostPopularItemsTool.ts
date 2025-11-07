import { mockCatalog } from '../data/catalog';
import { ai } from '../config/genkit';

export const fetchMostPopularItemsTool = ai.defineTool(
  {
    name: 'fetchMostPopularItems',
    description: 'Fetches the most popular items in the catalog (top 3)',
  },
  async () => {
    const popular = mockCatalog.slice(0, 3);
    return {
      success: true,
      items: popular,
      message: 'Here are our most popular items',
    };
  }
);

