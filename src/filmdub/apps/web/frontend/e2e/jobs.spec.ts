import { test, expect } from '@playwright/test';

test.describe('任务管理', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard/);
  });

  test('应该显示任务列表', async ({ page }) => {
    // 导航到任务页面
    await page.click('a:has-text("任务")');
    await page.waitForURL(/.*jobs/);

    // 验证任务列表页面
    await expect(page.locator('h1')).toContainText('任务列表');
    await expect(page.locator('.job-list')).toBeVisible();
  });

  test('应该能够筛选任务', async ({ page }) => {
    // 导航到任务页面
    await page.click('a:has-text("任务")');
    await page.waitForURL(/.*jobs/);

    // 选择状态筛选
    await page.selectOption('select[name="status"]', 'running');

    // 验证筛选结果
    await expect(page.locator('.job-item')).toHaveCount(0); // 或者根据实际数据调整
  });

  test('应该能够查看任务详情', async ({ page }) => {
    // 导航到任务页面
    await page.click('a:has-text("任务")');
    await page.waitForURL(/.*jobs/);

    // 点击第一个任务
    await page.click('.job-item:first-child');

    // 验证任务详情页面
    await expect(page.locator('h1')).toContainText('任务详情');
    await expect(page.locator('.job-info')).toBeVisible();
    await expect(page.locator('.task-progress')).toBeVisible();
  });

  test('应该能够暂停任务', async ({ page }) => {
    // 导航到任务页面并点击第一个任务
    await page.click('a:has-text("任务")');
    await page.waitForURL(/.*jobs/);
    await page.click('.job-item:first-child');

    // 点击暂停按钮
    await page.click('button:has-text("暂停")');

    // 验证暂停成功
    await expect(page.locator('.toast, .notification')).toContainText('任务已暂停');
    await expect(page.locator('.task-status')).toContainText('已暂停');
  });

  test('应该能够恢复任务', async ({ page }) => {
    // 导航到任务页面并点击已暂停的任务
    await page.click('a:has-text("任务")');
    await page.waitForURL(/.*jobs/);
    await page.click('.job-item[data-status="waiting"]');

    // 点击恢复按钮
    await page.click('button:has-text("恢复")');

    // 验证恢复成功
    await expect(page.locator('.toast, .notification')).toContainText('任务已恢复');
    await expect(page.locator('.task-status')).toContainText('运行中');
  });

  test('应该能够取消任务', async ({ page }) => {
    // 导航到任务页面并点击任务
    await page.click('a:has-text("任务")');
    await page.waitForURL(/.*jobs/);
    await page.click('.job-item:first-child');

    // 点击取消按钮并确认
    page.on('dialog', dialog => dialog.accept());
    await page.click('button:has-text("取消")');

    // 验证取消成功
    await expect(page.locator('.toast, .notification')).toContainText('任务已取消');
    await expect(page.locator('.task-status')).toContainText('已取消');
  });

  test('应该能够重试失败的任务', async ({ page }) => {
    // 导航到任务页面并点击失败的任务
    await page.click('a:has-text("任务")');
    await page.waitForURL(/.*jobs/);
    await page.click('.job-item[data-status="failed"]');

    // 点击重试按钮
    await page.click('button:has-text("重试")');

    // 验证重试成功
    await expect(page.locator('.toast, .notification')).toContainText('任务已重新调度');
    await expect(page.locator('.task-status')).toContainText('已调度');
  });

  test('应该显示任务错误日志', async ({ page }) => {
    // 导航到任务页面并点击失败的任务
    await page.click('a:has-text("任务")');
    await page.waitForURL(/.*jobs/);
    await page.click('.job-item[data-status="failed"]');

    // 点击查看错误日志
    await page.click('button:has-text("查看错误")');

    // 验证错误日志显示
    await expect(page.locator('.error-modal')).toBeVisible();
    await expect(page.locator('.error-log')).toBeVisible();
  });
});
