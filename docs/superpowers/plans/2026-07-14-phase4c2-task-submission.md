# 童旅记第 4C-2 TaskSubmission 前端联调 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 TaskSubmission start、note 保存和 complete 接入真实前端状态流，且不触及图片 API 或后端。

**Architecture:** Store 保存并替换远程 Task；页面只持有短暂 noteDraft。每个 `userId + planId + taskId` 使用同一串行队列，刷新、登出和并发响应均不会把过期状态写回。

**Tech Stack:** uni-app Vue 3、Pinia、JavaScript、现有 request 层、Node ESM 检查脚本。

---

### Task 1: 先写 4C-2 失败检查

**Files:**
- Create: `frontend/scripts/phase4c2-task-submission-integration-check.mjs`
- Create: `frontend/scripts/phase4c2-task-submission-flow-check.mjs`
- Modify: `frontend/scripts/phase4c1-task-draft-overlay-check.mjs`

- [ ] 编写 API 边界、Remote upsert、仅 imagePath Draft、Remote progress、队列、ready/start 和无图片 API 的静态断言。
- [ ] 编写 Pinia Mock API 流程：start、PATCH、complete、completed 后 PATCH、Plan 隔离、会话失效与本地 imagePath 隔离。
- [ ] 运行两个新脚本，确认它们因 4C-2 API/Store 逻辑尚未存在而失败。

### Task 2: 接入 Store 与 API

**Files:**
- Modify: `frontend/src/api/tasks.js`
- Modify: `frontend/src/stores/task.js`

- [ ] 新增 `startTaskSubmission`、`updateTaskSubmission`、`completeTaskSubmission`，全部为 `auth: true`。
- [ ] 添加 Remote Task upsert、会话绑定的每任务串行队列、请求状态和中文错误映射。
- [ ] 删除 Draft status/note 合并、`markTaskCompleted` 和 note 写入；只保留本地 imagePath action。
- [ ] 运行新脚本，确认 API/Store 检查转绿。

### Task 3: 接入 Tasks 与详情页交互

**Files:**
- Modify: `frontend/src/pages/tasks/index.vue`
- Modify: `frontend/src/pages/task-detail/index.vue`

- [ ] ready Plan 显示显式开始探索，复用 planStore action。
- [ ] 详情页增加 ready/not-started 操作门控、start、600ms note 保存、完成前 flush、completed 后 note 编辑和本地图片选择门控。
- [ ] 运行流程检查，确认 Remote Task 是 status/note 的唯一来源。

### Task 4: 文档和完整验证

**Files:**
- Modify: `README.md`
- Modify: `docs/backend-design.md`

- [ ] 记录 4C-2 的真实 Submission 边界与 4C-3 图片延后边界。
- [ ] 运行所有前端检查、H5 build、backend pytest 与三个 smoke 脚本。
- [ ] 以 390 x 844 检查 Tasks、详情和记录页面的基本布局。
