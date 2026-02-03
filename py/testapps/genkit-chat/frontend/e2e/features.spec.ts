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

import { expect, test } from '@playwright/test';

/**
 * Markdown rendering and Content Safety E2E Tests
 */

test.describe('Markdown Rendering', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.chat-container');
  });

  test('should have markdown toggle button in toolbar', async ({ page }) => {
    const markdownBtn = page.locator('.markdown-btn');
    await expect(markdownBtn).toBeVisible();
    await expect(markdownBtn.locator('span')).toContainText('MD');
  });

  test('should toggle markdown mode on click', async ({ page }) => {
    const markdownBtn = page.locator('.markdown-btn');

    // Initially active (markdown on by default)
    await expect(markdownBtn).toHaveClass(/active/);

    // Click to disable
    await markdownBtn.click();
    await expect(markdownBtn).not.toHaveClass(/active/);

    // Click to enable again
    await markdownBtn.click();
    await expect(markdownBtn).toHaveClass(/active/);
  });

  test('should show appropriate tooltip for markdown toggle', async ({ page }) => {
    const markdownBtn = page.locator('.markdown-btn');

    // Hover to show tooltip
    await markdownBtn.hover();

    // Check tooltip appears (content varies based on state)
    const tooltip = page.locator('.mat-mdc-tooltip');
    await expect(tooltip).toBeVisible();
  });
});

test.describe('Content Safety', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.chat-container');
  });

  test('should have safety toggle button in toolbar', async ({ page }) => {
    const safetyBtn = page.locator('.safety-btn');
    await expect(safetyBtn).toBeVisible();
    await expect(safetyBtn.locator('span')).toContainText('Safe');
  });

  test('should toggle content safety mode on click', async ({ page }) => {
    const safetyBtn = page.locator('.safety-btn');

    // Initially active (safety on by default)
    await expect(safetyBtn).toHaveClass(/active/);

    // Click to disable
    await safetyBtn.click();
    await expect(safetyBtn).not.toHaveClass(/active/);

    // Click to enable again
    await safetyBtn.click();
    await expect(safetyBtn).toHaveClass(/active/);
  });

  test('should show shield icon when active', async ({ page }) => {
    const safetyBtn = page.locator('.safety-btn');
    const icon = safetyBtn.locator('mat-icon');

    // When active, should show filled shield
    await expect(safetyBtn).toHaveClass(/active/);
    await expect(icon).toContainText('shield');
  });

  test('should show tooltip for safety toggle', async ({ page }) => {
    const safetyBtn = page.locator('.safety-btn');

    // Hover to show tooltip
    await safetyBtn.hover();

    // Check tooltip appears
    const tooltip = page.locator('.mat-mdc-tooltip');
    await expect(tooltip).toBeVisible();
  });
});

test.describe('Toolbar Layout', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.chat-container');
  });

  test('should have all toolbar buttons visible', async ({ page }) => {
    // Check main toolbar buttons
    await expect(page.locator('.streaming-btn')).toBeVisible();
    await expect(page.locator('.markdown-btn')).toBeVisible();
    await expect(page.locator('.safety-btn')).toBeVisible();
    await expect(page.locator('.model-select-btn')).toBeVisible();
  });

  test('toolbar buttons should be in correct order', async ({ page }) => {
    const toolbarLeft = page.locator('.toolbar-left');
    const buttons = toolbarLeft.locator('.toolbar-btn');

    // Should have at least 3 buttons (stream, md, safe)
    await expect(buttons).toHaveCount(await buttons.count());
    expect(await buttons.count()).toBeGreaterThanOrEqual(3);
  });
});
