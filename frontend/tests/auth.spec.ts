import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('Should block weak passwords during registration', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/register');
    
    await page.fill('input[type="email"]', 'automated_test@domain.com');
    await page.fill('input[type="password"]', 'weak');
    
    // The UI should display strength meter as Weak and button should be disabled
    const strengthMeter = page.locator('text=Weak');
    await expect(strengthMeter).toBeVisible();
    
    const submitButton = page.locator('button:has-text("Create Account")');
    await expect(submitButton).toBeDisabled();
  });

  test('Should redirect non-HR users away from HR dashboard', async ({ page, context }) => {
    // Mock candidate authentication state in localStorage and cookies
    await context.addInitScript(() => {
      localStorage.setItem('auth_token', 'mocked_candidate_token');
    });

    await page.goto('http://localhost:3000/dashboard/hr');
    
    // Access should be blocked and user redirected
    await expect(page).toHaveURL('http://localhost:3000/dashboard/candidate');
  });
});
