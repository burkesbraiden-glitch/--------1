# 童旅记后端设计记录

## 第 6A-5.2.2 Record Images 安全副本与受保护下载

- `RECORD_IMAGE_UPLOAD_DIR` 独立于任务图片目录：默认 `backend/var/uploads/record-images`，测试默认 `backend/var/testing-uploads/record-images`，测试可以覆盖为临时目录。
- `journey_record_images` 只接受受限的 `task-images/<filename>` 源 key，按 PNG/JPEG/WebP 签名字节生成 UUID4 文件名与 `record-images/{recordId}/{uuid}.{extension}` 相对 key；同源图片在一次操作中只复制一次，但每个 Submission 获得独立深拷贝的 asset 值。
- 写入采用 `record-images/.staging/{recordId}-{operationUuid}` 暂存，复制校验后使用同一根目录内的原子 rename 发布到不可合并、不可覆盖的 `{recordId}` 最终目录；提供只清理本操作目录的幂等 cleanup。
- `GET /api/v1/journey-records/{recordId}/images/{assetId}` 必须携带 JWT，并用现有 JourneyRecord 所有权查询隐藏跨用户记录；只有 finalized 记录可下载。路由不会接受 storage key 或 JWT URL 参数，并以 `inline` 与 `Cache-Control: private` 返回文件。
- 下载解析会验证 snapshot、资产 ID、storage key 根目录、文件大小与实际 MIME；错误响应不包含服务器绝对路径。
- 本阶段不接入 finalize、snapshot 写入、JourneyRecord serializer、Plan 完成校验或并发锁；不修改模型、migration、前端、真实 MySQL 或任务图片现有对外行为，也没有孤儿文件扫描。

## 第 6A-5.2.1 JourneyRecord Snapshot v1

- `journey_records.snapshot` 是 nullable JSON；迁移 `f6a52a1b2d4` 仅增加该列，没有默认值或历史回填。
- `journey_record_snapshots` 提供纯 builder/validator：校验 schemaVersion、结构类型、asset 引用与 `record-images/{recordId}/` 相对 key，并始终返回深拷贝。
- builder 复用现有动态 serializer 的 displayTitle、photoCount 与 noteCount 语义；本阶段不查询数据库、不访问文件系统、不写入 snapshot。
- finalize、Plan completed 校验、图片副本、下载、snapshot serializer、legacy 行为和并发控制均留在后续阶段。

## 第 4C-3 前端联调记录

- 前端已调用既有的真实任务图片上传和认证下载接口；本阶段没有修改 Flask、数据库、migration、图片格式规则或本地文件存储策略。
- 新增统一认证文件传输工具：上传使用 `uni.uploadFile` 的 `image` 字段，H5 下载使用 Authorization fetch、Blob Object URL 与 `cache: no-store`，非 H5 下载使用带 Authorization 的 `uni.downloadFile` 临时路径。
- Remote Task 的 `record.imageUrl` 继续只保存后端返回的认证相对路径；Blob URL、临时路径和上传预览均不写回任务业务数据。`taskStore` 使用用户、Plan、Task 隔离的展示缓存，在上传替换后失效旧缓存并阻止过期 generation 写回。
- `localTaskDrafts` 已删除，记录页基于 `record.displayImagePath` 显示真实认证图片；刷新后会通过 Tasks API 的 `imageUrl` 重新下载恢复。

## 第 4C-2 前端联调记录

- 前端在既有 `frontend/src/api/tasks.js` 上新增 `startTaskSubmission(planId, taskId)`、`updateTaskSubmission(planId, taskId, payload)` 和 `completeTaskSubmission(planId, taskId, payload)`；三个方法均复用统一 request 层并携带 JWT。
- `taskStore` 以 `tasksByPlanId` 中的 Remote Task 作为 `status`、`record.note` 和 `completedAt` 的唯一事实来源；start、PATCH、complete 返回的 Task 统一通过 `upsertRemoteTask()` 替换对应远程条目，不修改展示副本。
- `localTaskDrafts[planId][taskId]` 已不再保存 status 或 note，只保留本地临时 `imagePath`。展示层保留服务器 `record.imageUrl`，本地 imagePath 不覆盖 imageUrl。
- 同一 `userId + planId + taskId` 的 Submission 请求使用串行 Promise 队列；队列响应绑定当前用户会话代号，退出登录或用户切换后旧响应不会写回 Store。
- 任务详情页只在页面局部保存 `noteDraft`，600ms 防抖调用 PATCH；blur、隐藏、卸载和完成前均复用同一保存队列。complete 会等待已发送保存，并携带最新 note，completed 后 PATCH 保持后端返回的 completed 状态与 completedAt。
- Plan 为 ready 时不会自动 start，任务页和详情页使用既有 Plan start action 显式开始探索；not-started Task 必须先调用真实 start 后再记录。
- 本阶段继续允许 `uni.chooseImage` 本地预览，但未接任何 Task Image 上传或认证下载 API，也不会将 imagePath、imageUrl 或 image_url 发送到 Submission API。图片持久化留到第 4C-3。
- 本阶段没有修改后端、数据库结构或 migration。

## 第 4C-1 前端联调记录

