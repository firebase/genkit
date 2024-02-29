# Genkit with Express (and Cloud Run)

1. Install required tools
    1. make sure you are using node version 18 or higher (run `node --version` to check).
    1. install [gcloud cli](https://cloud.google.com/sdk/docs/install)

1. Create a directory for the Genkit sample project:

    ```
    export GENKIT_PROJECT_HOME=~/tmp/genkit-express-project1
    mkdir -p $GENKIT_PROJECT_HOME
    cd $GENKIT_PROJECT_HOME
    ```

    If you're going to use an IDE, open it to this directory.

1. Initialize the nodejs project:

    ```
    npm init -y
    ```

1. You will need a GCP or Firebase project for persisting traces in Firestore. After you have created / picked one, run the following to set an env var with your project ID and set the project as your default:

    ```
    export GCLOUD_PROJECT=<your-cloud-project>
    ```
    ```
    gcloud config set project $GCLOUD_PROJECT
    ```

    NOTE: Your project must have billing enabled.

1. You will need Application Default Credentials. Run:

    ```
    gcloud auth application-default login
    ```

1. Enable services used in this sample app:

     1. Enable Firestore by navigating to https://pantheon.corp.google.com/firestore/databases?project=_ and click "Create Database".

     1. Enable Vertex AI by running: 

        ```
        gcloud services enable aiplatform.googleapis.com
        ```

     1. Enable Compute Engine API (used for Cloud Functions)

        ```
        gcloud services enable compute.googleapis.com
        ```

1. Create tsconfig.json file (```touch tsconfig.json```) and paste this:
    ```
    {
       "compilerOptions": {
          "module": "commonjs",
         "noImplicitReturns": true,
         "noUnusedLocals": false,
         "outDir": "lib",
         "sourceMap": true,
          "strict": true,
         "target": "es2017",
         "skipLibCheck": true,
         "esModuleInterop": true
       },
        "compileOnSave": true,
       "include": [
         "src"
       ]
     }
     ```

    Replace the contents of your package.json file with the following:
     ```
     {
       "name": "genkit-express-project1",
       "version": "1.0.0",
       "description": "",
       "main": "lib/index.js",
        "scripts": {
         "start": "node lib/index.js",
         "compile": "tsc",
         "build": "npm run build:clean && npm run compile",
         "build:clean": "rm -rf ./lib",
          "build:watch": "tsc --watch"
       },
       "keywords": [],
       "author": "",
       "license": "ISC",
       "devDependencies": {
          "typescript": "^5.3.3"
       },
       "dependencies": {
         "express": "^4.18.2"
       }
     }
     ```

1. Install Genkit packages:

    ```
    cd functions
    mkdir genkit-dist
    cp $GENKIT_DIST/* genkit-dist
    npm install --save-dev typescript
    npm i --save ./genkit-dist/google-genkit-common-0.0.2.tgz
    npm i --save ./genkit-dist/google-genkit-flow-0.0.2.tgz
    npm i --save ./genkit-dist/google-genkit-ai-0.0.2.tgz
    npm i --save ./genkit-dist/google-genkit-providers-0.0.2.tgz 
    npm i --save ./genkit-dist/google-genkit-plugin-vertex-ai-0.0.2.tgz
    npm i --save-dev ./genkit-dist/google-genkit-tools-plugins-0.0.2.tgz
    npm i --save-dev ./genkit-dist/genkit-cli-0.0.2.tgz
    ```

1. Create the src/index.ts file where your Genkit code will live:

    ```
    mkdir src
    touch src/index.ts
    ```

    Paste the following sample code into src/index.ts file: https://paste.googleplex.com/6246351714648064


1. Build and run your code:

   ```
   npm run build
   ```

1. Start the dev UI:

    ```npx genkit start```

    1. To try out the joke flow navigate to http://localhost:4000/flows and run the flow via the emulator.

    1. Try out the express app:
        - http://localhost:5000/joke?subject=banana
        - http://localhost:5000/jokeStream?subject=banana


1. To deploy to Cloud Run first check that the "Default compute service account" has the necessary permissions to run your flow. By default it usually has an "Editor" role, but it's dependent on the org policy.

    Navigate to https://pantheon.corp.google.com/iam-admin/iam (make sure your project is selected) and search for the Principal ending with `-compute@developer.gserviceaccount.com`

    At the very least it will need the following roles: Cloud Datastore User, Vertex AI User, Logs Writer, Monitoring Metric Writer, Cloud Trace Agent.

    If you don't see it on the list then you'll need to manually grant it (`YOUT_PROJECT_NUMBER-compute@developer.gserviceaccount.com`) the necessary permissions.

    For reference: https://screencast.googleplex.com/cast/NTc2MDM0NjMzNjc4ODQ4MHw4ZWU2NDA2YS01Ng


1. Deploy to Cloud Run:

    ```
    gcloud run deploy --update-env-vars GCLOUD_PROJECT=$GCLOUD_PROJECT
    ```

    Test out your deployed app!

    ```
    export MY_CLOUD_RUN_SERVICE_URL=https://.....run.app
    ```
    ```
    curl -m 70 -X GET $MY_CLOUD_RUN_SERVICE_URL/jokeStream?subject=banana -H "Authorization: bearer $(gcloud auth print-identity-token)"
    ```
    ```
    curl -m 70 -X GET $MY_CLOUD_RUN_SERVICE_URL/joke?subject=banana -H "Authorization: bearer $(gcloud auth print-identity-token)"
    ```


