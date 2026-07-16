# 童旅记第 4C-2 TaskSubmission 前端联调设计

## 目标

让任务开始、文字记录和完成状态以真实后端 Task 为唯一事实来源，同时保留尚未上传的本地临时图片路径。

## 范围

- 前端仅新增 Submission start、note PATCH、complete 调用。
- Remote Task 的 `status`、`record.note`、`completedAt` 仅由 API 返回 Task 更新。
- `localTaskDrafts[planId][taskId]` 仅保存 `imagePath`。
- 不接图片上传或认证下载，不修改后端、数据库或 migration。

## 数据流

`taskStore` 用 `tasksByPlanId` 保存服务器 Task，并通过 `upsertRemoteTask(task)` 替换同 Plan 下的同 id 任务。展示对象复制 Remote Task，仅叠加本地 `record.imagePath`，不修改 Remote Task。

每个 Submission 操作以 `userId + planId + taskId` 为键进入串行 Promise 队列。队列项携带当前会话代号；退出登录清空队列和请求状态并递增会话代号，旧响应即使返回也不会写回 Store。详情页以局部 `noteDraft` 承接输入，600ms 后将保存操作入同一队列；完成前取消定时器、等待已排队保存，再以最新 `noteDraft` 调用 complete。

## 页面行为

- Plan 为 `ready` 时，任务可阅读，Tasks 与详情页显示“开始探索后即可记录”，由用户点击既有 Plan start action 后才开放记录。
- Plan 为 `in-progress` 且 Task 为 `not-started` 时，显示“开始任务”；start 成功后更新 Remote Task。
- `in-progress` 或 `completed` Task 的 note 可编辑；completed 后 PATCH 保持后端返回的 completed 状态和 completedAt。
- 本地图片只能在 Plan 为 `in-progress`、任务已开始后选择，且仅做本地预览。

## 验证

新增静态集成检查与 Pinia Mock API 流程检查；更新 4C-1 Overlay 检查为 Remote status/note + 本地 imagePath 语义。完成后运行前端全量检查、H5 build、后端 pytest 和既有 Tasks/Submission/Image smoke。
