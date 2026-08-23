# E2E 测试说明

## 安装浏览器

```bash
npm install @playwright/test --legacy-peer-deps
npx playwright install --with-deps chromium
```

## 运行测试

### 运行所有测试
```bash
npx playwright test
```

### 运行特定测试文件
```bash
npx playwright test auth.spec.ts
```

### 运行特定测试
```bash
npx playwright test -g "应该能够登录"
```

### 调试模式
```bash
npx playwright test --debug
```

### 显示浏览器界面
```bash
npx playwright test --headed
```

## 测试环境

### 环境变量

创建 `.env.test` 文件：

```env
BASE_URL=http://localhost:5173
API_URL=http://localhost:8000
```

### 测试数据库

E2E 测试使用独立的测试数据库，不会影响开发数据。

## 测试覆盖

### auth.spec.ts
- 用户注册
- 用户登录
- 登录错误处理
- 用户登出

### projects.spec.ts
- 项目列表
- 创建项目
- 查看项目详情
- 编辑项目
- 删除项目

### upload.spec.ts
- 上传页面显示
- 文件选择
- 文件格式验证
- 文件大小验证
- 上传进度
- 上传完成

### jobs.spec.ts
- 任务列表
- 任务筛选
- 任务详情
- 暂停任务
- 恢复任务
- 取消任务
- 重试任务
- 错误日志查看

## 测试数据

### 测试文件

将测试视频文件放在 `e2e/fixtures/` 目录下：

```
e2e/fixtures/
├── test-video.mp4          # 小型测试视频（< 10MB）
└── test-file.exe           # 用于测试格式错误的文件
```

### 测试用户

默认测试用户：
- 邮箱: `test@example.com`
- 密码: `password123`

## 持续集成

测试会在 CI 环境中自动运行：

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

## 故障排除

### 浏览器未安装

```bash
npx playwright install --with-deps chromium
```

### 测试超时

增加超时时间：

```typescript
test('慢速测试', async ({ page }) => {
  test.setTimeout(60000); // 60 秒
  // ...
});
```

### 网络问题

使用网络模拟：

```typescript
await page.route('**/*', route => route.continue());
```

## 最佳实践

1. **使用数据属性选择器**：避免依赖 CSS 类名
   ```typescript
   page.locator('[data-testid="submit-button"]')
   ```

2. **等待元素可见**：避免竞态条件
   ```typescript
   await expect(page.locator('.element')).toBeVisible();
   ```

3. **使用测试ID**：便于定位元素
   ```html
   <button data-testid="login-button">登录</button>
   ```

4. **清理测试数据**：每个测试后清理
   ```typescript
   test.afterEach(async ({ page }) => {
     await cleanupTestData();
   });
   ```

5. **使用 page fixtures**：复用页面配置
   ```typescript
   test.use({ viewport: { width: 1280, height: 720 } });
   ```
