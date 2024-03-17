import { runDevUiTest } from './utils';

runDevUiTest(async (page, url) => {
  await page.goto(url);
  await page.setViewport({ width: 1080, height: 1024 });

  const basicFlowElemement = await page.waitForSelector('text/testFlow');
  basicFlowElemement?.click();

  const editor = await page.waitForSelector('#input-editor .monaco-editor');
  editor?.click();
  // it takes a sec for monaco to "focus"
  await new Promise((r) => setTimeout(r, 1000));

  await editor!.type('"hello world"');

  const runFlowButton = await page.waitForSelector('text/Run Flow');
  runFlowButton?.click();

  await page.waitForSelector('text/Test flow passed');
})
