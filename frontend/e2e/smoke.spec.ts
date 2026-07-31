import { test, expect } from '@playwright/test';

test.describe('Infrastructure Monitoring MVP E2E Smoke Tests', () => {
  test('User can see login page and sign in as Admin', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h2')).toContainText('InfraTopology MVP');

    // Fill login credentials
    await page.fill('#username', 'admin@infra.com');
    await page.fill('#password', 'AdminSecurePass123!');
    await page.click('button[type="submit"]');

    // Redirect to Dashboard
    await expect(page).toHaveURL('/');
    await expect(page.locator('h1')).toContainText('Infrastructure Overview');
  });

  test('Navigation to Inventory, Topology, and Administration pages', async ({ page }) => {
    // Authenticate via local state
    await page.goto('/login');
    await page.fill('#username', 'admin@infra.com');
    await page.fill('#password', 'AdminSecurePass123!');
    await page.click('button[type="submit"]');

    // Navigate to Inventory
    await page.click('a:has-text("Inventory")');
    await expect(page).toHaveURL('/inventory');
    await expect(page.locator('h1')).toContainText('Infrastructure Inventory');

    // Navigate to Topology
    await page.click('a:has-text("Topology")');
    await expect(page).toHaveURL('/topology');
    await expect(page.locator('h1')).toContainText('Infrastructure Auto-Topology');

    // Navigate to Administration
    await page.click('a:has-text("Administration")');
    await expect(page).toHaveURL('/admin');
    await expect(page.locator('h1')).toContainText('Administration');
  });
});
