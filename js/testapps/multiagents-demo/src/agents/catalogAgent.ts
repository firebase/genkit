import { ai } from "../config/genkit";
    
import { fetchCatalogTool, fetchMostPopularItemsTool, getProductDetailsTool, searchCatalogTool } from "../tools";

// Simple agent for browsing and searching products
export const agent = ai.definePrompt({
    name: 'catalogAgent',
    description: 'Catalog Agent can help customers browse and search products',
    model: "googleai/gemini-2.5-flash",
    tools: [
      fetchCatalogTool,
      fetchMostPopularItemsTool,
      searchCatalogTool,
      getProductDetailsTool,
    ],
    system: `You are a helpful catalog agent for TechStore Computer Shop.
      Help customers browse products, search for items, and get product details.
      Be friendly and provide accurate information about products, prices, and availability.`,
  });