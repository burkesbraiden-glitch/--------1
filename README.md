# 童旅记

## 第 4C-3 阶段记录

- 任务图片已接入真实 `POST /plans/{planId}/tasks/{taskId}/submission/image` 上传与受 JWT 保护的图片下载接口；上传复用统一 API base 和既有 `tonglvji_auth` token 来源，不将 JWT 放入 URL，也不手动设置 multipart boundary。
- H5 通过带 Authorization 的 `fetch`、`cache: no-store` 和 Blob Object URL 显示图片；非 H5 使用 `uni.downloadFile` 的临时文件路径。展示路径仅存于前端图片缓存，不写回 Remote Task。
- `taskStore.taskImageCache` 按 `userId:planId:taskId` 隔离，并使用独立 generation、共享下载 Promise 与 session epoch 防止旧下载、旧用户或旧缓存覆盖新图片。替换图片会先写入后端返回的 Task，再失效缓存、revoke Blob URL 并认证重下。
- `localTaskDrafts` 和最终 `record.imagePath` 依赖已删除。详情页仅在上传中使用局部 `pendingPreviewPath`；任务详情和探索相册均只展示 `record.displayImagePath`。
- completed Task 替换图片后，`status`、`record.note` 和 `completedAt` 继续以上传接口返回的 Remote Task 为准。退出登录会清空图片缓存、使在途结果失效并撤销全部 H5 Blob URL。

## 第 4C-2 阶段记录

- 前端已接入真实 TaskSubmission 写入：任务开始、文字记录 PATCH 和任务完成全部复用 `frontend/src/api/tasks.js` 与统一 request 层，均携带 JWT。
- Remote Task 的 `status`、`record.note` 和 `completedAt` 现在只由后端返回的 Task 更新；`taskStore.upsertRemoteTask()` 替换对应 Plan 下的远程任务，任务页、详情页和记录页同步读取新结果。
- `localTaskDrafts[planId][taskId]` 已删除本地 `status` 与 `note`，现在只保存未上传的 `imagePath`；本地图片仍可预览，刷新后允许消失。
- 同一用户、Plan、Task 的 Submission 请求进入串行队列；详情页使用 600ms 防抖 `noteDraft`，完成前会取消未触发防抖、等待已发保存，并以最新文字调用 complete，避免旧 PATCH 覆盖完成结果。
- Plan 为 `ready` 时任务可以查看但不会自动开始；任务页和详情页提供显式“开始探索”。任务为 `not-started` 时必须先开始任务，completed 后仍可修正文字记录。
- 本阶段未接入任务图片上传或认证下载，绝不向 Submission API 发送 `imagePath`、`imageUrl` 或 `image_url`；图片持久化仍留在第 4C-3。
- 本阶段没有修改后端、数据库结构或 migration。

## 第 4C-1 阶段记录

- 前端已新增真实 Tasks API 模块，对接 `GET /plans/{id}/tasks`、`POST /plans/{id}/tasks/generate` 和 `GET /plans/{id}/tasks/{taskId}`，全部复用统一 request 层并携带 JWT。
- `taskStore` 的任务内容来源已切换为真实后端 Tasks，使用真实 MySQL 数字 Task id，不再从 `mockTasks` 创建业务任务数组。
- `localTaskSessions` 不再作为任务主数据；第 4C-1 使用 `tasksByPlanId` 保存远程任务，并用 `localTaskDrafts[planId][taskId]` 暂存本地 `status`、`note`、`imagePath`。
- 展示任务由 Remote Task + Local Draft Overlay 合并生成，远程 Task 对象保持服务器事实，不直接写入本地完成状态、文字或图片临时路径。
- 进入计划页、任务页或记录页时会恢复真实 Plan 并确保 Tasks；当真实任务为空且 Plan 为 `ready` 或 `in-progress` 时显式调用 generate，同 Plan 共享请求链避免重复生成。
- `taskCount` 通过 `planStore.syncTaskCount()` 同步到 `plans` 和 `currentPlan` 缓存，计划页显示真实任务数。
- 任务详情页支持数字 Task id 与路由字符串 id 匹配；列表中找不到时使用真实 Task Detail API 作为刷新兜底。
- 记录页继续读取 `taskStore.currentPlanTasks` 的合并展示结果，临时 completed、note、imagePath 仍可形成探索相册；`sourceTaskId` 去重已统一字符串化。
- 本阶段未接 TaskSubmission 写入 API，未调用 start、PATCH note 或 complete；4C-2 将删除本地 `status/note` Draft 并接入真实 Submission。
- 本阶段未接 Task Image 上传或认证下载；4C-3 将删除本地 `imagePath` 作为最终记录来源并接入真实图片缓存。
- 本阶段没有修改后端、没有新 migration。

## 第 4B-3 阶段记录

