# 童旅记 FE-R2 Plan Completion + JourneyRecord Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐“全部观察任务完成 → 用户显式完成探索 → 确保 JourneyRecord → 查看成长记录”的真实前端闭环，并使 JourneyRecord 创建失败可见、可恢复、可重试。

**Architecture:** Plan completion 由 `planStore` 管理，且只有服务器返回的 Plan 才能把本地状态更新为 `completed`；JourneyRecord create-or-get 由 `recordStore.ensureJourneyRecord(planId)` 统一管理。任务列表承担 completion/recovery UI，Task Detail 只在单个任务完成后进行非阻塞 ensure。

**Tech Stack:** 经典 uni-app、Vue 3、JavaScript、Pinia、Vite、Vitest、既有 request 层和 session boundary。

---

## 0. 前提、边界与基线

- 正式名称：童旅记。
- 基线：`main`、`a984a70b927f351070e974c4b5cb6130a93b9347`。
- 不修改 `backend/*`、数据库、migration、FE-R3、Notification、Guide audio 或 FE-R5 视觉重构。
- 不自动 finalize JourneyRecord；不自动导航到 Record Detail。
- 服务器状态是业务事实；前端任务计数只控制完成 CTA 的可见性。
- 旧 session 的 success/error/finally 不得写入新 session；活跃 Promise 不跨 session 复用；logout 后迟到响应不能复活 Store。
- 不把历史 checker debt 升级为 acceptance gate。
- 全部实施结束前不得 `git add`、`git commit` 或 `git push`。

- [ ] 在根目录执行：

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
git diff --check
```

预期：

```text
main
a984a70b927f351070e974c4b5cb6130a93b9347
<status 与 diff check 均无输出>
```

失败时立即停止并报告：

```text
FAILED_PHASE=FE-R2 baseline
FAILED_COMMAND=<actual command>
EXIT_CODE=<actual exit code>
ERROR_SUMMARY=<actual mismatch>
CURRENT_REAL_REGRESSION=unknown
FILES_MODIFIED_SO_FAR=<git status --short>
```

## 1. 文件责任图

| 文件 | FE-R2 责任 |
| --- | --- |
| `frontend/src/api/plans.js` | 新增 `completePlan(id)` 的唯一 REST 调用 |
| `frontend/src/stores/plan.js` | completion loading/error、session+plan 去重、服务器 Plan upsert、reset 清理 |
| `frontend/src/stores/record.js` | create-or-get ensure、retry、session protection、ensure state；保留 list/detail/save/finalize |
| `frontend/src/pages/task-detail/index.vue` | 任务完成后通过 Record Store 非阻塞 ensure |
| `frontend/src/pages/tasks/index.vue` | 唯一 completion CTA、部分成功恢复、手动详情导航 |
| `frontend/tests/session/fe-r2-plan-completion.spec.js` | Plan API/Store contract |
| `frontend/tests/session/fe-r2-record-ensure.spec.js` | Record ensure/retry/session contract |
| `frontend/tests/session/fe-r2-page-contract.spec.js` | 两个页面的静态契约 |

复用 `frontend/tests/session/setup/uniRuntime.js` 的 `setRequestHandler`、`createDeferred`、`getRequestCalls`、`flushRuntimePromises`，并复跑 `frontend/tests/session/stale-response.spec.js`。不新建并行 Store、重复 API 函数或第二套 Record Detail 页面。

## 2. FE-R2.1 — Plan Completion RED

**Files:**

- Create: `frontend/tests/session/fe-r2-plan-completion.spec.js`
- Read: `frontend/src/api/plans.js`, `frontend/src/stores/plan.js`

- [ ] 使用现有 session suite 夹具建立测试：

```javascript
import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  createDeferred, flushRuntimePromises, getRequestCalls,
  resetUniRuntime, setRequestHandler,
} from './setup/uniRuntime.js'
import { usePlanStore } from '../../src/stores/plan.js'
import { useUserStore } from '../../src/stores/user.js'
import { endUserSession } from '../../src/utils/sessionBoundary.js'

const userA = { id: 101, nickname: 'User A' }
const userB = { id: 202, nickname: 'User B' }
function login(user) { useUserStore().loginSuccess('token-' + user.id, user) }
function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}
function seed(plan, user = userA) {
  plan.applyPlanList([{ id: 119, title: '故宫探索', status: 'in-progress', taskCount: 3 }], user.id)
}
beforeEach(() => { resetUniRuntime(); setActivePinia(createPinia()) })
```

- [ ] 先写 API contract，RED 必须是缺少 `completePlan` 导出或行为：

```javascript
test('sends authenticated POST to the Plan completion endpoint', async () => {
  login(userA)
  setRequestHandler((options) => {
    respond(options, { plan: { id: 119, title: '故宫探索', status: 'completed', taskCount: 3 } })
  })
  const api = await import('../../src/api/plans.js')
  await api.completePlan(119)
  const [request] = getRequestCalls()
  expect(request.method).toBe('POST')
  expect(request.url).toContain('/plans/119/complete')
  expect(request.header.Authorization).toBe('Bearer token-101')
})
```

- [ ] 写 success/failure/服务端拒绝 RED：

```javascript
test('updates plans, currentPlan and status only from the completed server Plan', async () => {
  const plan = usePlanStore()
  login(userA); seed(plan)
  setRequestHandler((options) => respond(options, {
    plan: { id: 119, title: '故宫探索', status: 'completed', taskCount: 3 },
  }))
  await plan.completeExploration(119, userA.id)
  expect(plan.currentPlan.status).toBe('completed')
  expect(plan.plans.find((item) => item.id === 119).status).toBe('completed')
  expect(plan.status).toBe('completed')
})

test('keeps Plan in progress after network failure', async () => {
  const plan = usePlanStore()
  login(userA); seed(plan)
  setRequestHandler((options) => options.fail({ errMsg: 'offline' }))
  await expect(plan.completeExploration(119, userA.id)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
  expect(plan.currentPlan.status).toBe('in-progress')
  expect(plan.completionError.code).toBe('NETWORK_ERROR')
})

test('exposes PLAN_TASKS_INCOMPLETE without locally completing the Plan', async () => {
  const plan = usePlanStore()
  login(userA); seed(plan)
  setRequestHandler((options) => options.success({
    statusCode: 409,
    data: { success: false, error: { code: 'PLAN_TASKS_INCOMPLETE', message: 'incomplete' } },
  }))
  await expect(plan.completeExploration(119, userA.id)).rejects.toMatchObject({ code: 'PLAN_TASKS_INCOMPLETE' })
  expect(plan.currentPlan.status).toBe('in-progress')
  expect(plan.completionError.code).toBe('PLAN_TASKS_INCOMPLETE')
})
```

- [ ] 写同 session 去重 RED：

```javascript
test('dedupes concurrent completion for one active session and Plan', async () => {
  const plan = usePlanStore()
  const deferred = createDeferred()
  login(userA); seed(plan)
  setRequestHandler((options) => deferred.promise.then((data) => respond(options, data)))
  const first = plan.completeExploration(119, userA.id)
  const second = plan.completeExploration(119, userA.id)
  await flushRuntimePromises()
  expect(getRequestCalls().filter((call) => call.url.endsWith('/plans/119/complete'))).toHaveLength(1)
  deferred.resolve({ plan: { id: 119, title: '故宫探索', status: 'completed', taskCount: 3 } })
  await Promise.all([first, second])
})
```

- [ ] 写 A complete → logout → B login/Plan 220 的 stale success、error、finally 和 logout-only delayed-response RED。分别断言 B 的 `currentPlan.id === 220`、`completionError === null`、A finally 不会把 B pending completion 的 `isCompleting` 清为 false；logout-only 后断言 Plan Store 已 reset。

- [ ] 运行 RED：

```powershell
Set-Location frontend
npm run test:session -- tests/session/fe-r2-plan-completion.spec.js
```

预期：FAIL，且失败来自缺失的 FE-R2 API/Store 行为。

## 3. FE-R2.1 — Plan Completion GREEN

**Files:**

- Modify: `frontend/src/api/plans.js`
- Modify: `frontend/src/stores/plan.js`
- Test: `frontend/tests/session/fe-r2-plan-completion.spec.js`

- [ ] 在 API 新增：

```javascript
export function completePlan(id) {
  return request({
    path: '/plans/' + id + '/complete',
    method: 'POST',
    auth: true,
  })
}
```

- [ ] 在 Plan Store 模块作用域增加：

```javascript
let completionPromise = null
let completionPlanId = null
let completionUserId = null
let completionEpoch = null
```

- [ ] 在 Store state 增加独立 completion 状态，不得使用列表 `isLoading` 或 `error`：

```javascript
isCompleting: false,
completionError: null,
```

- [ ] 在 `resetSessionState()` 清除上述 state 和所有 completion metadata。

- [ ] 在 `startExploration` 后实现：

```javascript
async completeExploration(id = this.currentPlan?.id, userId = this.loadedForUserId) {
  if (!id) throw { code: 'PLAN_REQUIRED', message: '请先创建探索计划' }
  const requestSession = getCurrentSession()
  if (!requestSession.isLoggedIn || String(requestSession.userId) !== String(userId)) return null

  const sameRequest = completionPromise
    && completionPlanId === id
    && String(completionUserId) === String(requestSession.userId)
    && completionEpoch === requestSession.epoch
  if (sameRequest) return completionPromise

  this.isCompleting = true
  this.completionError = null
  completionPlanId = id
  completionUserId = requestSession.userId
  completionEpoch = requestSession.epoch

  const promise = plansApi.completePlan(id)
    .then((data) => {
      if (!data?.plan || typeof data.plan !== 'object') {
        throw { code: 'INVALID_RESPONSE', message: '探索完成结果异常' }
      }
      if (!isCurrentSession(requestSession)) return data.plan
      const plan = this.selectPlan(data.plan, userId)
      this.completionError = null
      return plan
    })
    .catch((error) => {
      if (isCurrentSession(requestSession)) this.completionError = error
      throw error
    })
    .finally(() => {
      if (isCurrentSession(requestSession) && completionPromise === promise) {
        this.isCompleting = false
        completionPromise = null
        completionPlanId = null
        completionUserId = null
        completionEpoch = null
      }
    })

  completionPromise = promise
  return promise
}
```

`selectPlan` 负责 upsert、`syncStatus` 和 selection 保留；禁止直接赋值 `currentPlan.status = 'completed'`。

- [ ] 运行 GREEN 和 FE-R1 regression：

```powershell
npm run test:session -- tests/session/fe-r2-plan-completion.spec.js
npm run test:session -- tests/session/stale-response.spec.js
```

两个命令均预期 PASS。

## 4. FE-R2.2 — JourneyRecord Ensure RED

**Files:**

- Create: `frontend/tests/session/fe-r2-record-ensure.spec.js`
- Read: `frontend/src/api/journeyRecords.js`, `frontend/src/stores/record.js`

- [ ] 使用与 Plan tests 相同的 Pinia/uni 夹具，并导入 `useRecordStore`、`useUserStore`、`endUserSession`。

- [ ] 写 create-or-get 与 existing record success RED：

```javascript
test('stores the create-or-get JourneyRecord for the ensured Plan', async () => {
  const record = useRecordStore()
  login(userA)
  setRequestHandler((options) => respond(options, {
    journeyRecord: { id: 501, planId: 119, status: 'draft', entries: [] },
  }))
  const result = await record.ensureJourneyRecord(119)
  expect(result).toMatchObject({ id: 501, planId: 119, status: 'draft' })
  expect(record.ensurePlanId).toBe(119)
  expect(record.ensureError).toBeNull()
  expect(record.ensuredRecord).toMatchObject({ id: 501, planId: 119 })
})
```

- [ ] 写 deferred duplicate ensure，断言 `POST /plans/119/journey-record` 仅一次。

- [ ] 写 network failure 和 retry：

```javascript
await expect(record.ensureJourneyRecord(119)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
expect(record.ensureError.code).toBe('NETWORK_ERROR')
expect(record.ensureLoading).toBe(false)
const recovered = await record.retryJourneyRecordEnsure()
expect(recovered.planId).toBe(119)
expect(record.ensureError).toBeNull()
```

- [ ] 写 invalid response：缺少 `journeyRecord` 或返回 record 的 `planId !== 119` 时 reject `INVALID_RESPONSE` 且不覆盖 `ensuredRecord`。

- [ ] 写 stale success/error/finally：A ensure 119 后 logout，B ensure 220；A late result 不能覆盖 B 的 `ensurePlanId`、`ensuredRecord`、`ensureError` 或 loading。另写 logout 后无新登录时 Store 保持 reset。

- [ ] 写 auth boundary：Store 仍 reject；页面在 `UNAUTHORIZED`、`INVALID_TOKEN`、`TOKEN_EXPIRED` 或 401 时调用 `endUserSession()`。

- [ ] 运行 RED：

```powershell
npm run test:session -- tests/session/fe-r2-record-ensure.spec.js
```

预期：FAIL，原因是 ensure/retry/state 尚未实现。

## 5. FE-R2.2 — Record Store GREEN

**Files:**

- Modify: `frontend/src/stores/record.js`
- Test: `frontend/tests/session/fe-r2-record-ensure.spec.js`

- [ ] 扩展既有 API import，加入 `createJourneyRecord`；加入：

```javascript
import { getCurrentSession, isCurrentSession } from '../utils/sessionBoundary.js'
```

- [ ] 模块作用域增加 `activeEnsurePromise`、`activeEnsurePlanId`、`activeEnsureUserId`、`activeEnsureEpoch`；state 增加：

```javascript
ensureLoading: false,
ensureError: null,
ensurePlanId: null,
ensuredRecord: null,
```

- [ ] 在 `loadJourneyRecordDetail` 前新增 `ensureJourneyRecord(planId)`。有效 planId、登录 session 和同 session+planId 去重检查必须为：

```javascript
const validPlanId = normalizePlanId(planId)
if (!validPlanId) return Promise.resolve(null)
const requestSession = getCurrentSession()
if (!requestSession.isLoggedIn || !requestSession.userId) return Promise.resolve(null)

const sameRequest = activeEnsurePromise
  && activeEnsurePlanId === validPlanId
  && String(activeEnsureUserId) === String(requestSession.userId)
  && activeEnsureEpoch === requestSession.epoch
if (sameRequest) return activeEnsurePromise
```

- [ ] 设置 `ensureLoading=true`、清空 error、记录 planId/metadata，调用既有 `createJourneyRecord(validPlanId)`。成功路径验证：

```javascript
if (!data?.journeyRecord || typeof data.journeyRecord !== 'object'
  || normalizePlanId(data.journeyRecord.planId) !== validPlanId) {
  throw { code: 'INVALID_RESPONSE', message: '成长记录生成结果异常' }
}
if (isCurrentSession(requestSession)) {
  this.ensuredRecord = mapJourneyRecord(data.journeyRecord, this.coverResources)
  this.ensureError = null
}
```

如果 list 已有该 planId，复用 `syncJourneyRecordListItem`；不得重写 list/detail/image/save/finalize。

- [ ] catch 仅在 active session 写 `ensureError` 后 rethrow。finally 仅在 active session 且同 Promise 时关闭 loading 并清 metadata。

- [ ] 增加：

```javascript
retryJourneyRecordEnsure() {
  const validPlanId = normalizePlanId(this.ensurePlanId)
  return validPlanId ? this.ensureJourneyRecord(validPlanId) : Promise.resolve(null)
}
```

- [ ] 在 `resetRecordState()` 清空 ensure state、metadata 和 active Promise，再执行原有 detail/resource/save/finalize 清理。

- [ ] 运行 GREEN 与全 maintained suite：

```powershell
npm run test:session -- tests/session/fe-r2-record-ensure.spec.js
npm run test:session
```

预期：均 PASS。

## 6. FE-R2.3 — Task Detail 非阻塞 ensure RED→GREEN

**Files:**

- Create: `frontend/tests/session/fe-r2-page-contract.spec.js`
- Modify: `frontend/src/pages/task-detail/index.vue`

- [ ] 用 Node 读取源文件的静态 RED contract：

```javascript
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const taskDetailSource = readFileSync(resolve(root, 'frontend/src/pages/task-detail/index.vue'), 'utf8')

test('Task Detail delegates Record ensure to Record Store', () => {
  expect(taskDetailSource).not.toContain("createJourneyRecord } from '../../api/journeyRecords.js'")
  expect(taskDetailSource).toContain("import { useRecordStore } from '../../stores/record'")
  expect(taskDetailSource).toContain('recordStore.ensureJourneyRecord')
})

test('Record ensure failure does not turn a completed Task into failure', () => {
  expect(taskDetailSource).toContain('任务已完成，但成长记录同步失败，可稍后重试')
  expect(taskDetailSource).toContain('void this.ensureJourneyRecordAfterTaskCompletion(task.planId)')
})
```

- [ ] 运行 RED：

```powershell
npm run test:session -- tests/session/fe-r2-page-contract.spec.js
```

- [ ] 删除直接 `createJourneyRecord` import；增加 `useRecordStore` 和 computed `recordStore() { return useRecordStore() }`。用下列 helper 替代旧静默 `syncJourneyRecordAfterCompletion`：

```javascript
async ensureJourneyRecordAfterTaskCompletion(planId) {
  try {
    await this.recordStore.ensureJourneyRecord(planId)
  } catch (error) {
    if (isAuthenticationError(error)) {
      await endUserSession()
      return
    }
    this.showToast('任务已完成，但成长记录同步失败，可稍后重试')
  }
}
```

- [ ] 保持主链先完成 Task 后 fire-and-forget ensure：

```javascript
const task = await this.task.completeTaskSubmission(this.currentTask.id, this.noteDraft)
if (task) {
  this.noteDraft = task.record?.note || ''
  this.noteHasLocalEdits = false
  void this.ensureJourneyRecordAfterTaskCompletion(task.planId)
}
```

不得从 helper throw 回 `completeTask`，不得 rollback Task，且不得增加 Plan completion。

- [ ] 运行 page contract GREEN。

## 7. FE-R2.4 — Tasks Page completion/recovery RED→GREEN

**Files:**

- Modify: `frontend/tests/session/fe-r2-page-contract.spec.js`
- Modify: `frontend/src/pages/tasks/index.vue`

- [ ] 先加 RED contract，锁定页面必须包含 in-progress、totalTasks、completedCount 门槛，和如下文案：`完成本次探索`、`正在完成…`、`探索已经完成`、`成长记录暂时没有生成成功`、`重新生成成长记录`、`探索完成 🎉`、`查看成长记录`。断言 Tasks Page 不引用 `finalizeJourneyRecord` 或 `finalizeJourneyRecordDraft`。

- [ ] 在 source contract 中截取 `async completeExploration()` 到 `async retryJourneyRecord()`，断言 `await this.planStore.completeExploration` 出现在 `await this.ensureJourneyRecordForCompletedPlan` 之前。该测试锁定 complete failure 不触发 ensure。

- [ ] 运行 RED：

```powershell
npm run test:session -- tests/session/fe-r2-page-contract.spec.js
```

- [ ] 在 Tasks Page 引入 `useRecordStore` 和 `recordStore()`。新增 computed：

```javascript
allTasksCompleted() {
  return this.displayPlan.status === 'in-progress'
    && this.totalTasks > 0
    && this.task.completedCount === this.totalTasks
},
isCompletedPlan() { return this.displayPlan.status === 'completed' },
isEnsuringJourneyRecord() {
  return this.isCompletedPlan && this.recordStore.ensureLoading
},
hasJourneyRecordEnsureError() {
  return this.isCompletedPlan && Boolean(this.recordStore.ensureError)
},
hasEnsuredJourneyRecord() {
  return this.isCompletedPlan && this.recordStore.ensuredRecord?.planId === this.displayPlan.id
},
```

- [ ] 在任务列表与奖励卡之间加入互斥卡片：allTasksCompleted 显示“全部观察任务完成”和“完成本次探索”；completion loading 显示“正在完成…”且 disabled；completed+ensure loading 显示“探索已完成 / 正在整理成长记录…”；completed+ensure error 显示恢复卡；completed+record ready 显示成功卡和“查看成长记录”。只增加 `.tasks-completion`、`.tasks-completion--success`、`.tasks-completion--error` scoped SCSS，沿用 `#f8efd9`、`#4a2f1b`、现有橙色按钮、圆角手账风，不遮挡 AiPet、AppTabbar 或 task list。

- [ ] 新增 methods：

```javascript
async completeExploration() {
  if (this.planStore.isCompleting || !this.allTasksCompleted) return
  const planId = Number(this.displayPlan?.id)
  if (!Number.isInteger(planId) || planId <= 0) return
  try {
    await this.planStore.completeExploration(planId, this.userStore.userInfo?.id)
    await this.ensureJourneyRecordForCompletedPlan(planId)
  } catch (error) {
    if (isAuthenticationError(error)) return endUserSession()
    if (error?.code === 'PLAN_TASKS_INCOMPLETE') {
      this.showToast('还有任务未完成，请刷新后检查')
      return this.restorePlanAndTasks(true)
    }
    this.showToast(this.taskErrorText(error, '完成探索失败，请稍后重试'))
  }
},

async ensureJourneyRecordForCompletedPlan(planId) {
  try {
    await this.recordStore.ensureJourneyRecord(planId)
  } catch (error) {
    if (isAuthenticationError(error)) await endUserSession()
  }
},

async retryJourneyRecord() {
  try {
    await this.recordStore.retryJourneyRecordEnsure()
  } catch (error) {
    if (isAuthenticationError(error)) await endUserSession()
  }
},

openJourneyRecord() {
  const planId = Number(this.displayPlan?.id)
  if (!Number.isInteger(planId) || planId <= 0) return
  uni.navigateTo({ url: '/pages/record-detail/index?planId=' + planId })
},
```

- [ ] 在 `restorePlanAndTasks` 完成真实 Plan 恢复后，若 Plan 已 completed 且当前 Store 没有该 plan 的 ensuredRecord 或同 plan active ensure，调用 `recordStore.ensureJourneyRecord(planId)`。普通失败保留 recovery card；认证失败结束 session。不得为 completed Plan 生成 Tasks，不得再次 complete Plan。

- [ ] 运行 page contract GREEN。

## 8. FE-R2.5 — focused/session regression

- [ ] 依次运行：

```powershell
npm run test:session -- tests/session/fe-r2-plan-completion.spec.js
npm run test:session -- tests/session/fe-r2-record-ensure.spec.js
npm run test:session -- tests/session/fe-r2-page-contract.spec.js
npm run test:session
```

- [ ] 验证：2/3 无 CTA；3/3+in-progress 有 CTA；complete 成功后才 ensure；complete 失败不 ensure；`PLAN_TASKS_INCOMPLETE` 刷新真实状态；部分成功不回滚 Plan；retry 仅 ensure；route 携带 planId；无自动导航；无自动 finalize；completed Plan re-entry 只恢复 ensure；Task Detail ensure 失败不回滚 Task。

- [ ] 仅运行与修改文件直接相关且项目仍维护的 checker；不批量执行所有 `frontend/scripts/*.mjs`，不运行 6A migration verifier、破坏性数据库验收或 SQL backup。

## 9. FE-R2.6 — H5、范围与交接

- [ ] 在 `frontend` 运行：

```powershell
npm run build:h5
```

预期：退出码 0 且输出含 `DONE Build complete.`；Sass legacy API 提示不单独判为 build failure。

- [ ] 确认 `PARTIAL_SUCCESS`：Plan complete success + ensure failure 时 `Plan.status === 'completed'`，UI 仅提供“重新生成成长记录”，不会再次调用 complete。

- [ ] 在根目录运行：

```powershell
git status --short
git diff --name-status
git diff --check
```

允许的生产路径：`frontend/src/api/plans.js`、`frontend/src/stores/plan.js`、`frontend/src/stores/record.js`、`frontend/src/pages/task-detail/index.vue`、`frontend/src/pages/tasks/index.vue`。允许的新 tests 只有本计划文件责任图列出的三项。任何 backend、database、migration、FE-R3 或视觉资产重构差异都为范围失败；不要自动清理或 Git 集成。

## 10. 实施失败规则与自审

任一首次 blocking failure 立即停止：

```text
FAILED_PHASE=<FE-R2.1 至 FE-R2.6>
FAILED_COMMAND=<actual command>
EXIT_CODE=<actual exit code>
ERROR_SUMMARY=<first new failure>
CURRENT_REAL_REGRESSION=true / false / unknown
FILES_MODIFIED_SO_FAR=<git status --short>
```

- [ ] 检查每个独立行为都有先 FAIL、后最小实现、后 PASS 的记录。
- [ ] 检查 `completePlan`、`completeExploration`、`ensureJourneyRecord`、`retryJourneyRecordEnsure` 在所有任务中命名一致。
- [ ] 检查 server-authoritative Plan、Record ensure、partial success、record retry、Task Detail 非阻塞 ensure、去重、session isolation、completed Plan recovery、`PLAN_TASKS_INCOMPLETE`、无自动导航/封存均有对应测试。
- [ ] 运行禁止占位语扫描，确认没有未填充步骤、模糊异常处理或只引用前文的步骤。
- [ ] 检查历史 checker debt 没有成为 acceptance gate。
- [ ] 完成后先执行 FE-R2 Git Pre-Commit Audit，等待用户明确授权后再进行 Git 操作。
# 2026-08-11 FE-R4A supersession:

本文中的 AiPet / 小旅 / usePetStore 相关要求仅记录当时实现，不再属于当前首版要求，不得在后续实现中恢复。
