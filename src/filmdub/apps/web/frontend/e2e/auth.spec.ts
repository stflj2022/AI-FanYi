import { test, expect } from '@playwright/test';

test.describe('用户认证', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('应该显示登录页面', async ({ page }) => {
    await expect(page).toHaveTitle(/AI-FanYi/);
    await expect(page.locator('h1')).toContainText('登录');
  });

  test('应该能够注册新用户', async ({ page }) => {
    // 点击注册链接
    await page.click('text=注册');

    // 填写注册表单
    const timestamp = Date.now();
    const username = `testuser_${timestamp}`;
    const email = `test_${timestamp}@example.com`;

    await page.fill('input[name="username"]', username);
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', 'password123');
    await page.fill('input[name="confirmPassword"]', 'password123');

    // 提交表单
    await page.click('button[type="submit"]');

    // 验证注册成功
    await expect(page).toHaveURL(/.*login/);
    await expect(page.locator('.toast, .notification')).toContainText('注册成功');
  });

  test('应该能够登录', async ({ page }) => {
    // 填写登录表单
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');

    // 提交表单
    await page.click('button[type="submit"]');

    // 验证登录成功并跳转到 Dashboard
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.locator('h1')).toContainText('仪表盘');
  });

  test('应该显示登录错误', async ({ page }) => {
    // 填写错误的登录信息
    await page.fill('input[name="email"]', 'wrong@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');

    // 提交表单
    await page.click('button[type="submit"]');

    // 验证显示错误消息
    await expect(page.locator('.error, .toast-error')).toBeVisible();
  });

  test('应该能够登出', async ({ page }) => {
    // 先登录
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard/);

    // 点击登出按钮
    await page.click('button:has-text("登出")');

    // 验证返回到登录页面
    await expect(page).toHaveURL(/.*login/);
  });
});
