#!/bin/bash
# Run from root: scripts/e2e/deploy_e2e.sh

# Build the commonjs functions 
cd e2e/functions_commonjs/functions
echo "Installing commonjs e2e function dependencies"
npm i
echo "Building functions"
npm run build

echo "Deploying to Cloud"
firebase deploy --only functions

cd $CURRENT