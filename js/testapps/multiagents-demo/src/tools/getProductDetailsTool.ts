import { z } from 'genkit';
import { mockCatalog } from '../data/catalog';
import { ai } from '../config/genkit';

export const getProductDetailsTool = ai.defineTool(
  {
    name: 'getProductDetails',
    description: 'Get detailed information about a specific product by ID',
    inputSchema: z.object({
      productId: z
        .string()
        .describe('The ID of the product to get details for'),
    }),
  },
  async (input) => {
    const product = mockCatalog.find((item) => item.id === input.productId);
    if (!product) {
      return {
        success: false,
        message: 'Product not found',
      };
    }
    return {
      success: true,
      product,
    };
  }
);

