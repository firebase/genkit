import { ai } from '../config/genkit';

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