- 前端新增 `frontend/src/api/tasks.js`，仅封装真实 Task 查询、生成和详情读取：`getTasks(planId)`、`generateTasks(planId)`、`getTask(planId, taskId)`。
- 第 4C-1 只接真实 Tasks 内容、真实数字 Task id、真实 taskCount 和真实 Task Detail；不接 TaskSubmission 写入，也不接 Task Image 上传或认证下载。
- `taskStore` 继续作为唯一任务 Store，但任务主数据改为 `tasksByPlanId` 中的后端返回 Task，不再从 `mockTasks` 或 `localTaskSessions` 创建业务任务。
- 本地过渡状态放入 `localTaskDrafts[planId][taskId]`，只暂存第 4C-1 需要的 `status`、`note`、`imagePath`；Draft 只有用户实际本地操作时才创建字段，避免遮住服务器已有 submission 数据。
- 展示任务由 Remote Task 与 Local Draft Overlay 合并生成：内容字段、`record.imageUrl` 来自服务器；本地 `status/note/imagePath` 只作为 4C-1 展示覆盖层；远程 Task 对象不被直接修改。
- `ensureTasks(planId, planStatus)` 先 GET tasks；若为空且 Plan 为 `ready` 或 `in-progress`，再显式 POST generate；`draft` 与 `completed` 不自动 generate。
- 同一 `planId` 的 `ensureTasks` 使用模块作用域共享 Promise，避免计划页、任务页、刷新恢复或重复进入导致重复 generate。
- `planStore.syncTaskCount(planId, taskCount)` 负责同步 `plans` 数组和 `currentPlan` 缓存，页面不直接写 `currentPlan.taskCount`。
- 任务详情页使用字符串化 id 比较支持 `task.id = 35` 与路由 `id = "35"`；直接刷新详情页时先恢复 Plan 和任务列表，列表缺失时调用真实 Detail API 兜底。
- 记录页继续读取 `taskStore.currentPlanTasks` 的合并展示任务，因此第 4C-1 的本地 completed、note、imagePath 仍能生成临时探索相册；`sourceTaskId` 去重使用字符串化 id。
- 退出登录或认证失效时清理远程任务缓存、Local Draft、currentTask/currentTaskId、loading/error/generating 和进行中 Promise，防止用户之间串任务或临时记录。
- 4C-2 完成后应删除本地 `status` 和 `note` Draft 逻辑，改用真实 Submission start/PATCH/complete；4C-3 完成后应删除本地 `imagePath` 作为最终记录来源，改用认证图片上传下载和展示缓存。
- 本阶段没有修改后端、数据库结构或 migration。

## 第 4B-3 阶段记录

- 新增 `backend/app/services/task_images.py`，负责 Task 所有权校验复用、上传文件读取、大小限制、签名字节格式识别、安全文件名生成、原子写入、Submission 创建或更新、旧图片替换和事务失败清理。
- 在现有 Tasks Blueprint 下新增两个 JWT 接口：`POST /plans/<plan_id>/tasks/<task_id>/submission/image` 和 `GET /plans/<plan_id>/tasks/<task_id>/submission/image`。
- 图片读取也必须认证；GET 会按当前 JWT 用户查询 Plan，再按 `task_id + plan_id` 查询 Task，跨用户 Plan 返回 `PLAN_NOT_FOUND`，跨 Plan Task 返回 `TASK_NOT_FOUND`。
- 当前 MVP 使用本地文件系统存储，默认上传目录为 `backend/var/uploads/task-images`；运行时目录通过 `.gitignore` 忽略，不放入前端 static，也不进入版本控制。
- 新增配置 `TASK_IMAGE_UPLOAD_DIR` 和 `TASK_IMAGE_MAX_BYTES`，默认最大图片大小为 `10 * 1024 * 1024` bytes；测试通过临时目录覆盖上传目录，避免写入真实开发目录。
- `task_submissions.image_url` 语义调整为服务器内部 storage key，例如 `task-images/8f1998c0c8324a68bc52a21c48019831.png`；禁止保存完整 URL、客户端本地路径、blob/wxfile 路径或服务器绝对路径。
- `serialize_task()` 小范围调整：当 Submission 有图片时，`record.imageUrl` 返回认证下载路径 `/api/v1/plans/{planId}/tasks/{taskId}/submission/image`；没有图片仍返回 `null`，其他 Task 字段不变。
- 图片格式只允许 PNG、JPEG、WebP；服务端按实际签名字节识别格式，并据此决定最终扩展名和 Content-Type，不信任原始扩展名。
- 上传文件名使用 UUID4 hex 加服务端识别出的扩展名，禁止使用用户原始文件名、路径片段或时间戳作为唯一标识。
- 首次上传会自动创建 `in-progress` TaskSubmission；已有 in-progress Submission 会保留 note 并只替换 `image_url`；已有 completed Submission 允许替换图片但保持 `status`、`note` 和 `completed_at`。
- 图片替换顺序为：先写入新文件，再更新数据库并提交，提交成功后删除旧文件；如果数据库提交失败，会 rollback 并删除新文件，保留旧图片。
- GET image 会将 storage key resolve 到上传目录内，并确认最终路径仍位于 `TASK_IMAGE_UPLOAD_DIR` 内；异常路径、缺 Submission、空 image_url 或文件不存在统一返回 `TASK_IMAGE_NOT_FOUND`。
- GET image 返回 `image/png`、`image/jpeg` 或 `image/webp`，`Content-Disposition` 为 inline，`Cache-Control` 为 private。
- 新增 `backend/tests/test_task_images.py` 覆盖上传缺 token、越权、Plan 状态、缺文件、空文件、非法格式、超大文件、PNG/JPEG/WebP、UUID 文件名、内部 storage key、首次创建 Submission、note/completed 兼容、替换清理、DB 失败清理、GET 鉴权、Content-Type 和 list/detail imageUrl。
- 新增 `backend/scripts/phase4b3_task_images_smoke.py`，用于真实 MySQL + 本地文件系统顺序 smoke，并在 finally 中恢复数据库和上传目录基线。
- 本阶段没有数据库结构变更，没有新 migration，没有修改前端；前端仍未接真实图片上传 API。未来生产环境可迁移对象存储和签名 URL。

## 第 4B-2 阶段记录

