import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { getRequestCalls, resetUniRuntime, setFetchHandler, setRequestHandler, setUploadHandler } from './setup/uniRuntime.js'
import { usePlanStore } from '../../src/stores/plan.js'
import { useTaskStore } from '../../src/stores/task.js'
import { useUserStore } from '../../src/stores/user.js'
import { ensureCurrentPlanReady } from '../../src/utils/planRecovery.js'

const user = { id: 7, nickname: 'Compatibility User' }

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function taskFor(planId, id = 67, patch = {}) {
  return {
    id,
    planId,
    order: 1,
    title: `Task ${planId}`,
    status: 'not-started',
    record: { imageUrl: null, note: '' },
    ...patch,
  }
}

function login() {
  useUserStore().loginSuccess('task-compatibility-token', user)
}

describe('Task Store runtime compatibility', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('keeps remote Task state isolated by plan and clears it at session reset', () => {
    const plans = usePlanStore()
    const tasks = useTaskStore()
    const taskA = taskFor(101, 35)
    const taskB = taskFor(202, 35, { status: 'completed', record: { imageUrl: '/api/v1/plans/202/tasks/35/submission/image', note: 'server note' } })

    plans.applyPlanList([{ id: 101, title: 'Plan A' }, { id: 202, title: 'Plan B' }], user.id)
    tasks.setTasksForPlan(101, [taskA], 1)
    tasks.setTasksForPlan(202, [taskB], 1)

    plans.selectPlanById(101, user.id)
    tasks.setCurrentTask('35')
    plans.selectPlanById(202, user.id)

    expect(tasks.currentPlanTasks).toEqual([expect.objectContaining({ planId: 202, status: 'completed', record: expect.objectContaining({ note: 'server note', displayImagePath: '' }) })])
    expect(tasks.tasksByPlanId['101'][0].record.displayImagePath).toBeUndefined()

    tasks.resetSessionState()
    expect(tasks.tasksByPlanId).toEqual({})
    expect(tasks.taskImageCache).toEqual({})
    expect(tasks.currentTask).toBeNull()
  })

  test('serializes remote submission results and preserves the latest completion state', async () => {
    let serverTask = taskFor(100)
    setRequestHandler((options) => {
      if (options.url.endsWith('/submission/start')) {
        serverTask = { ...serverTask, status: 'in-progress' }
        respond(options, { task: serverTask })
        return
      }
      if (options.url.endsWith('/submission')) {
        serverTask = { ...serverTask, record: { ...serverTask.record, note: options.data.note } }
        respond(options, { task: serverTask })
        return
      }
      if (options.url.endsWith('/submission/complete')) {
        serverTask = { ...serverTask, status: 'completed', completedAt: '2026-07-14T08:00:00Z', record: { ...serverTask.record, note: options.data.note } }
        respond(options, { task: serverTask })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    login()
    const plans = usePlanStore()
    const tasks = useTaskStore()
    plans.applyPlanList([{ id: 100, title: 'Plan A', status: 'in-progress' }], user.id)
    plans.selectPlanById(100, user.id)
    tasks.setTasksForPlan(100, [serverTask], 1)
    tasks.setCurrentTask(67)

    await tasks.startTaskSubmission(67)
    await Promise.all([tasks.saveTaskNote(67, 'older note'), tasks.completeTaskSubmission(67, 'completed note')])

    expect(tasks.currentTask).toEqual(expect.objectContaining({ status: 'completed', completedAt: '2026-07-14T08:00:00Z', record: expect.objectContaining({ note: 'completed note' }) }))
    expect(getRequestCalls().map((request) => request.method)).toEqual(['POST', 'PATCH', 'POST'])
  })

  test('uses authenticated image cache without leaking a display path across plans', async () => {
    let fetchCount = 0
    setFetchHandler(async () => {
      fetchCount += 1
      return { ok: true, status: 200, blob: async () => new Blob(['image'], { type: 'image/png' }) }
    })
    setUploadHandler((options) => {
      options.success({
        statusCode: 200,
        data: JSON.stringify({ success: true, data: { task: taskFor(100, 67, { status: 'completed', record: { imageUrl: '/api/v1/plans/100/tasks/67/submission/image', note: '' } }) } }),
      })
    })

    login()
    const plans = usePlanStore()
    const tasks = useTaskStore()
    plans.applyPlanList([{ id: 100, title: 'Plan A', status: 'in-progress' }, { id: 200, title: 'Plan B', status: 'in-progress' }], user.id)
    tasks.setTasksForPlan(100, [taskFor(100)], 1)
    tasks.setTasksForPlan(200, [taskFor(200, 67, { record: { imageUrl: null, note: 'B note' } })], 1)
    plans.selectPlanById(100, user.id)
    tasks.setCurrentTask(67)

    const uploaded = await tasks.uploadTaskImage(67, 'temp://image.png')
    expect(uploaded.record.imageUrl).toContain('/submission/image')
    expect(uploaded.record.displayImagePath).toMatch(/^blob:/)
    await Promise.all([tasks.ensureTaskImageDisplay(67), tasks.ensureTaskImageDisplay(67)])
    expect(fetchCount).toBe(1)
    expect(tasks.tasksByPlanId['100'][0].record.displayImagePath).toBeUndefined()

    plans.selectPlanById(200, user.id)
    expect(tasks.currentPlanTasks[0].record.displayImagePath).toBe('')
    expect(tasks.currentPlanTasks[0].record.note).toBe('B note')

    tasks.resetSessionState()
    expect(tasks.taskImageCache).toEqual({})
  })

  test('restores the selected Plan and its remote Tasks through the shared recovery helper', async () => {
    uni.setStorageSync('tonglvji_auth', { token: 'refresh-token', userInfo: user })
    uni.setStorageSync('tonglvji_current_plan_selection', { userId: '7', planId: '20' })
    setRequestHandler((options) => {
      if (options.url.endsWith('/auth/me')) {
        respond(options, { user })
        return
      }
      if (options.url.endsWith('/plans')) {
        respond(options, { plans: [{ id: 19, title: 'Plan A', status: 'ready' }, { id: 20, title: 'Plan B', status: 'ready' }] })
        return
      }
      if (options.url.endsWith('/plans/20/tasks')) {
        respond(options, { tasks: [taskFor(20, 201), taskFor(20, 202), taskFor(20, 203)], taskCount: 3 })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const result = await ensureCurrentPlanReady({ withTasks: true })

    expect(result.currentPlan?.id).toBe(20)
    expect(useUserStore().isLoggedIn).toBe(true)
    expect(useTaskStore().currentPlanTasks.map((task) => task.planId)).toEqual([20, 20, 20])
  })
})
