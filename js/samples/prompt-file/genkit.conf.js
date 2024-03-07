const { configureGenkit } = require('@google-genkit/common/config');
const { googleAI } = require('@google-genkit/providers/google-ai');

exports.default = configureGenkit({
  plugins: [googleAI()],
});