- 新增 `backend/app/services/task_submissions.py`，负责 TaskSubmission 写入状态机、Plan/Task 所有权检查、note 校验、幂等、`completed_at` 管理、事务提交和唯一约束冲突恢复。
- 在现有 `backend/app/api/v1/tasks.py` Blueprint 下新增三个 JWT 接口：`POST /plans/<plan_id>/tasks/<task_id>/submission/start`、`PATCH /plans/<plan_id>/tasks/<task_id>/submission`、`POST /plans/<plan_id>/tasks/<task_id>/submission/complete`。
- 写入接口先按当前 JWT 用户查询 Plan，再按 `task_id + plan_id` 查询 Task；Plan 不存在或越权返回 404 `PLAN_NOT_FOUND`，Task 不存在或不属于该 Plan 返回 404 `TASK_NOT_FOUND`。
- 只有 `in-progress` Plan 允许写入 TaskSubmission；`draft` 返回 `PLAN_NOT_READY`，`ready` 返回 `PLAN_NOT_STARTED`，`completed` 返回 `PLAN_ALREADY_COMPLETED`。
- `submission/start` 无业务请求字段；无 Submission 时创建 `in-progress`，重复 start 返回现有 Task，已 completed 时返回 `TASK_ALREADY_COMPLETED`，禁止回退状态。
- `PATCH submission` 当前只允许 `note`；note 必须是字符串，允许空字符串，trim 外围空白，保留内部换行和空格，最大 2000 字符。首次 PATCH 自动创建 `in-progress` Submission；completed 后仍可修改 note，但保持 completed 状态和原 `completed_at`。
- `submission/complete` 允许空请求体或仅带 `note`；not-started 可直接创建 completed Submission，in-progress 更新为 completed，completed 重复调用保持幂等，`completed_at` 首次写入后不再重写。
- `completed_at` 使用 `app.utils.time.utc_now()`，不使用本地时间；Task 返回继续复用 `serialize_task()`，因此 GET Tasks / GET Detail 与写入响应结构一致。
- `task_submissions.image_url` 本阶段始终保持 `null`；客户端提交 `imagePath`、`imageUrl` 或 `image_url` 均返回 `VALIDATION_ERROR`，真实图片上传留到第 4B-3。
- 全部 Task 完成后不自动修改 `ExplorationPlan.status`；Plan 继续保持 `in-progress`，旅程结束能力留到后续阶段。
- 新增 `backend/tests/test_task_submissions.py` 覆盖 start、PATCH note、complete、幂等、用户隔离、GET 状态反映、图片字段拒绝和 Plan 不自动完成。
- 新增 `backend/scripts/phase4b2_task_submissions_smoke.py`，用于真实 MySQL 顺序 smoke；本阶段没有新 migration，没有修改前端。

## 第 4B-1 阶段记录

- 新增 `backend/app/services/task_generator.py`，作为服务端 Mock Task Generator；输入为 `ExplorationPlan`，至少使用 `destination`、`age_group`、`interests`，输出固定 3 条 Task 内容定义。
- 故宫模板匹配规范化后的 `故宫`、`故宫博物院`，迁移前端已验收的 3 个任务：找屋顶上的小兽、拍一扇宫门、讲一个故事；数据库 id 仍使用 `tasks.id` 自增 BigInteger，不保存前端字符串 id。
- 非故宫目的地使用稳定通用 fallback：观察代表性细节、寻找颜色和形状、亲子表达与记录；模板结合 destination、ageGroup 和 interests，不随机、不联网、不调用 AI。
- 新增 `backend/app/services/tasks.py`，负责当前用户 Plan 查询、任务列表、任务详情、任务生成、幂等处理、事务和序列化；路由层只读取路径参数、调用 service 并返回统一 JSON。
- 新增 `backend/app/api/v1/tasks.py`，仅注册 `GET /plans/{plan_id}/tasks`、`POST /plans/{plan_id}/tasks/generate`、`GET /plans/{plan_id}/tasks/{task_id}`，全部要求 JWT。
- `GET tasks` 不自动创建任务；没有任务时返回 `tasks: []` 和 `taskCount: 0`，避免读取接口产生写入副作用。
- `POST tasks/generate` 仅允许 `ready` 与 `in-progress` Plan；`draft` 返回 `PLAN_NOT_READY`，`completed` 返回 `PLAN_ALREADY_COMPLETED`。
- 首次生成在一个事务中创建 3 条 Task；重复 generate 返回已有任务和 HTTP 200，不覆盖内容、不增加数量、不改变 id。
- 若数据库已有异常的部分任务集，本阶段不静默补齐，返回 `TASK_SET_INCOMPLETE`，details 包含 `expectedCount` 和 `actualCount`。
- Task API 先按 `plan_id + current user id` 查询 Plan，再按 `task.id + task.plan_id` 查询 Task，越权统一返回 `PLAN_NOT_FOUND` 或 `TASK_NOT_FOUND`，不泄露其他用户数据。
- `serialize_task()` 输出 camelCase：`id`、`planId`、`order`、`title`、`subtitle`、`status`、`ageGroup`、`duration`、`type`、`summary`、`objective`、`steps`、`questions`、`recordMode`、`theme`、`record`、`completedAt`、`createdAt`、`updatedAt`。
- Task status 动态计算：无 submission 返回 `not-started`；有 submission 返回 `task_submissions.status`。record 动态序列化为 `{ imageUrl, note }`；当前不返回 `submissionId`。
- Plan API 的 `taskCount` 已改为真实 `tasks` 数量；`GET /plans` 使用 `selectinload(ExplorationPlan.tasks)` 避免明显 N+1，单 Plan 接口保持同一序列化逻辑。
- 本阶段没有新 migration，没有数据库结构变更，没有前端修改；TaskSubmission 写入 API、任务完成 API、图片上传和前端真实 Tasks 联调留到后续阶段。

