#!/bin/bash

# git clone git@github.com:firebase/genkit.git
# cd genkit
# pnpm i
# pnpm build
# pnpm test:all
# Run from root: scripts/release_main.sh

# pnpm login --registry https://wombat-dressing-room.appspot.com

CURRENT=`pwd`
RELEASE_BRANCH="${RELEASE_BRANCH:-main}"
RELEASE_TAG="${RELEASE_TAG:-next}"

cd genkit-tools/common
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit-tools/telemetry-server
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit-tools/cli
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/core
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/ai
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/genkit
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/chroma
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/dev-local-vectorstore
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/firebase
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/google-cloud
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/googleai
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/ollama
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/pinecone
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/vertexai
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/evaluators
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/langchain
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/checks
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/mcp
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/express
pnpm publish --tag $RELEASE_TAG --publish-branch $RELEASE_BRANCH --registry https://wombat-dressing-room.appspot.com
cd $CURRENT
