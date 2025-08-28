/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import assert from 'assert';
import { describe, it } from 'node:test';
import { ensurePrefixed, removePrefix } from '../src/common.js';

describe('Name Helper Functions', () => {
  describe('removePrefix', () => {
    it('should remove googleai/ prefix from prefixed names', () => {
      assert.strictEqual(
        removePrefix('googleai/gemini-1.5-flash'),
        'gemini-1.5-flash'
      );
      assert.strictEqual(
        removePrefix('googleai/imagen-3.0-generate-002'),
        'imagen-3.0-generate-002'
      );
      assert.strictEqual(
        removePrefix('googleai/veo-2.0-generate-001'),
        'veo-2.0-generate-001'
      );
      assert.strictEqual(
        removePrefix('googleai/embedding-001'),
        'embedding-001'
      );
    });

    it('should return unprefixed names unchanged', () => {
      assert.strictEqual(removePrefix('gemini-1.5-flash'), 'gemini-1.5-flash');
      assert.strictEqual(
        removePrefix('imagen-3.0-generate-002'),
        'imagen-3.0-generate-002'
      );
      assert.strictEqual(
        removePrefix('veo-2.0-generate-001'),
        'veo-2.0-generate-001'
      );
      assert.strictEqual(removePrefix('embedding-001'), 'embedding-001');
    });

    it('should handle edge cases', () => {
      // Empty string
      assert.strictEqual(removePrefix(''), '');

      // Just the prefix
      assert.strictEqual(removePrefix('googleai/'), '');

      // Multiple slashes (should only remove the first googleai/)
      assert.strictEqual(
        removePrefix('googleai/googleai/gemini-1.5-flash'),
        'googleai/gemini-1.5-flash'
      );

      // Case sensitivity - should not match
      assert.strictEqual(
        removePrefix('GoogleAI/gemini-1.5-flash'),
        'GoogleAI/gemini-1.5-flash'
      );
      assert.strictEqual(
        removePrefix('GOOGLEAI/gemini-1.5-flash'),
        'GOOGLEAI/gemini-1.5-flash'
      );
    });

    it('should handle special characters in model names', () => {
      assert.strictEqual(
        removePrefix('googleai/gemini-2.0-flash-exp'),
        'gemini-2.0-flash-exp'
      );
      assert.strictEqual(
        removePrefix('googleai/gemini-2.5-pro-exp-03-25'),
        'gemini-2.5-pro-exp-03-25'
      );
      assert.strictEqual(
        removePrefix('googleai/gemma-3-12b-it'),
        'gemma-3-12b-it'
      );
    });
  });

  describe('ensurePrefixed', () => {
    it('should add googleai/ prefix to unprefixed names', () => {
      assert.strictEqual(
        ensurePrefixed('gemini-1.5-flash'),
        'googleai/gemini-1.5-flash'
      );
      assert.strictEqual(
        ensurePrefixed('imagen-3.0-generate-002'),
        'googleai/imagen-3.0-generate-002'
      );
      assert.strictEqual(
        ensurePrefixed('veo-2.0-generate-001'),
        'googleai/veo-2.0-generate-001'
      );
      assert.strictEqual(
        ensurePrefixed('embedding-001'),
        'googleai/embedding-001'
      );
    });

    it('should return already prefixed names unchanged', () => {
      assert.strictEqual(
        ensurePrefixed('googleai/gemini-1.5-flash'),
        'googleai/gemini-1.5-flash'
      );
      assert.strictEqual(
        ensurePrefixed('googleai/imagen-3.0-generate-002'),
        'googleai/imagen-3.0-generate-002'
      );
      assert.strictEqual(
        ensurePrefixed('googleai/veo-2.0-generate-001'),
        'googleai/veo-2.0-generate-001'
      );
      assert.strictEqual(
        ensurePrefixed('googleai/embedding-001'),
        'googleai/embedding-001'
      );
    });

    it('should handle edge cases', () => {
      // Empty string
      assert.strictEqual(ensurePrefixed(''), 'googleai/');

      // Just the prefix
      assert.strictEqual(ensurePrefixed('googleai/'), 'googleai/');

      // Multiple slashes (should add prefix to the whole thing)
      assert.strictEqual(
        ensurePrefixed('googleai/googleai/gemini-1.5-flash'),
        'googleai/googleai/gemini-1.5-flash'
      );

      // Case sensitivity - should not match existing prefix
      assert.strictEqual(
        ensurePrefixed('GoogleAI/gemini-1.5-flash'),
        'googleai/GoogleAI/gemini-1.5-flash'
      );
      assert.strictEqual(
        ensurePrefixed('GOOGLEAI/gemini-1.5-flash'),
        'googleai/GOOGLEAI/gemini-1.5-flash'
      );
    });

    it('should handle special characters in model names', () => {
      assert.strictEqual(
        ensurePrefixed('gemini-2.0-flash-exp'),
        'googleai/gemini-2.0-flash-exp'
      );
      assert.strictEqual(
        ensurePrefixed('gemini-2.5-pro-exp-03-25'),
        'googleai/gemini-2.5-pro-exp-03-25'
      );
      assert.strictEqual(
        ensurePrefixed('gemma-3-12b-it'),
        'googleai/gemma-3-12b-it'
      );
    });
  });

  describe('round-trip consistency', () => {
    it('should maintain consistency: removePrefix(ensurePrefixed(x)) === x for non-prefix-only names', () => {
      const testNames = [
        'gemini-1.5-flash',
        'imagen-3.0-generate-002',
        'veo-2.0-generate-001',
        'embedding-001',
        'gemini-2.0-flash-exp',
        'gemini-2.5-pro-exp-03-25',
        'gemma-3-12b-it',
        '',
      ];

      for (const name of testNames) {
        const result = removePrefix(ensurePrefixed(name));
        assert.strictEqual(result, name, `Failed for name: "${name}"`);
      }
    });

    it('should handle edge case: removePrefix(ensurePrefixed("googleai/")) === ""', () => {
      // Special case: "googleai/" becomes "" after round-trip
      const result = removePrefix(ensurePrefixed('googleai/'));
      assert.strictEqual(
        result,
        '',
        'googleai/ should become empty string after round-trip'
      );
    });

    it('should maintain consistency: ensurePrefixed(removePrefix(x)) === x for prefixed names', () => {
      const testNames = [
        'googleai/gemini-1.5-flash',
        'googleai/imagen-3.0-generate-002',
        'googleai/veo-2.0-generate-001',
        'googleai/embedding-001',
        'googleai/gemini-2.0-flash-exp',
        'googleai/gemini-2.5-pro-exp-03-25',
        'googleai/gemma-3-12b-it',
        'googleai/',
      ];

      for (const name of testNames) {
        const result = ensurePrefixed(removePrefix(name));
        assert.strictEqual(result, name, `Failed for name: "${name}"`);
      }
    });
  });

  describe('double prefix prevention', () => {
    it('should prevent double prefixes when used together', () => {
      // Simulate the scenario that was causing double prefixes
      const inputName = 'googleai/gemini-1.5-flash';

      // This is what the resolver does:
      const rawActionName = removePrefix(inputName);
      const fullActionName = ensurePrefixed(rawActionName);

      // Should not result in double prefix
      assert.strictEqual(fullActionName, 'googleai/gemini-1.5-flash');
      assert.notStrictEqual(
        fullActionName,
        'googleai/googleai/gemini-1.5-flash'
      );
    });

    it('should handle multiple prefix removals safely', () => {
      const doublePrefixed = 'googleai/googleai/gemini-1.5-flash';

      // First removal
      const firstRemoval = removePrefix(doublePrefixed);
      assert.strictEqual(firstRemoval, 'googleai/gemini-1.5-flash');

      // Second removal
      const secondRemoval = removePrefix(firstRemoval);
      assert.strictEqual(secondRemoval, 'gemini-1.5-flash');

      // Ensure prefixed
      const finalResult = ensurePrefixed(secondRemoval);
      assert.strictEqual(finalResult, 'googleai/gemini-1.5-flash');
    });
  });

  describe('TypeScript type safety', () => {
    it('should work with template literal types', () => {
      // These tests verify that the functions work with the template literal types
      // defined in common.ts

      const unprefixedName = 'gemini-1.5-flash';
      const prefixedName = 'googleai/gemini-1.5-flash';

      // removePrefix should return the raw name type
      const rawResult = removePrefix(prefixedName);
      assert.strictEqual(rawResult, unprefixedName);

      // ensurePrefixed should return the prefixed name type
      const fullResult = ensurePrefixed(unprefixedName);
      assert.strictEqual(fullResult, prefixedName);

      // Both should work with either input type
      assert.strictEqual(removePrefix(unprefixedName), unprefixedName);
      assert.strictEqual(ensurePrefixed(prefixedName), prefixedName);
    });
  });

  describe('real-world usage scenarios', () => {
    it('should handle resolver scenarios correctly', () => {
      // Simulate what happens in the plugin resolver
      const scenarios = [
        { input: 'gemini-1.5-flash', expected: 'googleai/gemini-1.5-flash' },
        {
          input: 'googleai/gemini-1.5-flash',
          expected: 'googleai/gemini-1.5-flash',
        },
        {
          input: 'imagen-3.0-generate-002',
          expected: 'googleai/imagen-3.0-generate-002',
        },
        {
          input: 'googleai/imagen-3.0-generate-002',
          expected: 'googleai/imagen-3.0-generate-002',
        },
        {
          input: 'veo-2.0-generate-001',
          expected: 'googleai/veo-2.0-generate-001',
        },
        {
          input: 'googleai/veo-2.0-generate-001',
          expected: 'googleai/veo-2.0-generate-001',
        },
      ];

      for (const scenario of scenarios) {
        const rawActionName = removePrefix(scenario.input);
        const fullActionName = ensurePrefixed(rawActionName);
        assert.strictEqual(
          fullActionName,
          scenario.expected,
          `Failed for input: "${scenario.input}"`
        );
      }
    });

    it('should handle static factory scenarios correctly', () => {
      // Simulate what happens in the static .model() and .embedder() factories
      const scenarios = [
        { input: 'gemini-1.5-flash', expected: 'googleai/gemini-1.5-flash' },
        {
          input: 'googleai/gemini-1.5-flash',
          expected: 'googleai/gemini-1.5-flash',
        },
        { input: 'embedding-001', expected: 'googleai/embedding-001' },
        { input: 'googleai/embedding-001', expected: 'googleai/embedding-001' },
      ];

      for (const scenario of scenarios) {
        const fullName = ensurePrefixed(scenario.input);
        assert.strictEqual(
          fullName,
          scenario.expected,
          `Failed for input: "${scenario.input}"`
        );
      }
    });
  });
});