## 第 4A 阶段记录

- 新增 `tasks` 表表示一个具体探索计划中的任务内容，字段为 `id`、`plan_id`、`sort_order`、`title`、`subtitle`、`age_group`、`duration`、`task_type`、`summary`、`objective`、`steps`、`questions`、`record_mode`、`theme`、`created_at`、`updated_at`。
- 新增 `task_submissions` 表表示任务当前完成状态和用户记录，字段为 `id`、`task_id`、`status`、`image_url`、`note`、`completed_at`、`created_at`、`updated_at`。
- `tasks` 不保存完成状态和记录内容；`status`、图片 URL 和文字记录属于 `task_submissions`。没有 `TaskSubmission` 行表示未来 API 应返回 `not-started`。
- `TaskSubmission.status` 只允许 `in-progress` 与 `completed`；`not-started` 不落库。`completed_at` 允许为空，未来 Service 层负责约束 completed 必须写入完成时间。
- `TaskSubmission` 不重复保存 `user_id`、`child_id`、`plan_id` 或 `destination`；用户隔离未来通过 `Task -> ExplorationPlan -> user_id` 校验。
- `ExplorationPlan.tasks` 与 `Task.plan` 为一对多；`Task.submission` 与 `TaskSubmission.task` 为一对零或一，通过 `task_submissions.task_id UNIQUE` 保证。
- `record_mode` 当前来自前端自然语言展示文本，不是稳定枚举，数据库使用 `String(255)`，暂不加值域 CheckConstraint。
- 当前真实前端未使用 `points` 与 `illustration`，4A 不落库。`taskCount` 未来由 `tasks` 实际数量动态计算。
- 本阶段没有任务 Seed，没有任务 API，没有文件上传 API，没有任务生成器，没有修改前端。

## 第 3C-2 前端联调记录

- 前端新增 Guide API 模块和轻量 guideStore，对接 `GET /plans/{id}/guide` 与 `POST /plans/{id}/guide/generate`。
- Guide 页先恢复真实 currentPlan，再读取 Guide；仅在 `GUIDE_NOT_FOUND` 时自动 generate。
- 刷新和重复进入同一 Plan 会读取已存在 Guide，避免重复创建 GuideCard。
- Plan 切换时前端先清旧 Guide 会话，避免 Plan A/B 串 Guide。
- 当前 Guide Generator 仍是服务端 Mock Generator，不接 OpenAI 或真实 AI。

## 已确认基础约定

- API 前缀统一为 `/api/v1`。
- 数据库字段使用 `snake_case`。
- API JSON 字段使用 `camelCase`。
- `users` 不保存 child age。
- `exploration_plans` 不保存 `task_count`，API 层后续动态计算。
- `guide_cards` 不保存 `destination`，目的地统一来自关联 `exploration_plans.destination`。
- 第 3B Service 层创建探索计划时必须验证 `child.user_id` 属于当前 JWT 用户，禁止创建跨用户计划。
- `tasks` 与 `task_submissions` 是 `1:0..1` 关系。
- `task_submissions` 当前 MVP 通过 `task_id UNIQUE` 保证单任务单提交。
- `record_items` 使用 `source_task_id` 去重。
- `favorites` 使用 `user_id + target_type + target_id` 唯一。
- 使用 `APP_ENV`，不使用 `FLASK_ENV`。
- MySQL 驱动使用 PyMySQL。

## 当前后端阶段拆分

### 第 0 阶段

已完成环境检查、数据库设计和 API 契约设计。

### 第 1A 阶段

建立 Flask 后端基础工程，不进入业务 API 开发：

- 使用 `D:\python\python.exe` 创建 `backend/.venv`。
- 使用普通 CPython 3.14，不使用 3.14t 自由线程版本。
- 安装并验证基础依赖：Flask、Flask-SQLAlchemy、Flask-Migrate、Flask-JWT-Extended、PyMySQL、python-dotenv、Flask-Cors、pytest。
- 使用 Application Factory 创建 Flask app。
- 创建 extensions 对象并在 `create_app()` 中执行 `init_app()`。
- 注册 `/api/v1` Blueprint。
- 提供 `GET /api/v1/health` 健康检查。
- 提供统一 JSON 成功和失败响应。
- 提供 404、405、500 统一 JSON 错误处理。
- 使用 pytest 覆盖 app 创建、健康检查和 404 响应。

第 1A 阶段不连接 MySQL，不创建数据库，不执行 SQL，不创建 migrations，不创建业务模型，不开发 auth、children、plans、tasks、records API。

### 第 1B 阶段

建立本地 MySQL 开发连接，不进入业务模型和业务 API：

- 使用 MySQL `login-path` 管理员访问方式，不在项目文件、终端输出或报告中保存管理员密码。
- 本地开发数据库为 `tonglvji`，字符集 `utf8mb4`，排序规则 `utf8mb4_0900_ai_ci`。
- 本地开发应用用户为 `tonglvji_app`，Host 为 `127.0.0.1`。
- 应用用户权限只授予 `tonglvji.*`，不授予全局权限、管理员权限或 `GRANT OPTION`。
- 本地真实配置写入 `backend/.env`，该文件被 `.gitignore` 忽略。
- `backend/.env.example` 保持占位值，不写入真实密钥、密码或完整连接串。
- DevelopmentConfig 从 `DATABASE_URL` 读取 MySQL 连接，并启用 `pool_pre_ping` 和本地适用的 `pool_recycle`。
- 健康检查会执行真实数据库检查，成功时返回 `database.status = connected` 和 `database.dialect = mysql`。
- 数据库不可用时，健康检查返回 HTTP 503 和统一错误码 `DATABASE_UNAVAILABLE`，不返回密码、完整连接串或内部堆栈。
- `backend/scripts/bootstrap_mysql.py` 仅用于本地开发初始化数据库、应用用户和 `.env`。
- `backend/scripts/mysql_smoke.py` 用于真实 MySQL smoke，验证应用创建、`SELECT 1`、当前数据库、dialect 和 health connected。
- pytest 保持为单元测试，不依赖本机真实 MySQL 密码。
- 已初始化 Flask-Migrate 骨架 `backend/migrations/`，未生成 migration revision，未执行 `flask db migrate` 或 `flask db upgrade`。