- 后端已新增真实任务图片上传 API：`POST /api/v1/plans/{plan_id}/tasks/{task_id}/submission/image`，字段名固定为 `image`，必须携带 JWT。
- 后端已新增受 JWT 保护的图片读取 API：`GET /api/v1/plans/{plan_id}/tasks/{task_id}/submission/image`，会继续校验当前用户拥有 Plan 且 Task 属于该 Plan。
- 当前图片使用服务器本地文件系统存储，默认目录为 `backend/var/uploads/task-images`；该运行时目录被忽略，不进入版本控制。
- `task_submissions.image_url` 只保存内部 storage key，例如 `task-images/<uuid>.png`，不保存 HTTP URL、客户端本地路径、blob/wxfile 路径或服务器绝对路径。
- 上传只允许 PNG、JPEG、WebP，并按文件签名字节识别真实格式；SVG、GIF 和其他文件会被拒绝。
- 上传大小默认限制为 10 MiB；文件名由 UUID4 hex 生成，不使用用户原始文件名。
- 首次上传会自动创建 `in-progress` TaskSubmission；替换图片只更新同一条 Submission，并在数据库提交成功后删除旧文件。
- completed 任务允许替换图片，但保持 `status`、`note` 和 `completed_at` 不变。
- Task list/detail 的 `record.imageUrl` 不返回内部 storage key，而返回认证下载路径 `/api/v1/plans/{planId}/tasks/{taskId}/submission/image`。
- 前端尚未接真实图片 API，当前仍保留本地临时图片流程；未来生产环境可迁移对象存储和签名 URL。
- 本阶段没有新 migration，没有修改前端。

## 第 4B-2 阶段记录

- 后端已新增 TaskSubmission 写入 API：`POST /api/v1/plans/{plan_id}/tasks/{task_id}/submission/start`、`PATCH /api/v1/plans/{plan_id}/tasks/{task_id}/submission`、`POST /api/v1/plans/{plan_id}/tasks/{task_id}/submission/complete`。
- Task start 会在 `in-progress` Plan 下创建 `in-progress` submission；重复 start 幂等返回同一 Task；已完成任务不允许重新 start。
- PATCH 当前只允许更新 `note`，会 trim 外围空白、允许空字符串、限制 2000 字符；首次 PATCH 会自动创建 `in-progress` submission，已完成任务仍可修正 note 且不改变 `completed_at`。
- complete 可从未开始或进行中直接进入 `completed`，首次完成写入 UTC `completed_at`；重复 complete 幂等，不重写完成时间。
- 写入接口继续使用 Task 序列化，GET list / detail 会立即反映 `status`、`record.note` 和 `completedAt`。
- 用户隔离继续通过当前 JWT 用户拥有的 Plan 校验；跨用户 Plan 返回 `PLAN_NOT_FOUND`，Task 不属于该 Plan 返回 `TASK_NOT_FOUND`。
- `image_url` 当前仍保持为空，客户端提交 `imagePath` / `imageUrl` / `image_url` 会被拒绝；图片上传留到第 4B-3。
- 全部 Task 完成后不会自动 complete ExplorationPlan；前端仍未接真实 Submission，仍保留当前本地任务记录兼容。
- 本阶段没有新 migration，没有修改前端。

## 第 4B-1 阶段记录

- 后端已新增服务端 Mock Task Generator；当前不是 AI，不接 OpenAI 或任何外部 AI API。
- 新增任务 API：`GET /api/v1/plans/{plan_id}/tasks`、`POST /api/v1/plans/{plan_id}/tasks/generate`、`GET /api/v1/plans/{plan_id}/tasks/{task_id}`。
- `GET tasks` 只读取，不自动生成；只有 `POST tasks/generate` 会为 `ready` 或 `in-progress` Plan 生成 3 个任务。
- 任务生成保持幂等：已有完整 3 条任务时直接返回现有任务；异常的部分任务集返回 `TASK_SET_INCOMPLETE`。
- Task API 按当前 JWT 用户校验 Plan，实现用户隔离；Task status 和 record 由 `task_submissions` 动态序列化，`tasks` 表不保存状态和记录。
- Plan API 的 `taskCount` 已改为根据真实 `tasks` 数量动态计算，`exploration_plans` 仍不保存 `task_count`。
- 当前仍未开发 TaskSubmission 写入 API、任务完成 API、图片上传 API；前端仍然使用 `localTaskSessions`，未接真实 Tasks API。

## 第 4A 阶段记录

- 后端已新增任务内容表 `tasks` 与任务完成状态表 `task_submissions`，第三个正式 migration 为 `c795c3738e73_create_tasks_and_task_submissions.py`。
- `tasks` 只保存任务内容；不保存 `status`、`record`、`image_path`、`note`，也不重复保存 `user_id`、`child_id`。
- `task_submissions` 保存单个任务当前提交状态和用户记录；无 Submission 行表示未来 API 应计算为 `not-started`，数据库中的 `status` 只允许 `in-progress`、`completed`。
- `taskCount` 未来由 `tasks` 实际数量动态计算；当前没有任务 Seed，没有任务 API，没有修改前端。

