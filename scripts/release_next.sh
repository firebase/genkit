#!/bin/bash

# git clone git@github.com:firebase/genkit.git
# cd genkit
# git checkout next
# pnpm i
# pnpm build
# pnpm test:all

# Run from root: scripts/release_next.sh

pnpm login --registry https://wombat-dressing-room.appspot.com

CURRENT=`pwd`

cd genkit-tools/cli
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit-tools/common
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit-tools/telemetry-server
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/core
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/ai
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/genkit
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/dotprompt
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/chroma
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/dev-local-vectorstore
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/firebase
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/google-cloud
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/googleai
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/ollama
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/pinecone
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/vertexai
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/evaluators
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/langchain
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/checks
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/mcp
pnpm publish --tag next --publish-branch next --registry https://wombat-dressing-room.appspot.com
cd $CURRENT
