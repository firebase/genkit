import { z } from 'genkit';
import { mockCatalog } from '../data/mockCatalog';
import { ai } from '../config/genkit';

// Catalog Tools
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

// Payment Tools
export const processPaymentTool = ai.defineTool(
  {
    name: 'processPayment',
    description: 'Process a payment for an order',
    inputSchema: z.object({
      orderId: z.string().describe('The order ID to process payment for'),
      amount: z.number().describe('The payment amount'),
      paymentMethod: z
        .string()
        .describe('Payment method (credit_card, debit_card, paypal)'),
    }),
  },
  async (input) => {
    // Mock payment processing
    return {
      success: true,
      transactionId: `TXN-${Date.now()}`,
      orderId: input.orderId,
      amount: input.amount,
      status: 'completed',
      message: 'Payment processed successfully',
    };
  }
);

export const getStoreInfoTool = ai.defineTool(
  {
    name: 'getStoreInfo',
    description:
      'Get store information including hours, location, and contact details',
  },
  async () => {
    return {
      success: true,
      store: {
        name: 'TechStore Computer Shop',
        address: '123 Tech Street, Silicon Valley, CA 94000',
        phone: '(555) 123-4567',
        email: 'info@techstore.com',
        hours: {
          monday: '9:00 AM - 7:00 PM',
          tuesday: '9:00 AM - 7:00 PM',
          wednesday: '9:00 AM - 7:00 PM',
          thursday: '9:00 AM - 7:00 PM',
          friday: '9:00 AM - 8:00 PM',
          saturday: '10:00 AM - 6:00 PM',
          sunday: 'Closed',
        },
      },
    };
  }
);
