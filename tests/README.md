# E2E tests

This folder houses some e2e tests. You can run them by: `npm run test` (this assumes you've already ran `npm i`), however there are a few extra steps:

1. Some tests use puppeteer framework which requires a dev build of the chrome browser. This is a one time setup step. Run

   ```
   npx puppeteer browsers install chrome
   ```

1. The test will attempt to install genkit packages from the `dist` folder up in the root folder, so if you want to test agaisnt the latest build of your local source you'll need to build and pack it first.

   to build, it's OK to use `build:watch` in specific package folders that you're working on, or re-build only the individual packages by running `npm run build` there.

   To rebuild everything (slow but guaranteed clean build) from the root run:

   ```
   npm run build:all
   ```

   to pack what you already built, you can run `npm run pack` from most package folders, but you can also from the root run:

   ```
   npm run pack:all
   ```

   which will pack everything (it's pretty fast).

   In the root package.json there's a `test:e2e` script that should handle all these steps.
