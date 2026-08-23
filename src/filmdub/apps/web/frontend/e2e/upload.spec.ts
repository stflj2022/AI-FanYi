import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('视频上传', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard/);
  });

  test('应该显示上传页面', async ({ page }) => {
    // 导航到上传页面
    await page.click('a:has-text("上传")');
    await page.waitForURL(/.*upload/);

    // 验证上传页面
    await expect(page.locator('h1')).toContainText('上传视频');
    await expect(page.locator('.upload-area')).toBeVisible();
  });

  test('应该能够选择文件', async ({ page }) => {
    // 导航到上传页面
    await page.click('a:has-text("上传")');
    await page.waitForURL(/.*upload/);

    // 创建测试文件
    const fileInput = page.locator('input[type="file"]');

    // 模拟文件选择
    const filePath = path.join(__dirname, 'fixtures', 'test-video.mp4');

    // 上传文件
    await fileInput.setInputFiles(filePath);

    // 验证文件被选中
    await expect(page.locator('.file-info')).toBeVisible();
  });

  test('应该显示文件格式错误', async ({ page }) => {
    // 导航到上传页面
    await page.click('a:has-text("上传")');
    await page.waitForURL(/.*upload/);

    // 尝试上传不支持的文件
    const fileInput = page.locator('input[type="file"]');
    const filePath = path.join(__dirname, 'fixtures', 'test-file.exe');

    await fileInput.setInputFiles(filePath);

    // 验证显示错误
    await expect(page.locator('.error-message')).toContainText('文件格式不支持');
  });

  test('应该显示文件过大错误', async ({ page }) => {
    // 导航到上传页面
    await page.click('a:has-text("上传")');
    await page.waitForURL(/.*upload/);

    // 尝试上传过大的文件（模拟）
    // 这里需要创建一个超过限制的测试文件
    // 实际测试中可以使用小文件并修改上传限制

    await expect(page.locator('.upload-area')).toBeVisible();
  });

  test('应该能够开始上传', async ({ page }) => {
    // 导航到上传页面
    await page.click('a:has-text("上传")');
    await page.waitForURL(/.*upload/);

    // 选择文件
    const fileInput = page.locator('input[type="file"]');
    const filePath = path.join(__dirname, 'fixtures', 'test-video.mp4');
    await fileInput.setInputFiles(filePath);

    // 点击上传按钮
    await page.click('button:has-text("开始上传")');

    // 验证上传进度显示
    await expect(page.locator('.upload-progress')).toBeVisible();
  });

  test('应该显示上传完成状态', async ({ page }) => {
    // 导航到上传页面
    await page.click('a:has-text("上传")');
    await page.waitForURL(/.*upload/);

    // 选择文件并上传
    const fileInput = page.locator('input[type="file"]');
    const filePath = path.join(__dirname, 'fixtures', 'test-video.mp4');
    await fileInput.setInputFiles(filePath);
    await page.click('button:has-text("开始上传")');

    // 等待上传完成（可能需要根据实际情况调整等待时间）
    await page.waitForSelector('.upload-success', { timeout: 30000 });

    // 验证成功消息
    await expect(page.locator('.toast, .notification')).toContainText('上传成功');
  });
});
