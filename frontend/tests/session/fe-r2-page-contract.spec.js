import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const taskDetailSource = readFileSync(
  resolve(root, 'frontend/src/pages/task-detail/index.vue'),
  'utf8',
)
const tasksPageSource = readFileSync(
  resolve(root, 'frontend/src/pages/tasks/index.vue'),
  'utf8',
)

function methodSource(name, nextMethodName) {
  const start = taskDetailSource.indexOf(`async ${name}(`)
  const end = taskDetailSource.indexOf(`\n    },\n    ${nextMethodName}(`, start)

  expect(start).toBeGreaterThanOrEqual(0)
  expect(end).toBeGreaterThan(start)
  return taskDetailSource.slice(start, end)
}

function tasksMethodSource(name) {
  const asyncStart = tasksPageSource.indexOf(`async ${name}(`)
  const start = asyncStart >= 0 ? asyncStart : tasksPageSource.indexOf(`\n    ${name}(`)
  const end = tasksPageSource.indexOf('\n    },', start)

  expect(start).toBeGreaterThanOrEqual(0)
  expect(end).toBeGreaterThan(start)
  return tasksPageSource.slice(start, end)
}

describe('FE-R2.3 Task Detail JourneyRecord contract', () => {
  test('does not own the JourneyRecord API boundary directly', () => {
    expect(taskDetailSource).not.toMatch(
      /import\s*\{\s*createJourneyRecord\s*\}\s*from\s*['"]\.\.\/\.\.\/api\/journeyRecords\.js['"]/,
    )
    expect(taskDetailSource).not.toContain('createJourneyRecord(')
    expect(taskDetailSource).not.toContain('syncJourneyRecordAfterCompletion')
  })

  test('delegates JourneyRecord ensure to the Record Store', () => {
    expect(taskDetailSource).toMatch(
      /import\s*\{\s*useRecordStore\s*\}\s*from\s*['"]\.\.\/\.\.\/stores\/record['"]/,
    )
    expect(taskDetailSource).toMatch(
      /recordStore\(\)\s*\{\s*return useRecordStore\(\)\s*\}/,
    )
    expect(taskDetailSource).toContain('this.recordStore.ensureJourneyRecord(validPlanId)')
  })

  test('keeps normal ensure failures visible, non-blocking, and session-safe', () => {
    const ensureSource = methodSource('ensureJourneyRecordAfterTaskCompletion', 'async completeTask')
    const authenticationIndex = ensureSource.indexOf('if (isAuthenticationError(error))')
    const toastIndex = ensureSource.indexOf('任务已完成，但成长记录同步失败，可稍后重试。')

    expect(ensureSource).toContain('return await this.recordStore.ensureJourneyRecord(validPlanId)')
    expect(authenticationIndex).toBeGreaterThanOrEqual(0)
    expect(ensureSource).toContain('await endUserSession()')
    expect(toastIndex).toBeGreaterThan(authenticationIndex)
    expect(ensureSource).toContain("this.showToast('任务已完成，但成长记录同步失败，可稍后重试。')")
    expect(ensureSource).not.toMatch(/catch\s*\([^)]*\)\s*\{\s*return null\s*\}/)
    expect(ensureSource).not.toContain('completeTaskSubmission(')
    expect(ensureSource).not.toMatch(/status\s*=\s*['"]in-progress['"]|delete/i)
    expect(ensureSource).not.toMatch(/uni\.(navigateTo|redirectTo|reLaunch|navigateBack)/)
  })

  test('completes the Task first without adding Plan completion, retry UI, navigation, or finalization', () => {
    const completeSource = methodSource('completeTask', 'goBack')
    const completeTaskIndex = completeSource.indexOf('await this.task.completeTaskSubmission')
    const ensureIndex = completeSource.indexOf('void this.ensureJourneyRecordAfterTaskCompletion(task.planId)')

    expect(completeTaskIndex).toBeGreaterThanOrEqual(0)
    expect(ensureIndex).toBeGreaterThan(completeTaskIndex)
    expect(completeSource).not.toContain('await this.ensureJourneyRecordAfterTaskCompletion')
    expect(completeSource).not.toMatch(/uni\.(navigateTo|redirectTo|reLaunch|navigateBack)/)
    expect(taskDetailSource).not.toContain('completePlan')
    expect(taskDetailSource).not.toContain('completeExploration')
    expect(taskDetailSource).not.toContain('/plans/')
    expect(taskDetailSource).not.toContain('完成本次探索')
    expect(taskDetailSource).not.toContain('重新生成成长记录')
    expect(taskDetailSource).not.toContain('finalizeJourneyRecord')
    expect(taskDetailSource).not.toContain('finalizeJourneyRecordDraft')
  })
})

describe('FE-R2.4 Tasks Page completion and recovery contract', () => {
  test('shows the completion CTA only for an in-progress Plan with every Task completed', () => {
    expect(tasksPageSource).toMatch(
      /import\s*\{\s*useRecordStore\s*\}\s*from\s*['"]\.\.\/\.\.\/stores\/record['"]/,
    )
    expect(tasksPageSource).toMatch(
      /recordStore\(\)\s*\{\s*return useRecordStore\(\)\s*\}/,
    )
    expect(tasksPageSource).toMatch(
      /allTasksCompleted\(\)[\s\S]*?this\.displayPlan\.status\s*===\s*['"]in-progress['"][\s\S]*?this\.totalTasks\s*>\s*0[\s\S]*?this\.task\.completedCount\s*===\s*this\.totalTasks/,
    )
    expect(tasksPageSource).toContain('v-if="isPlanReady && task.currentPlanTasks.length"')
    expect(tasksPageSource).toContain('开始探索')
    expect(tasksPageSource).toContain('v-if="allTasksCompleted"')
    expect(tasksPageSource).toContain('完成本次探索')
    expect(tasksPageSource).toContain(':disabled="planStore.isCompleting"')
    expect(tasksPageSource).toContain('正在完成…')
  })

  test('completes the server Plan before ensuring its JourneyRecord', () => {
    const completionSource = tasksMethodSource('completeExploration')
    const completePlanIndex = completionSource.indexOf('await this.planStore.completeExploration')
    const ensureRecordIndex = completionSource.indexOf('await this.ensureJourneyRecordForCompletedPlan(planId)')

    expect(completePlanIndex).toBeGreaterThanOrEqual(0)
    expect(ensureRecordIndex).toBeGreaterThan(completePlanIndex)
    expect(completionSource).toContain('isAuthenticationError(error)')
    expect(completionSource).toContain('await endUserSession()')
    expect(completionSource).toContain("error?.code === 'PLAN_TASKS_INCOMPLETE'")
    expect(completionSource).toContain('还有任务未完成，请刷新后检查')
    expect(completionSource).toContain('await this.restorePlanAndTasks(true)')
    expect(completionSource).not.toMatch(/currentPlan\.status\s*=|displayPlan\.status\s*=/)
    expect(completionSource).not.toMatch(/uni\.(navigateTo|redirectTo|reLaunch|navigateBack)/)
  })

  test('keeps completed Plan recovery separate from completion and finalization', () => {
    const ensureSource = tasksMethodSource('ensureJourneyRecordForCompletedPlan')
    const retrySource = tasksMethodSource('retryJourneyRecord')

    expect(tasksPageSource).toMatch(
      /isCompletedPlan\(\)[\s\S]*?displayPlan\.status\s*===\s*['"]completed['"]/,
    )
    expect(tasksPageSource).toContain('正在整理成长记录…')
    expect(tasksPageSource).toContain('探索已经完成')
    expect(tasksPageSource).toContain('成长记录暂时没有生成成功')
    expect(tasksPageSource).toContain('重新生成成长记录')
    expect(ensureSource).toContain('await this.recordStore.ensureJourneyRecord(planId)')
    expect(ensureSource).toContain('await endUserSession()')
    expect(retrySource).toMatch(/recordStore\.(retryJourneyRecordEnsure|ensureJourneyRecord)\(/)
    expect(retrySource).not.toContain('completeExploration(')
    expect(tasksPageSource).not.toContain('finalizeJourneyRecord')
    expect(tasksPageSource).not.toContain('finalizeJourneyRecordDraft')
    expect(tasksPageSource).not.toMatch(/修改已完成任务|重新编辑|更换已完成.*图片/)
  })

  test('recovers completed Plans without recompleting and only navigates from the record CTA', () => {
    const restoreSource = tasksMethodSource('restorePlanAndTasks')
    const completionSource = tasksMethodSource('completeExploration')
    const ensureSource = tasksMethodSource('ensureJourneyRecordForCompletedPlan')
    const recordNavigationSource = tasksMethodSource('openJourneyRecord')

    expect(restoreSource).toContain('this.isCompletedPlan')
    expect(restoreSource).toContain('this.ensureJourneyRecordForCompletedPlan(planId)')
    expect(restoreSource).not.toContain('completeExploration(')
    expect(tasksPageSource).toContain('探索完成 🎉')
    expect(tasksPageSource).toContain('这次旅行已经整理成成长记录')
    expect(tasksPageSource).toContain('查看成长记录')
    expect(recordNavigationSource).toContain('/pages/record-detail/index?planId=')
    expect(recordNavigationSource).toContain('uni.navigateTo')
    expect(completionSource).not.toMatch(/uni\.(navigateTo|redirectTo|reLaunch|navigateBack)/)
    expect(ensureSource).not.toMatch(/uni\.(navigateTo|redirectTo|reLaunch|navigateBack)/)
  })
})
