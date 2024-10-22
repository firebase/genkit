#!/bin/bash

# Run from root: scripts/release_main.sh

pnpm login --registry https://wombat-dressing-room.appspot.com


CURRENT=`pwd`

cd genkit/genkit-tools/common
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/genkit-tools/cli
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/core
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/ai
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/flow
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/plugins/dotprompt
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/plugins/chroma
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/plugins/dev-local-vectorstore
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/plugins/firebase
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/plugins/google-cloud
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/plugins/googleai
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/plugins/ollama
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/plugins/pinecone
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd genkit/js/plugins/vertexai
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  genkit/js/plugins/evaluators
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

cd  genkit/js/plugins/langchain
pnpm publish --registry https://wombat-dressing-room.appspot.com
cd $CURRENT