第 1B 阶段不创建 users、children、exploration_plans、tasks、records 等业务表，不创建业务模型，不开发 auth、children、plans、tasks、records API。

### 第 2A 阶段

建立首批业务基础模型和第一个正式 migration，仅包含用户与孩子档案：

- SQLAlchemy `MetaData` 已配置稳定命名规则：`ix_<table>_<column>`、`uq_<table>_<column>`、`ck_<table>_<constraint>`、`fk_<table>_<column>_<referred_table>`、`pk_<table>`。
- 新增 UTC 时间工具 `utc_now()`，MySQL `DateTime` 保存无时区 UTC 值。
- `users` 表字段：`id`、`phone`、`nickname`、`city`、`wechat_openid`、`created_at`、`updated_at`。
- `users` 不保存 `age`、`age_group`、`interests`。
- `users.phone` 和 `users.wechat_openid` 均允许为空、唯一并建立索引。
- `users` 使用检查约束保证 `phone IS NOT NULL OR wechat_openid IS NOT NULL`，避免无登录标识用户。
- `children` 表字段：`id`、`user_id`、`name`、`age`、`city`、`age_group`、`interests`、`is_default`、`created_at`、`updated_at`。
- `children.age` 使用检查约束允许 0 到 18。
- `children.age_group` 使用检查约束限制为 `3-6` 或 `7-12`。
- `children.interests` 使用 JSON 类型，默认空列表。
- `users` 与 `children` 为一对多关系，`children.user_id` 外键指向 `users.id`，数据库使用 `ON DELETE CASCADE`。
- `is_default` 字段已保留；每个用户唯一默认孩子规则留到 service 层处理。
- 首个 migration revision 为 `b88ed65c69db_create_users_and_children.py`，只创建 `users` 和 `children`。
- 已执行 migration upgrade，当前数据库 revision 为 `b88ed65c69db`。
- 当前未插入用户或孩子数据。

第 2A 阶段不开发认证 API、children CRUD API，不创建 exploration_plans、guide_cards、tasks、task_submissions、journey_records、favorites、badges 等后续阶段表。

### 第 2B-1 阶段

建立认证 API，不修改数据库结构，不创建新 migration：

- 新增 `/api/v1/auth/send-code`，当前 development/testing 只模拟发送成功并返回 `cooldownSeconds`，不会返回或记录验证码。
- 固定验证码仅在 development/testing 使用，ProductionConfig 禁用固定验证码；生产环境未接真实短信时返回 `SMS_NOT_CONFIGURED`。
- 新增 `/api/v1/auth/login`，手机号格式使用 `^1[3-9]\d{9}$`，开发/测试环境校验固定验证码。
- 手机号首次登录只创建 `User`，默认 `nickname = 童旅用户`，不创建 Child、计划、任务或收藏。
- 手机号重复登录按 `users.phone` 查找已有用户，不创建重复用户。
- 新增 `/api/v1/auth/mock-wechat-login`，仅 development/testing 可用，production 返回 `FEATURE_DISABLED`。
- Mock 微信 openid 使用 `mock:` 加 `SHA256(mockCode)` 短摘要生成，不直接保存用户输入。
- 登录成功只签发 JWT access token，JWT identity 使用 `str(user.id)`。
- access token 过期时间通过 `JWT_ACCESS_TOKEN_HOURS` 配置，开发默认 168 小时。
- 新增 `/api/v1/auth/me`，通过 `@jwt_required()` 读取 JWT identity，再使用 `db.session.get(User, user_id)` 查询当前用户。
- `/auth/me` 当前只返回 `id`、`phone`、`nickname`、`city`，不返回 children、currentChild、计划或任务统计。
- 新增 `/api/v1/auth/logout`，当前不做服务器端 token 吊销，只确认请求携带有效 token；客户端需要删除本地 access token。
- 当前 logout 不做服务器端 token 吊销，access token 在自然过期前理论上仍可验证；真正 token 撤销留到后续有明确需求时再设计。
- Flask-JWT-Extended 错误已接入统一 JSON：缺 token 返回 `UNAUTHORIZED`，无效 token 返回 `INVALID_TOKEN`，过期 token 返回 `TOKEN_EXPIRED`。
- 真实认证行为由 `backend/scripts/phase2b1_auth_smoke.py` 验证，普通 pytest 不依赖本机真实 MySQL 密码或 `.env`。

第 2B-1 阶段不开发 children CRUD，不创建默认孩子，不开发 refresh token、JWT blocklist、真实短信服务或真实微信 OAuth。

### 第 2B-2 阶段

建立孩子档案 API，不修改数据库结构，不创建新 migration：

- 新增 `/api/v1/children` 列表接口，必须携带 JWT，只返回当前用户自己的孩子。
- 列表接口按默认孩子优先、`created_at` 升序排序，返回 `children` 和 `currentChild`。
- 新增 `/api/v1/children` 创建接口，创建成功返回 HTTP 201 和 `Child created`。
- 新增 `/api/v1/children/<id>` 详情接口，只允许读取当前用户自己的孩子。
- 新增 `/api/v1/children/<id>` 更新接口，只允许更新当前用户自己的孩子。
- 越权读取或更新其他用户 child 时返回 404 `CHILD_NOT_FOUND`，不泄露目标 child 是否真实存在。
- API JSON 使用 camelCase：`ageGroup`、`isDefault`；不返回 `user_id`、`created_at`、`updated_at`。
- API 层当前只接受 3 到 12 岁，数据库层仍保留 0 到 18 的宽松约束。
- `ageGroup` 由 age 推导：3 到 6 为 `3-6`，7 到 12 为 `7-12`。
- 请求传入 `ageGroup` 时必须与 age 一致；PATCH 只更新 age 时会自动同步 ageGroup。
- `interests` 缺失默认为空列表；必须是字符串数组；每项 trim、非空、最多 30 字，最多 10 项，并按原顺序去重。
- 当前用户第一个孩子强制 `isDefault = true`，即使请求传入 false。
- 后续创建孩子时，`isDefault = true` 会在同一事务中把当前用户其他孩子置为 false。
- PATCH `isDefault = true` 会在同一事务中切换默认孩子。
- 不允许把当前默认孩子 PATCH 为 `isDefault = false`，返回 409 `DEFAULT_CHILD_REQUIRED`。
- 默认孩子规则只作用于当前用户，不影响其他用户。
- 真实 children 行为由 `backend/scripts/phase2b2_children_smoke.py` 验证；普通 pytest 不依赖本机真实 MySQL 密码或 `.env`。

第 2B-2 阶段不开发 DELETE child，不开发计划、讲解卡、任务、记录、收藏、徽章 API，不生成新 migration。

### 第 2C-1 阶段

完成前端真实认证联调，不修改后端业务 API、数据库结构或 migration：

- 前端新增统一 `VITE_API_BASE_URL` 配置，默认本地开发指向 `http://127.0.0.1:5000/api/v1`。
- 前端新增统一 `uni.request` 请求层，负责拼接 API Base URL、JSON 请求头、Bearer token、统一成功数据和错误对象。
- 前端新增 auth API 模块，对接 `/auth/send-code`、`/auth/login`、`/auth/mock-wechat-login`、`/auth/me` 和 `/auth/logout`。
- 前端统一使用 `tonglvji_auth` 保存 `{ token, userInfo }`，首次恢复真实认证时清理旧 `tonglvji_mock_auth`。
- 手机号验证码发送走真实 Flask `/auth/send-code`，成功后按后端返回的 `cooldownSeconds` 开始倒计时。
- 手机号登录走真实 Flask `/auth/login`，验证码正确性由后端判断，前端不再本地比较固定验证码。
- Mock 微信登录走真实 Flask `/auth/mock-wechat-login`，当前使用稳定开发 `mockCode`，不接微信 SDK、OAuth 或 openid。
- 应用启动、登录页、我的页和底部导航通过 `restoreSession()` 调用 `/auth/me` 验证本地 token，并通过共享 Promise 防止重复 `/auth/me`。
- 客户端 logout 会尝试调用真实 `/auth/logout`，无论后端结果如何都清理本地 token、用户信息和登录状态。
- 登录页和我的页保持当前验收视觉，仅替换数据和认证逻辑。
- 当前阶段不修改 `childStore` 为真实 API，不开发孩子档案联调、计划、讲解卡、任务、记录、收藏或新后端业务 API。

### 第 2C-2 阶段

完成前端真实孩子档案联调，不修改后端 children API、数据库结构或 migration：

- 前端新增 children API 模块，复用统一 `uni.request` 请求层，并对接 `GET /children`、`POST /children`、`GET /children/{id}` 和 `PATCH /children/{id}`。
- `childStore` 继续作为唯一孩子档案 Store，保留 `currentChild`、`ageGroup`、`interests` 和 `setAgeGroup()` 的旧页面兼容字段。
- `childStore` 新增真实远程状态：`children`、`hasRemoteChild`、`isLoading`、`isLoaded`、`error` 和 `loadedForUserId`。
- 旧页面使用安全 fallback 避免空数据导致页面崩溃；我的页使用 `hasRemoteChild` 区分真实孩子与 fallback，不把 fallback 展示为已保存数据库孩子。
- `fetchChildren(userId)` 调用真实 `GET /children`，通过共享请求防止同一用户重复并发加载。
- 当 `loadedForUserId` 与当前用户不同，会先清空远程孩子状态，防止退出后新用户短暂看到上一用户孩子资料。
- 无孩子时不自动创建默认孩子，我的页显示真实空状态，并提供轻量“完善孩子档案”表单。
- 创建孩子通过真实 `POST /children`，成功后立即同步 `children`、`currentChild`、`ageGroup` 和 `interests`。
- 更新孩子通过真实 `PATCH /children/{id}`，成功后更新 Pinia 中对应孩子和当前孩子展示。
- 退出登录时只清理前端孩子会话状态，不删除数据库孩子数据。
- 当前阶段不开发多孩子切换、删除孩子、探索计划 API、讲解卡 API、任务 API、记录 API、收藏 API或第 3 阶段能力。

### 第 3A 阶段

建立探索计划和讲解卡模型，生成第二个正式 migration，并验证真实 MySQL schema；本阶段只完成模型、migration 和 schema，不开发 plans API、guide API、tasks、records、favorites 或 badges：

- 前端真实计划结构来自 `frontend/src/stores/plan.js` 和 `frontend/src/mock/plans.js`：`id`、`title`、`destination`、`ageGroup`、`duration`、`taskCount`、`interests`、`status`、`taskIds`。
- 其中 `title`、`destination`、`ageGroup`、`duration`、`interests`、`status` 是计划业务持久化字段；`taskCount` 和 `taskIds` 是当前 Mock/UI 展示字段，不在 `exploration_plans` 落库。
- `exploration_plans` 表字段：`id`、`user_id`、`child_id`、`title`、`destination`、`age_group`、`duration`、`interests`、`status`、`created_at`、`updated_at`。
- `exploration_plans.age_group` 使用 CheckConstraint 限制为 `3-6` 或 `7-12`，不使用数据库 Enum。
- `exploration_plans.status` 使用 CheckConstraint 限制为 `draft`、`ready`、`in-progress`、`completed`，数据库默认值为 `draft`。
- `exploration_plans.user_id` 外键指向 `users.id`，数据库使用 `ON DELETE CASCADE`。
- `exploration_plans.child_id` 外键指向 `children.id`，数据库使用 `ON DELETE RESTRICT`，避免误删孩子档案时自动删除探索历史。
- `User.exploration_plans`、`Child.exploration_plans`、`ExplorationPlan.user` 和 `ExplorationPlan.child` 已建立 ORM 关系；Child 关系不配置 ORM 删除级联。
- 第 3B Service 层创建计划时必须验证 child 属于当前 JWT 用户，数据库层当前不创建触发器验证 `child.user_id == plan.user_id`。
- 前端真实讲解卡结构来自 `frontend/src/pages/guide/index.vue`：`child_intro` 对应“讲给孩子听”的多段文本数组，`questions` 是字符串数组，`focus_items` 是字符串数组，`destination` 从当前 plan 读取。
- 页面中的 `audioState`：`idle`、`playing`、`paused` 是前端局部播放状态，不保存为数据库字段。
- `guide_cards` 表字段：`id`、`plan_id`、`child_intro`、`questions`、`focus_items`、`audio_url`、`created_at`、`updated_at`。
- `guide_cards.plan_id` 外键指向 `exploration_plans.id`，数据库使用 `ON DELETE CASCADE`，并通过唯一索引保证一个计划最多一张讲解卡。
- `guide_cards` 不保存 `destination`；API 后续需要目的地时从关联 `ExplorationPlan.destination` 返回，避免重复和不一致。
- `GuideCard` 不保存 `audio_status`、`is_playing`、`is_paused` 或 `play_state`，只保留可空 `audio_url`。
- 第二个正式 migration 为 `0a9cec9dc9f8_create_exploration_plans_and_guide_cards.py`，仅创建 `exploration_plans` 和 `guide_cards` 及相关索引、外键、唯一约束和检查约束。
- 已执行 `flask db upgrade`，当前数据库 revision 为 `0a9cec9dc9f8`。
- 第 3A.1 已验证该 migration 可逆：可 downgrade 回 `b88ed65c69db`，保留 `users` 与 `children`，删除 `guide_cards` 与 `exploration_plans`，并可再次 upgrade 回 `0a9cec9dc9f8`。
- `backend/scripts/phase3a_plan_schema_smoke.py` 用于真实 MySQL schema smoke，只输出 `phase3a plan schema checks passed`。

### 第 3B-1 阶段

建立探索计划 API，不修改数据库结构，不生成新 migration，不创建 GuideCard：

- 新增 `/api/v1/plans` 创建接口，必须携带 JWT。
- 新增 `/api/v1/plans` 列表接口，只返回当前 JWT 用户自己的计划。
- 新增 `/api/v1/plans/<id>` 详情接口，查询条件包含 `plan.id` 和当前 `user_id`；不存在或属于其他用户均返回 404 `PLAN_NOT_FOUND`。
- 新增 `/api/v1/plans/<id>` 更新接口，只允许修改 `title`、`destination`、`duration`、`interests`；不允许修改 `childId`、`ageGroup`、`status`、`taskCount`、`taskIds` 或 `userId`。
- 新增 `/api/v1/plans/<id>/start`，状态机为 `ready -> in-progress`；`in-progress` 重复 start 幂等成功；`draft` 返回 409 `PLAN_NOT_READY`；`completed` 返回 409 `PLAN_ALREADY_COMPLETED`。
- 创建计划时，如果请求未传 `childId`，后端选择当前用户的默认孩子；旧数据没有默认孩子时回退到当前用户第一条孩子。
- 当前用户没有任何孩子时，创建计划返回 409 `CHILD_REQUIRED`，不自动创建 Child，不使用前端 fallback Child。
- 创建计划时必须验证 child 属于当前 JWT 用户；其他用户的 child 返回 404 `CHILD_NOT_FOUND`。
- `ageGroup` 缺省时使用选中 child 的 `age_group`；请求传入时必须与 child 的 `age_group` 一致，否则返回 400 `VALIDATION_ERROR`。
- 创建成功时显式保存 `status = ready`，符合当前首页一次性提交完整计划信息的流程。
- API 序列化使用 camelCase：`id`、`title`、`destination`、`ageGroup`、`duration`、`taskCount`、`interests`、`status`、`childId`、`createdAt`、`updatedAt`。
- `taskCount` 当前 API 动态返回 `0`，数据库仍不保存 `task_count`；未来创建 tasks 表后由真实任务数量动态计算。
- 创建 Plan 不自动创建 GuideCard；`guide_cards` 数量在本阶段不因计划 API 增加，服务端讲解卡生成留到第 3B-2。
- `backend/scripts/phase3b1_plans_smoke.py` 用于真实 MySQL plans smoke，只输出 `phase3b1 plans checks passed`。

### 第 3B-2 阶段

建立服务端 Mock 讲解卡生成与读取 API，不修改数据库结构，不生成新 migration，不接真实 AI：

- 新增 `/api/v1/plans/<id>/guide` 读取接口，必须携带 JWT。
- 新增 `/api/v1/plans/<id>/guide/generate` 生成接口，必须携带 JWT。
- Guide 查询先按当前 JWT 用户和 `plan_id` 查询 ExplorationPlan；计划不存在或属于其他用户均返回 404 `PLAN_NOT_FOUND`。
- GET guide 只读取，不自动生成；计划存在但 GuideCard 不存在时返回 404 `GUIDE_NOT_FOUND`，`guide_cards` 数量不变化。
- POST generate 仅允许 `ready`、`in-progress`、`completed` 状态生成；`draft` 返回 409 `PLAN_NOT_READY`。
- POST generate 如果 GuideCard 已存在，直接返回已有记录和 HTTP 200，不重新生成、不修改内容、不创建第二条。
- POST generate 如果 GuideCard 不存在，调用服务端 Mock Guide Generator 创建 GuideCard，保存 `child_intro`、`questions`、`focus_items`、`audio_url`，成功返回 HTTP 201。
- 并发情况下依赖 `guide_cards.plan_id UNIQUE` 做最终保护；如果提交时出现唯一约束冲突，服务层 rollback 后重新查询并返回已存在的 GuideCard。
- 新增 `backend/app/services/guide_generator.py`，当前只使用 Python 模板，不发起 HTTP 请求，不调用 OpenAI、第三方 AI SDK 或任何外部 AI API。
- 故宫模板匹配 `故宫` 和 `故宫博物院`，尽量保留前端已验收的讲解卡内容：“讲给孩子听”映射为 `child_intro`，“可以先问孩子”映射为 `questions`，“今天重点看”映射为 `focus_items`。
- 非故宫目的地使用稳定通用 fallback，根据 `plan.destination`、`plan.age_group` 和 `plan.interests` 生成儿童友好的介绍、亲子提问和观察重点；同一 Plan 重复生成结果稳定。
- Guide API 序列化使用 camelCase：`id`、`planId`、`destination`、`childIntro`、`questions`、`focusItems`、`audioUrl`、`createdAt`、`updatedAt`。
- GuideCard 不保存 `destination`，API 返回的 `destination` 来自关联 `guide.plan.destination`。
- GuideCard 不保存 `audioStatus`、`isPlaying`、`isPaused` 或 `playState` 等前端局部播放状态，只保留可空 `audio_url`。
- 创建 Plan 仍然不自动创建 GuideCard，保持第 3B-1 行为。
- `backend/scripts/phase3b2_guides_smoke.py` 用于真实 MySQL guide smoke，只输出 `phase3b2 guide checks passed`。

### 第 3C-1 阶段

完成前端真实 Plan 联调，不修改后端、不修改数据库结构、不生成 migration、不接 Guide API：

- 新增 `frontend/src/api/plans.js`，复用统一 request 层，对接 `POST /plans`、`GET /plans`、`GET /plans/{id}`、`PATCH /plans/{id}` 和 `POST /plans/{id}/start`，全部使用 `auth: true`。
- `planStore` 继续作为唯一 Plan Store，不新增 remotePlanStore 或 backendPlanStore。
- `planStore.plans` 和 `planStore.currentPlan` 第 3C-1 后只表示真实后端 Plan，初始为 `[]` 和 `null`，不再使用 `mockPlans[0]` 作为真实计划 fallback。
- 当前计划选择使用 `tonglvji_current_plan_selection`，只保存 `{ userId, planId }`，不保存整个 Plan 对象；恢复时必须验证 `userId` 与当前真实用户一致。
- `fetchPlans(userId)` 调用真实 `GET /plans`，同一用户并发复用同一个请求；不同用户加载前先清空旧计划，避免用户 B 短暂看到用户 A 的计划。
- GET /plans 成功后优先恢复 storage 中仍存在的计划，否则选择后端列表第一条；后端列表当前按 `updatedAt`、`createdAt` 降序。
- 首页创建计划前会恢复真实认证、加载真实孩子档案，并校验选择的 `ageGroup` 与真实 `currentChild.ageGroup` 一致。
- 未登录时禁止创建本地假计划，提示登录后跳转登录页；没有真实孩子时禁止使用 fallback Child，提示完善孩子档案并跳转我的页。
- 首页创建真实 Plan 只发送 `title`、`destination`、`duration`、`interests`、`childId` 和 `ageGroup`，不发送 `status`、`taskCount`、`taskIds`、`id` 或 `userId`。
- `startExploration()` 调用真实 `POST /plans/{id}/start`；后端成功后才更新 currentPlan/plans 并进入任务页，失败时不进入任务页。
- `taskCount` 保持后端真实值，当前仍为 0；前端展示层区分 `serverTaskCount`、`localTaskCount` 和 `availableTaskCount`，不把临时任务数量写回真实 Plan。
- 当前 tasks API 尚未开发。为保持已验收任务和记录流程，`taskStore` 暂时为每个真实 Plan 建立独立 `localTaskSessions[planId]`。
- 每个真实 Plan 第一次需要任务时，从现有 `mockTasks` 深拷贝生成自己的本地任务会话，并把副本 `planId` 设置为真实 Plan id；该状态只存在于前端 taskStore，不写回 Plan、后端或数据库。
- 不同真实 Plan 的任务状态、`record.imagePath` 和 `record.note` 不共享，防止 Plan A/B 串完成状态、照片或文字。
- `currentPlan = null` 时任务列表返回空数组，不展示无归属 Mock tasks。
- Guide 页面第 3C-1 只恢复真实 currentPlan 并显示真实 destination，不调用 Guide API；如果 destination 不是故宫，正文仍是本地过渡内容，真实 Guide 接入留到第 3C-2。
- logout 时清理 childStore、planStore 和 taskStore 的前端会话状态，不删除数据库 Plan。
- 临时任务兼容删除条件：后端真实 tasks API、task_submissions API 完成，前端 taskStore 完成真实任务联调后，删除 `localTaskSessions`、本地任务模板兼容、`availableTaskCount` 过渡逻辑和记录页对 Mock tasks 的依赖。
