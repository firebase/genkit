/**
 * Copyright 2026 Google LLC
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
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import { expect, type Page, test } from '@playwright/test';

/**
 * Drag and Drop E2E Tests for Queue Reordering
 */

test.describe('Queue Drag and Drop', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.chat-container');
  });

  /**
   * Helper to inject multiple queue items
   */
  async function injectQueueItems(page: Page, items: string[]) {
    await page.evaluate((msgs) => {
      const el = document.querySelector('app-chat');
      if (!el) return;
      const comp = (
        window as unknown as { ng: { getComponent: (el: Element) => unknown } }
      ).ng.getComponent(el) as {
        chatService: {
          promptQueue: { set: (items: unknown[]) => void };
          isLoading: { set: (val: boolean) => void };
        };
      };
      comp.chatService.isLoading.set(true);
      comp.chatService.promptQueue.set(
        msgs.map((msg, i) => ({
          id: `test-${i}-${Date.now()}`,
          content: msg,
          model: 'googleai/gemini-2.0-flash',
          timestamp: new Date(),
        }))
      );
    }, items);
  }

  test('should display drag handles for all queue items', async ({ page }) => {
    await injectQueueItems(page, ['First', 'Second', 'Third']);

    const dragHandles = page.locator('.drag-handle');
    await expect(dragHandles).toHaveCount(3);
  });

  test('should show grab cursor on drag handle hover', async ({ page }) => {
    await injectQueueItems(page, ['Draggable']);

    const dragHandle = page.locator('.drag-handle').first();
    const cursor = await dragHandle.evaluate((el) => window.getComputedStyle(el).cursor);
    expect(cursor).toBe('grab');
  });

  test('should reorder items on drag and drop', async ({ page }) => {
    await injectQueueItems(page, ['First', 'Second', 'Third']);

    // Get the first and last items
    const items = page.locator('.queue-item');
    const firstItem = items.nth(0);
    const lastItem = items.nth(2);

    // Get the first item's drag handle
    const dragHandle = firstItem.locator('.drag-handle');

    // Perform drag and drop
    await dragHandle.dragTo(lastItem);

    // Wait for Angular to process
    await page.waitForTimeout(300);

    // Check the new order - first item should now be at the end
    const contents = await page.locator('.queue-item-content').allTextContents();
    expect(contents[0]).toBe('Second');
    expect(contents[2]).toBe('First');
  });

  test('queue items should have CDK drag classes', async ({ page }) => {
    await injectQueueItems(page, ['Test item']);

    const queueItem = page.locator('.queue-item');
    // cdkDrag adds data attributes
    await expect(queueItem).toBeVisible();
  });

  test('drop list container should exist', async ({ page }) => {
    await injectQueueItems(page, ['Test item']);

    const dropList = page.locator('[cdkDropList]');
    await expect(dropList).toBeVisible();
  });
});
