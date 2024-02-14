const { configureGenkit } = require('@google-genkit/common/config');
const { googleAI } = require('@google-genkit/providers/models');

exports.default = configureGenkit({
  plugins: [googleAI()],
});
