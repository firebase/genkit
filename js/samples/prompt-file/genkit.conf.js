const { configureGenkit } = require('@genkit-ai/common/config');
const { googleAI } = require('@genkit-ai/providers/google-ai');

exports.default = configureGenkit({
  plugins: [googleAI()],
});
