# 04: 视频文件上传

**What to build:**
实现视频文件上传功能，支持拖拽上传、大文件上传、进度显示、以及上传后的媒体元数据提取。用户可以上传视频文件到 MinIO，并查看视频的时长、分辨率、编码等信息。

**Blocked by:** 01-web-ui-foundation, 02-user-authentication, 03-project-management-ui

**Status:** ready-for-agent

- [ ] 创建 Upload Service
- [ ] 实现文件上传 API（POST /api/v1/uploads）
- [ ] 实现上传进度查询 API（GET /api/v1/uploads/{id}）
- [ ] 集成 MinIO SDK 上传文件
- [ ] 使用 FFprobe 提取视频元数据
- [ ] 创建 Media Asset 记录（关联到 Project）
- [ ] 实现上传状态跟踪（pending, uploading, ready, failed）
- [ ] 创建上传组件（UploadArea，使用 react-dropzone）
- [ ] 实现拖拽上传功能
- [ ] 实现上传进度条显示
- [ ] 实现上传错误处理和重试
- [ ] 创建视频预览组件（上传后显示第一帧）
- [ ] 创建媒体信息显示组件（时长、分辨率、编码）
- [ ] 实现上传文件类型和大小验证
- [ ] 实现前端上传状态管理
- [ ] 编写上传功能测试（包括大文件模拟）
