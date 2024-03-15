const path = require('path');
const webpack = require('webpack');

module.exports = {
  mode: 'development',
  // make sure this points to your entry point file
  entry: './demopage/index.js',
  output: {
    path: path.resolve(__dirname, 'public'),
    filename: 'bundle.js',
  },
  plugins: [
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
    }),
  ],
};
