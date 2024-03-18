# Functions demo with Firebase Auth

To run this demo, follow the instructions in /docs/firebase.md to deploy.

The `jokeFlow` in this package requires Firebase Auth to work. Specifically
the Auth account must have the `email_verified = true` claim. There is a demo
page included here to test this out.

1. Get a project ready to test with in the Firebase Console.

1. Set up your project with Firebase Hosting; you'll need to go to the Firebase
   Console [Hosting page](https://console.firebase.google.com/project/_/hosting/)
   and enable it. You'll also need to create a new web app (available on the project
   overview page).

1. Take the JS config object you get from the last step, and put it in a file in the
   public directory called "config.js" (this file is gitignored; don't check in
   your project config!). The config should be stored in a global variable called
   `firebaseConfig`. I.e. `window.firebaseConfig = {...}`.

You're all ready to go with the demo using the local emulator suite. Execute
the following commands:

```
npm run build:js
firebase emulators:start --project=GCLOUD_PROJECT
```

At this point, simply navigate to `http://localhost:5000?emulated=true`.

## Deploying and testing

You can deploy these functions as well and use the demo page to test:

1. Deploy the functions. Depending on your org policy, you may need to manually
   set the function as invokable by anyone publicly (Firebase Auth checks happen
   post-IAM checks). See
   https://cloud.google.com/run/docs/securing/managing-access#make-service-public

1. Go back to the Firebase Console, enable Firebase Auth and turn on the
   "Anonymous" and "Google" Auth providers.

1. At this point you should be all set. Run the following commands to launch:

```
npm run build:js
firebase serve --only hosting --project $GCLOUD_PROJECT
```

And navigate to `http://localhost:5000`.
