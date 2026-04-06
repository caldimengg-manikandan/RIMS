import { test, expect } from '@playwright/test';

test.describe('Full System Flow - RIMS Platform', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to homepage before each test
    await page.goto('/');
  });

  // ---------------------------------------------------------
  // STEP 2: END-TO-END USER FLOWS
  // ---------------------------------------------------------

  test('Candidate Registration, Suspense Loaders, and AI Access', async ({ page }) => {
    // Test the Suspense boundaries of the login and register pages
    await page.click('text=Candidate');
    await expect(page).toHaveURL(/.*register.*role=candidate.*/);

    // Verify Password complexity UI elements (Step 9)
    await page.fill('input[name="password"]', 'weak');
    await expect(page.locator('text=Password must be at least 8 characters')).toBeVisible();

    await page.fill('input[name="password"]', 'StrongH@sh123');
    // Expect visual validation to turn green ideally

    // Accessibility test (Step 9)
    const termsCheckbox = page.locator('#terms-checkbox');
    await expect(termsCheckbox).toHaveAttribute('aria-checked', 'false');
    await termsCheckbox.click();
    await expect(termsCheckbox).toHaveAttribute('aria-checked', 'true');
  });

  // ---------------------------------------------------------
  // STEP 5 & 11: ASYNC JOBS & UX CHAOS
  // ---------------------------------------------------------

  test('Async AI Interview Polling Loop and Graceful Loaders', async ({ page }) => {
    // Navigate straight to a mock interview access portal
    // Assuming backend returns 202 status: "processing", we expect a multi-second hold message
    
    await page.goto('/interview/access');
    await page.fill('input[name="email"]', 'valid_candidate@test.com');
    await page.fill('input[name="access_key"]', 'valid_test_key_abc');
    await page.click('button:has-text("Enter Interview")');

    // Polling UI State Validation
    const loaderMessage = page.locator('text=Generating custom AI interview questions');
    await expect(loaderMessage).toBeVisible({ timeout: 5000 });

    // Assuming it completes eventually, it should push to /interview/uuid
    // Playwright captures the routing push correctly
    await expect(page).toHaveURL(/.*interview\/.*/, { timeout: 30000 });
  });

  // ---------------------------------------------------------
  // STEP 9: UX/UI EDGE CASES & COMPLIANCE
  // ---------------------------------------------------------

  test('Legal and Compliance 404 Prevention', async ({ page }) => {
    await page.goto('/terms');
    await expect(page.locator('h1:has-text("Terms of Service")')).toBeVisible();
    await expect(page.locator('h1:has-text("404")')).toBeHidden();

    await page.goto('/privacy');
    await expect(page.locator('h1:has-text("Privacy Policy")')).toBeVisible();
    await expect(page.locator('h1:has-text("404")')).toBeHidden();
  });
});
