#!/bin/bash

# git clone git@github.com:firebase/genkit.git
# cd genkit
# pnpm i
# pnpm build
# pnpm test:all
# Run from root: scripts/release_main.sh

# pnpm login --registry https://wombat-dressing-room.appspot.com

CURRENT=`pwd`

cd genkit-tools/common
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit-tools/telemetry-server
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit-tools/cli
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/core
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/ai
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/genkit
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/dotprompt
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/chroma
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/dev-local-vectorstore
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/firebase
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/google-cloud
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/googleai
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/ollama
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/pinecone
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd js/plugins/vertexai
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/evaluators
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/langchain
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/checks
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  js/plugins/mcp
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT
