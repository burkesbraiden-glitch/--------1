# 童旅记 FE-R2 设计文档：探索完成与成长记录恢复闭环

## 1. 文档目的与边界

**FE-R2 = Plan Completion + JourneyRecord Loop Recovery。**

本设计将已确认的产品决策固化为后续 implementation plan 的唯一输入，补齐 FE-R0 遗留的两个 P1：

1. 前端没有 `POST /plans/{id}/complete` 的正式用户入口。
2. JourneyRecord 自动创建失败可能被静默吞掉，用户没有稳定的恢复入口。

本轮仅创建本设计文档；不实施功能、不运行迁移、不写数据库、不修改生产代码，且不执行 `git add`、`git commit` 或 `git push`。

### 1.1 已确认的产品决策

| 决策 | 已确认结果 |
| --- | --- |
| 完成探索的唯一入口 | 任务列表页 |
| 不作为入口的页面 | 最后一个任务详情页、计划页 |
| 完成成功后的停留位置 | 仍留在任务列表页 |
| 进入成长记录的方式 | 用户主动点击“查看成长记录” |
| 成长记录详情路由 | `/pages/record-detail/index?planId=<planId>` |
| 记录封存 | 不自动执行；由既有详情页中的用户显式 finalize 流程负责 |

### 1.2 范围

后续实现可评估的前端范围仅为：

```text
frontend/src/api/plans.js
frontend/src/stores/plan.js
frontend/src/stores/record.js
frontend/src/pages/tasks/index.vue
frontend/src/pages/task-detail/index.vue
frontend/tests/*
frontend/scripts/*
```

本轮和 FE-R2 均不修改：

```text
backend/*
migrations/*
database schema
```

后端已提供并继续作为业务事实来源：

```text
POST /plans/{id}/complete
POST /plans/{id}/journey-record
```

不进入 FE-R3 及后续阶段：已完成任务的图文修正 UX、讲解音频、Mock 登录边界、真实水彩资产重构、通知、真实 AI、收藏、新 API、数据库 schema 或 migration。

## 2. 已核对的现有契约

### 2.1 Plan 完成

后端 `complete_plan` 只接受 `in-progress` 计划；若已经完成则幂等地返回既有 Plan。服务端会重新校验正式任务集与每个 TaskSubmission 的 `completed` 状态，条件不满足时返回 `PLAN_TASKS_INCOMPLETE`。因此前端的 `completedCount === totalTasks && totalTasks > 0` 仅用于决定是否展示入口，绝不能代替服务端的业务校验。

成功响应中的 Plan 才能将本地 `plans` 与 `currentPlan` 更新为 `completed`。禁止直接改写 `currentPlan.status` 伪造完成，也禁止在服务端失败后保留伪完成状态。

### 2.2 JourneyRecord

`POST /plans/{id}/journey-record` 对接既有 create-or-get 语义：已有记录时返回已有记录，而不是创建第二条。JourneyRecord 的“存在”与 `finalized` 是不同状态；FE-R2 成功 ensure 后通常得到的仍是 `draft` 记录。

现有任务详情页在任务完成后直接调用 `createJourneyRecord(planId)`，catch 后返回 `null`。后续实现必须保留“任务完成后尽早确保 draft 存在”的业务意图，但把 API 调用、加载、错误、重试、去重、会话隔离的所有权收敛到 Record Store。

记录详情页继续使用已有 `loadJourneyRecordDetail(planId)`。不得创建第二套详情页，也不得在 FE-R2 调用 finalize。

### 2.3 会话与认证边界

FE-R2 继承 FE-R1：`getCurrentSession()` 取得请求所属会话，`isCurrentSession()` 决定结果是否仍可写回。过期 session 的 success、error、finally 都不得污染新 session；共享 Promise 也不得跨 session 使用。认证错误 `UNAUTHORIZED`、`INVALID_TOKEN`、`TOKEN_EXPIRED` 或 HTTP 401 统一进入 `endUserSession()`，不能仅显示为普通的 JourneyRecord retry 错误。

## 3. 目标闭环与顺序

```text
观察任务全部完成
  → 用户在任务列表点击“完成本次探索”
  → completeExploration(planId, userId)
  → POST /plans/{id}/complete
  → 服务端成功返回 completed Plan
  → 更新 Plan Store
  → recordStore.ensureJourneyRecord(planId)
  → 成功：显示“探索完成”，可查看成长记录
  → 失败：显示已完成与“重新生成成长记录”恢复入口
  → 用户进入详情页，整理标题 / 小结 / 封面
  → 用户自行执行既有 finalize 流程
```

关键顺序不可交换：不得先把 UI 或 Store 伪设为 `completed`，再请求后端；不得在 Plan complete 失败时 ensure JourneyRecord；不得为了重试记录而再次 complete Plan。

## 4. Plan Completion 设计

### 4.1 展示门槛与入口

仅当任务列表当前 Plan 满足下列全部条件时，显示“完成本次探索”主按钮：

```text
Plan.status === 'in-progress'
completedCount === totalTasks
totalTasks > 0
```

任务列表是唯一主入口，承载完整旅程闭环；任务详情页不新增完成 Plan 入口。CTA 放在既有任务进度与任务列表语境中，以补充的“完成探索卡”呈现，不改变页面结构、底部导航或 AI 宠物规则。

### 4.2 Plan Store 职责

在 `frontend/src/api/plans.js` 增加 `plansApi.completePlan(id)`，调用：

```text
POST /plans/{id}/complete
```

Plan Store 提供类似 `completeExploration(planId, userId)` 的动作，并承担：

1. 捕获当前 session，调用 completePlan。
2. 仅在 session 仍有效时，用响应 Plan 同步 `plans`、`currentPlan` 与持久选择状态；保留当前 Plan 的选择。
3. 对同一 `session + planId` 的并发操作复用同一 active Promise，阻止重复点击产生多条独立请求。
4. 仅在相同有效 session 中更新 loading、error 与 active Promise；旧请求的 finally 不得清理新请求状态。
5. 网络或业务失败时不更新为 `completed`。

页面在该动作进行中显示“正在完成…”并禁用按钮。请求完成后，页面以服务端返回的状态为准重新协调当前 Plan 与任务数据。

### 4.3 业务拒绝与恢复

若服务端返回 `PLAN_TASKS_INCOMPLETE`，Plan 必须保持 `in-progress`。页面显示：

> 还有任务未完成，请刷新后检查

恢复操作是重新获取当前 Plan 与 Tasks 的真实状态，而不是绕过服务端校验或强制完成。其他可重试的 complete 失败显示“完成探索失败”，并仅重试 complete 操作。认证错误则结束用户会话。

## 5. JourneyRecord ensure 设计

### 5.1 统一所有权

Record Store 新增 `ensureJourneyRecord(planId)`（具体字段命名可在 implementation plan 中细化），统一负责：

```text
create-or-get JourneyRecord
ensure loading
ensure error
ensure planId / ownership
active Promise
retry
result/current record sync
resetSessionState cleanup
session protection
```

页面不得直接管理 JourneyRecord 创建 API。任务详情页在任务完成后改为调用该 Store 动作：任务本身一旦已成功完成，即使 ensure 失败也不能回滚任务；失败要有可见提示，例如“任务已完成，但成长记录同步失败，可稍后重试”。

### 5.2 去重、幂等与会话隔离

同一有效 `session + planId` 的 ensure 只允许一条活跃请求。刷新、重复点击、任务详情页的提前 ensure、Plan 完成后的再次 ensure 和失败后的 retry 都复用后端 create-or-get 幂等语义，不得产生第二条 JourneyRecord。

每个 ensure 操作都记录 request session。在 success、catch、finally 中再次检查 session：

- 旧 session 成功不得写入 `currentRecord`、ensure success 或 UI 状态。
- 旧 session 失败不得写入 ensure error。
- 旧 session finally 不得清除新 session 的 loading 或 active Promise。
- 登录退出后 `resetSessionState` 清理 ensure 状态、对应 Promise 引用与记录状态，且保留现有资源清理责任。

### 5.3 ensure 成功与 retry

ensure 成功后保存足以让任务列表判断“JourneyRecord 已存在”的当前记录状态；它不代表 finalized。成功界面的“查看成长记录”只导航，不重复创建记录：

```text
/pages/record-detail/index?planId=<planId>
```

ensure 的网络或普通业务失败必须可见、可重试。retry 只调用：

```text
ensureJourneyRecord(planId)
```

认证错误不作为普通 retry 呈现，而是走 `endUserSession()`。

## 6. 部分成功模型

下列结果是 FE-R2 的核心恢复情形：

```text
Plan complete success + JourneyRecord ensure failure = PARTIAL_SUCCESS
```

Plan 已完成是不可回滚的服务器事实。此时不得把 Plan 改回 `in-progress`，不得要求用户重新完成任务，也不得再次调用 complete Plan。任务列表必须明确表达：

```text
探索已经完成
成长记录暂时没有生成成功
[重新生成成长记录]
```

重试成功后切换到“探索完成 🎉”与“查看成长记录”。

## 7. 任务列表状态矩阵

| Plan / Record 状态 | 页面表现 | 可用操作 |
| --- | --- | --- |
| `ready` | 任务已经准备 | 开始探索 |
| `in-progress` + 未全部完成 | 正常任务进度 | 不显示完成探索按钮 |
| `in-progress` + 全部任务 completed | 全部观察任务完成 | 完成本次探索 |
| completing | 正在完成本次探索 | 主按钮 disabled |
| complete API failed | 完成探索失败提示 | 重新完成探索 |
| `PLAN_TASKS_INCOMPLETE` | 服务端仍认为任务未完成 | 刷新任务状态 |
| `completed` + ensuring record | 探索已完成，正在整理成长记录 | disabled |
| `completed` + record ensure failed | 探索已完成，但记录生成失败 | 重新生成成长记录 |
| `completed` + record ready | 探索完成 🎉；这次旅行已经整理成成长记录 | 查看成长记录 |

“完成探索卡”“探索完成卡”“错误恢复卡”均沿用 `docs/design-reference/04-task-list.png` 的米黄色纸张、深棕文字、橙色主强调、圆角手账卡片和绘本感；只增加状态内容，不整体 redesign，不引入科技蓝、企业后台、玻璃拟态或新导航。

## 8. 页面交互与文案

### 8.1 完成卡

- 前提：`in-progress` 且任务展示数据为全部完成。
- 主按钮：**完成本次探索**。
- 请求中：**正在完成…**，按钮 disabled。
- 失败：**完成探索失败**，提供重试；若为 `PLAN_TASKS_INCOMPLETE`，改为刷新任务状态。

### 8.2 成功卡

- 标题：**探索完成 🎉**。
- 说明：**这次旅行已经整理成成长记录**。
- 主按钮：**查看成长记录**。
- 点击后才进入 Record Detail；成功后不得自动跳转。

### 8.3 部分成功恢复卡

- 标题：**探索已经完成**。
- 说明：**成长记录暂时没有生成成功**。
- 主按钮：**重新生成成长记录**。
- 不显示再次完成探索的入口。

## 9. 非目标与保护规则

1. 不自动 finalize JourneyRecord；用户仍可在 Record Detail 编辑旅行标题、小结和封面，再自行“封存这份旅行记录”。
2. 不新建 Record Detail 页面；继续复用 `loadJourneyRecordDetail(planId)`。
3. 不将 completed Task 的图文编辑能力带入 FE-R2。
4. 不修改后端、数据库、迁移或新增 API。
5. 不修复历史 stale checker，除非其被证明为当前真实回归；FE-R2 只为当前 contract 新增有针对性的验证。

## 10. 实现阶段的 TDD 验证边界

实现阶段必须先写测试并观察真实 RED，再做最小实现、转为 GREEN，并执行全量回归。新增验证聚焦当前 FE-R2 contract：

### 10.1 Plan completion

```text
completePlan API path / method / auth
complete success updates Plan
failure does not locally complete Plan
PLAN_TASKS_INCOMPLETE recovery
repeated clicks deduplicated
stale session success ignored
stale session error / finally isolated
```

### 10.2 JourneyRecord ensure

```text
create-or-get success
existing record success
duplicate ensure deduplicated
network failure visible
retry success
session invalidation
auth error ends session
```

### 10.3 端到端前端闭环

```text
2/3：无完成 CTA
3/3：出现完成 CTA
complete success：再 ensure record
complete fail：不 ensure
complete success + ensure fail：部分成功 UI
retry record：成功 UI
success：查看成长记录
按钮路由使用 planId
无自动跳转
无自动 finalize
```

### 10.4 Task Detail 回归

```text
JourneyRecord ensure 失败时，任务完成仍成功
不再静默吞掉 JourneyRecord 创建错误
```

## 11. Acceptance Criteria

1. 任务未全部完成时不能完成 Plan。
2. 全部完成后任务列表出现显式完成入口。
3. Plan 只有在服务端成功响应后才变为 completed。
4. Plan complete 与 ensure Record 均防止重复请求。
5. 旧 session 结果不能污染新 session。
6. Plan 完成后确保 JourneyRecord 存在。
7. JourneyRecord ensure 失败必须可见且可重试。
8. Record failure 不回滚已完成的 Plan。
9. 成功后不自动跳页。
10. 只有点击“查看成长记录”才进入 Record Detail。
11. FE-R2 不自动 finalize。
12. Task Detail 不再静默吞掉 JourneyRecord 创建错误。
13. 不修改 backend、DB 或 migration。
14. 不进入 FE-R3 或后续阶段。

## 12. 实施前后的门禁

开始 implementation 前，先基于本设计创建独立 implementation plan，并保持历史 checker 与当前 contract 的边界清晰。每次验证应在正确工作区与会话下运行；任何首次新失败先停止并报告，不顺带修复范围外问题。

本设计文档提交审核前不进行 Git 写入。用户审核后，才可明确授权进入 implementation plan；本文件本身不授权功能实现。
