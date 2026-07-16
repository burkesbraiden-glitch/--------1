# 童旅记第 4C-3 任务图片前端联调 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让童旅记任务图片通过真实认证上传和下载接口在详情页与记录页稳定显示。

**Architecture:** 使用统一认证文件工具完成平台差异传输；Store 维护会话隔离、generation 防乱序的展示缓存，页面只消费展示路径而不修改 Remote Task。

**Tech Stack:** uni-app、Vue 3、Pinia、JavaScript、H5 fetch/Blob、uni.uploadFile、uni.downloadFile。

---

### Task 1: 先建立失败的 4C-3 检查

**Files:**
- Create: `frontend/scripts/phase4c3-task-image-integration-check.mjs`
- Create: `frontend/scripts/phase4c3-task-image-cache-flow-check.mjs`
- Modify: `frontend/scripts/phase4c1-task-draft-overlay-check.mjs`
- Modify: `frontend/scripts/phase3c1-task-compatibility-check.mjs`

- [ ] 写入静态约束和 Mock 文件传输流程断言。
- [ ] 运行两个新脚本，确认它们因缺少 4C-3 实现而失败。

### Task 2: 统一认证文件传输

**Files:**
- Modify: `frontend/src/utils/request.js`
- Create: `frontend/src/utils/authenticatedFile.js`
- Modify: `frontend/src/api/tasks.js`

- [ ] 导出受控 URL、Authorization 与认证失效辅助能力。
- [ ] 实现 H5 Blob 和非 H5 临时路径下载，以及无 multipart boundary 的上传。
- [ ] 运行静态检查，确认 API 与认证约束通过。

### Task 3: Store 图片缓存与 Remote Task 更新

**Files:**
- Modify: `frontend/src/stores/task.js`

- [ ] 删除 localTaskDrafts 与 imagePath 展示层。
- [ ] 实现按用户、Plan、Task 隔离的缓存、共享下载 Promise、generation 与 cleanup。
- [ ] 实现上传后 upsert、失效、revoke、强制重下和会话失效保护。
- [ ] 运行缓存流程脚本，确认上传、替换、隔离、乱序与 reset 行为通过。

### Task 4: 页面接入与文档

**Files:**
- Modify: `frontend/src/pages/task-detail/index.vue`
- Modify: `frontend/src/pages/record/index.vue`
- Modify: `frontend/src/stores/recordJourney.mjs`
- Modify: `README.md`
- Modify: `docs/backend-design.md`

- [ ] 详情页仅用 pendingPreviewPath 作为上传瞬时预览，成功后显示 displayImagePath。
- [ ] 记录页预取并只显示 displayImagePath。
- [ ] 更新阶段文档与过期检查断言。

### Task 5: 完整回归

**Files:**
- Verify only

- [ ] 运行全部 `frontend/scripts/*.mjs`。
- [ ] 运行 `npm run build:h5`，预期输出 `DONE Build complete.`。
- [ ] 运行 `backend` pytest 与三个 4B smoke 脚本。