`frontend/src/package.json` 仅用于 Node 阶段检查脚本按 ESM 导入 src 下源码。

## 第 3C-2 阶段记录

- 前端已接入真实 Guide API：读取 Flask GuideCard，缺失时自动调用服务端 generate。
- 刷新 Guide 页会优先读取已存在 Guide，同一 Plan 不重复创建 GuideCard。
- Plan 间 Guide 会话隔离，切换 Plan 时先清旧 Guide 再加载新 Guide。
- 当前 Guide Generator 仍是服务端 Mock Generator，不是真实 AI；真实 AI 留到后续阶段。

童旅记是一个亲子旅行学习 App，帮助家长把普通旅行变成孩子能够观察、发现、提问、表达和成长的探索过程。

当前阶段：第 3C-1 阶段，前端真实 Plan 联调已完成，Guide 仍留到第 3C-2。

## 目录

- frontend/：经典 uni-app Vue 3 + Vite 前端项目。
- backend/：Flask 后端工程，当前包含 MySQL 本地开发连接、健康检查、认证 API、孩子档案 API、探索计划 API、探索计划模型和讲解卡模型。
- docs/：产品说明、实施计划和设计参考。

## 当前约束

- 前端第 0-6 阶段已完成。
- 后端第 1A 阶段已完成。
- 后端第 1B 阶段已完成。
- 后端第 2A 阶段已完成。
- 后端第 2B-1 阶段已完成。
- 后端第 2C-2 阶段已完成。
- 后端第 3A 阶段已完成。
- 后端第 3A.1 阶段已完成。
- 后端第 3B-2 阶段已完成。
- 前端当前处于第 3C-1 阶段。
- MySQL 已连接本地开发数据库 `tonglvji`。
- 已建立 `users`、`children`、`exploration_plans` 和 `guide_cards` 业务表。
- 已建立第二个正式 migration：`0a9cec9dc9f8_create_exploration_plans_and_guide_cards.py`。
- 已建立手机号登录、Mock 微信登录、`/auth/me` 和客户端式 logout。
- 已建立孩子档案列表、创建、详情和更新 API。
- 已建立 ExplorationPlan 和 GuideCard ORM 模型。
- 已建立探索计划创建、列表、详情、更新和开始探索 API。
- 已建立服务端 Mock Guide Generator、讲解卡生成 API 和讲解卡读取 API。
- 讲解卡生成保持幂等；同一个探索计划最多持久化一张 GuideCard。
- 讲解卡 API 按当前 JWT 用户隔离计划，不泄露其他用户计划是否存在。
- 前端已建立统一 API 配置、`uni.request` 请求层和 auth API 模块。
- 前端登录页已接入真实 `send-code`、手机号登录、Mock 微信登录、JWT 保存、`/auth/me` session 恢复和客户端 logout。
- 前端已建立 children API 模块，`childStore` 已接入真实 `GET /children`、`POST /children` 和 `PATCH /children/{id}`。
- 我的页已接入真实 `currentChild`、无孩子空状态、孩子档案创建/更新、刷新恢复和退出登录孩子会话清理。
- 前端已建立 plans API 模块，`planStore` 已接入真实 `GET /plans`、`POST /plans`、`GET /plans/{id}`、`PATCH /plans/{id}` 和 `POST /plans/{id}/start`。
- `currentPlan` 使用真实后端 Plan id，并通过 `tonglvji_current_plan_selection` 按 `userId + planId` 恢复。
- 首页创建探索计划会校验登录状态、真实孩子档案和孩子年龄组；未登录或无真实孩子时不会创建本地假计划。
- 当前 tasks 仍未后端化；每个真实 Plan 暂时使用独立本地任务模板会话，避免不同计划之间串任务状态、照片和文字。
- 任务临时兼容会在真实 tasks API、task_submissions API 和 taskStore 后端联调完成后删除。
- 不开发孩子删除、任务、记录、收藏等业务 API。
- `exploration_plans` 不保存 `task_count`，任务数未来由 tasks 表动态计算。
- 计划 API 当前返回 `taskCount = 0`，但不落库。
- `guide_cards` 不保存 `destination`，目的地统一来自关联计划。
- 当前创建 Plan 不自动创建 GuideCard；只有 `POST /plans/{id}/guide/generate` 会创建 GuideCard。
- 当前讲解卡生成不是真实 AI，不接 OpenAI 或任何外部 AI API。
- `guide_cards` 不保存 `destination`，API 返回的 destination 来自关联 Plan。
- 第 3C-1 不接 Guide API；Guide 页面只读取真实 Plan 的 destination，讲解内容仍保持本地过渡，真实 Guide 接入留到第 3C-2。
