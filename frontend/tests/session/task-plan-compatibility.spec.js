import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { resetUniRuntime } from './setup/uniRuntime.js'
import { usePlanStore } from '../../src/stores/plan.js'
import { useTaskStore } from '../../src/stores/task.js'

const planA = {
  id: 101,
  title: '计划 A',
  destination: '故宫博物院',
  ageGroup: '7-12',
  duration: '3小时',
  taskCount: 0,
  status: 'ready',
}

const planB = {
  id: 202,
  title: '计划 B',
  destination: '国家博物馆',
  ageGroup: '7-12',
  duration: '2小时',
  taskCount: 0,
  status: 'ready',
}

const taskA = {
  id: 35,
  planId: 101,
  order: 1,
  title: 'A 真实任务',
  subtitle: 'A subtitle',
  status: 'not-started',
  ageGroup: '7-12',
  duration: '约10分钟',
  type: '观察任务',
  summary: 'A summary',
  objective: 'A objective',
  steps: ['A step'],
  questions: ['A question'],
  recordMode: '拍照记录',
  theme: 'beasts',
  record: {
    imageUrl: null,
    note: '',
  },
}

describe('task plan compatibility', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('keeps remote task state isolated across plan switches', () => {
    const planStore = usePlanStore()
    const taskStore = useTaskStore()
    const taskB = { ...taskA, planId: 202, title: 'B 真实任务' }

    planStore.applyPlanList([planA, planB], 1)
    taskStore.setTasksForPlan(101, [taskA], 1)
    taskStore.setTasksForPlan(202, [taskB], 1)

    planStore.selectPlanById(101, 1)
    expect(taskStore.currentPlanTasks).toHaveLength(1)
    taskStore.setCurrentTask('35')

    planStore.selectPlanById(202, 1)
    const bTasks = taskStore.currentPlanTasks
    expect(bTasks).toHaveLength(1)
    expect(bTasks.every((task) => task.planId === 202)).toBe(true)
    expect(bTasks.every((task) => task.status === 'not-started')).toBe(true)
    expect(bTasks.every((task) => task.record?.note === '')).toBe(true)
    expect(bTasks.every((task) => !task.record?.displayImagePath)).toBe(true)
    expect(taskStore.currentTask === null || taskStore.currentTask.planId === 202).toBe(true)

    taskStore.setCurrentTask(35)
    planStore.selectPlanById(101, 1)
    const aAgain = taskStore.currentPlanTasks
    expect(aAgain[0].record.note).toBe('')
    expect(aAgain[0].record.displayImagePath).toBeFalsy()
    expect(aAgain[0].status).toBe('not-started')
    expect(aAgain.every((task) => !task.record?.displayImagePath)).toBe(true)
    expect(planStore.currentPlan.taskCount).toBe(1)

    planStore.currentPlan = null
    expect(taskStore.currentPlanTasks).toEqual([])
  })
})
