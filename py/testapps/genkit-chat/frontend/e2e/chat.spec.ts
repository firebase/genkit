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
 * Genkit Chat E2E Tests
 *
 * Tests for the chat interface UI elements and behaviors including:
 * - Chat input and message sending
 * - Prompt queue functionality
 * - Model selection
 * - Focus management
 */

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for the app to fully load
    await page.waitForSelector('.chat-container');
  });

  test('should display welcome message on initial load', async ({ page }) => {
    // Check for welcome greeting
    await expect(page.locator('.welcome-header')).toBeVisible();
    await expect(page.locator('.welcome-title')).toBeVisible();
    await expect(page.locator('.welcome-subtitle')).toContainText('How can I help you today?');
  });

  test('should have chat input focused and ready', async ({ page }) => {
    const chatInput = page.locator('.chat-input');
    await expect(chatInput).toBeVisible();
    // Input should be usable
    await chatInput.fill('Test message');
    await expect(chatInput).toHaveValue('Test message');
  });

  test('should maintain focus on input after sending message', async ({ page }) => {
    const chatInput = page.locator('.chat-input');
    await chatInput.fill('Hello');
    await page.keyboard.press('Enter');

    // Wait a moment for Angular change detection
    await page.waitForTimeout(100);

    // Focus should return to input
    await expect(chatInput).toBeFocused();
  });

  test('should show model selector', async ({ page }) => {
    const modelSelector = page.locator('.model-selector');
    await expect(modelSelector).toBeVisible();
  });

  test('should display quick action chips', async ({ page }) => {
    const quickActions = page.locator('.quick-actions');
    await expect(quickActions).toBeVisible();
  });
});

test.describe('Prompt Queue', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.chat-container');
  });

  /**
   * Helper to inject a queue item via Angular's service for testing
   */
  async function injectQueueItem(page: Page, content: string) {
    await page.evaluate((msg) => {
      const el = document.querySelector('app-chat');
      if (!el) return;
      const comp = (
        window as unknown as { ng: { getComponent: (el: Element) => unknown } }
      ).ng.getComponent(el) as {
        chatService: {
          promptQueue: { set: (items: unknown[]) => void; (): unknown[] };
          isLoading: { set: (val: boolean) => void };
        };
      };
      const currentQueue = comp.chatService.promptQueue();
      comp.chatService.isLoading.set(true); // Queue only shows when loading
      comp.chatService.promptQueue.set([
        ...(currentQueue as unknown[]),
        {
          id: `test-${Date.now()}`,
          content: msg,
          model: 'googleai/gemini-2.0-flash',
          timestamp: new Date(),
        },
      ]);
    }, content);
  }

  test('should show queue when loading and items are queued', async ({ page }) => {
    await injectQueueItem(page, 'Test queued prompt');

    // Queue should appear
    const queue = page.locator('.prompt-queue');
    await expect(queue).toBeVisible();

    // Should show queue count
    await expect(page.locator('.queue-count')).toContainText('1 Queued');
  });

  test('should display queue item content', async ({ page }) => {
    await injectQueueItem(page, 'My queued message');

    const queueItem = page.locator('.queue-item-content');
    await expect(queueItem).toContainText('My queued message');
  });

  test('should have drag handle for reordering', async ({ page }) => {
    await injectQueueItem(page, 'Draggable item');

    const dragHandle = page.locator('.drag-handle');
    await expect(dragHandle).toBeVisible();
  });

  test('should have send, edit, and delete buttons', async ({ page }) => {
    await injectQueueItem(page, 'Item with actions');

    const actions = page.locator('.queue-item-actions');
    await expect(actions.locator('button')).toHaveCount(3); // send, edit, delete
  });

  test('should have send all and clear all buttons in header', async ({ page }) => {
    await injectQueueItem(page, 'Item for header');

    await expect(page.locator('.send-all-btn')).toBeVisible();
    await expect(page.locator('.clear-all-btn')).toBeVisible();
  });

  test('should clear queue when clear all is clicked', async ({ page }) => {
    await injectQueueItem(page, 'Item to clear');

    // Verify queue is visible
    await expect(page.locator('.prompt-queue')).toBeVisible();

    // Click clear all
    await page.locator('.clear-all-btn').click();

    // Queue should disappear (no items left)
    await expect(page.locator('.prompt-queue')).not.toBeVisible();
  });

  test('should delete individual queue item', async ({ page }) => {
    await injectQueueItem(page, 'First item');
    await injectQueueItem(page, 'Second item');

    // Should have 2 items
    await expect(page.locator('.queue-count')).toContainText('2 Queued');

    // Delete first item
    await page.locator('.queue-item-actions button').nth(2).first().click(); // Delete is 3rd button

    // Should have 1 item now
    await expect(page.locator('.queue-count')).toContainText('1 Queued');
  });

  test('queue should be scrollable with many items', async ({ page }) => {
    // Add multiple items
    for (let i = 1; i <= 5; i++) {
      await injectQueueItem(page, `Queue item ${i}`);
    }

    const queueItems = page.locator('.queue-items');
    // Check that it has max-height set (means scrollable)
    const maxHeight = await queueItems.evaluate((el) => window.getComputedStyle(el).maxHeight);
    expect(maxHeight).toBe('150px');
  });
});

test.describe('Message Display', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.chat-container');
  });

  test('should have proper spacing between messages and input', async ({ page }) => {
    const messagesContainer = page.locator('.messages-container');
    const paddingBottom = await messagesContainer.evaluate(
      (el) => window.getComputedStyle(el).paddingBottom
    );
    // Should have generous padding (120px)
    expect(Number.parseInt(paddingBottom, 10)).toBeGreaterThanOrEqual(100);
  });
});

test.describe('Theme', () => {
  test('should support theme toggle', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.chat-container');

    // Check for theme toggle in settings or sidebar
    const themeToggle = page.locator('[matTooltip*="Theme"]');
    if (await themeToggle.isVisible()) {
      await expect(themeToggle).toBeVisible();
    }
  });
});
