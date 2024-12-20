#!/bin/bash
# Run from root: scripts/e2e/deploy_e2e.sh
CURRENT=`pwd`

# Build the all the core packages
cd js/
echo "Building core packages"
pnpm build

echo "Packing core Genkit packages"
pnpm pack:all
cd $CURRENT

# Commonjs Firebase Functions
# Copy locally packed files into the dist directory with the function
echo "Moving tarballs to functions directory"
mkdir -p ./e2e/functions_commonjs/functions/dist
cp dist/genkit-[1-9]*.tgz ./e2e/functions_commonjs/functions/dist/
cp dist/genkit-ai-firebase*.tgz ./e2e/functions_commonjs/functions/dist/
cp dist/genkit-ai-googleai*.tgz ./e2e/functions_commonjs/functions/dist/
