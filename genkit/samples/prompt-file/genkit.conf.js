const { configureGenkit } = require('@google-genkit/common/config');
const { googleAI } = require('@google-genkit/providers/openai');

exports.default = configureGenkit({
  plugins: [googleAI()],
});
