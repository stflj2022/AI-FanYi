import { test, expect } from '@playwright/test';

test.describe('项目管理', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard/);
  });

  test('应该显示项目列表', async ({ page }) => {
    // 导航到项目页面
    await page.click('a:has-text("项目")');
    await page.waitForURL(/.*projects/);

    // 验证项目列表页面
    await expect(page.locator('h1')).toContainText('项目列表');
  });

  test('应该能够创建新项目', async ({ page }) => {
    // 导航到项目页面
    await page.click('a:has-text("项目")');

    // 点击新建项目按钮
    await page.click('button:has-text("新建项目")');

    // 填写项目表单
    const timestamp = Date.now();
    await page.fill('input[name="title"]', `测试项目 ${timestamp}`);
    await page.fill('textarea[name="description"]', '这是一个测试项目');
    await page.selectOption('select[name="sourceLanguage"]', 'en');
    await page.selectOption('select[name="targetLanguage"]', 'zh');

    // 提交表单
    await page.click('button[type="submit"]');

    // 验证创建成功
    await expect(page.locator('.toast, .notification')).toContainText('项目创建成功');
    await expect(page.locator(`text=测试项目 ${timestamp}`)).toBeVisible();
  });

  test('应该能够查看项目详情', async ({ page }) => {
    // 导航到项目页面
    await page.click('a:has-text("项目")');
    await page.waitForURL(/.*projects/);

    // 点击第一个项目
    await page.click('.project-card, .project-item:first-child');

    // 验证项目详情页面
    await expect(page.locator('h1')).toContainText('项目详情');
    await expect(page.locator('.project-info')).toBeVisible();
  });

  test('应该能够编辑项目', async ({ page }) => {
    // 导航到项目页面并点击第一个项目
    await page.click('a:has-text("项目")');
    await page.waitForURL(/.*projects/);
    await page.click('.project-card, .project-item:first-child');

    // 点击编辑按钮
    await page.click('button:has-text("编辑")');

    // 修改项目信息
    await page.fill('input[name="title"]', '更新后的项目名称');

    // 保存更改
    await page.click('button:has-text("保存")');

    // 验证更新成功
    await expect(page.locator('.toast, .notification')).toContainText('项目更新成功');
    await expect(page.locator('h2')).toContainText('更新后的项目名称');
  });

  test('应该能够删除项目', async ({ page }) => {
    // 导航到项目页面
    await page.click('a:has-text("项目")');
    await page.waitForURL(/.*projects/);

    // 点击删除按钮（需要确认）
    page.on('dialog', dialog => dialog.accept());
    await page.click('.project-card:first-child button:has-text("删除")');

    // 验证删除成功
    await expect(page.locator('.toast, .notification')).toContainText('项目删除成功');
  });
});
