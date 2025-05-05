import { __disableReflectionApi, shutdown } from 'genkit';
import { pdfQA, simpleEcho } from './pdf-rag.js';

describe('Math functions', () => {
  beforeAll(() => {
    __disableReflectionApi();
  });

  // afterAll(async () => {
  //   await shutdown();
  // });
  // test('adds 1 + 2 to equal 3', () => {
  //   expect(1 + 2).toBe(3);
  // });

  // test('multiplies 3 * 4 to equal 12', () => {
  //   expect(3 * 4).toBe(12);
  // });

  test('simpleEcho', async () => {

    expect(await simpleEcho('Hellozzz world')).toBe('Hellozzz world');
  });

  // test('pdfQA', async () => {
  //   expect(await pdfQA('Can I feed milk to my cats?')).toContain('No');
  // });
});
