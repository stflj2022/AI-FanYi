# 02: 用户认证系统

**What to build:**
实现完整的用户认证功能，包括注册、登录、JWT Token 生成和验证、密码哈希、以及登录状态持久化。完成后用户可以注册账号、登录系统，并在前端保持登录状态。

**Blocked by:** 01-web-ui-foundation

**Status:** ready-for-agent

- [ ] 实现 User 模型的 CRUD 操作
- [ ] 实现密码哈希和验证（使用 bcrypt）
- [ ] 实现 JWT Token 生成和验证
- [ ] 实现 Refresh Token 机制
- [ ] 创建注册 API 端点（POST /api/v1/auth/register）
- [ ] 创建登录 API 端点（POST /api/v1/auth/login）
- [ ] 创建 Token 刷新端点（POST /api/v1/auth/refresh）
- [ ] 创建登出端点（POST /api/v1/auth/logout）
- [ ] 实现 JWT 依赖注入（FastAPI Depends）
- [ ] 创建权限装饰器（@require_auth, @require_admin）
- [ ] 创建登录页面（Login 组件）
- [ ] 创建注册页面（Register 组件）
- [ ] 实现前端 Token 存储（localStorage + HttpOnly Cookie）
- [ ] 实现前端请求拦截器（自动添加 JWT Token）
- [ ] 实现前端认证状态管理（Zustand）
- [ ] 实现路由保护（未登录重定向到登录页）
- [ ] 编写认证相关测试（单元测试 + 集成测试）
