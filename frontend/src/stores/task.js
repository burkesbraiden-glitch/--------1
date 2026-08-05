import { defineStore } from 'pinia'
import * as tasksApi from '../api/tasks.js'
import { usePlanStore } from './plan.js'
import { useUserStore } from './user.js'
import { endUserSession } from '../utils/sessionBoundary'

const ensurePromises = new Map()
const submissionQueues = new Map()
const imageUploadPromises = new Map()
const imageDownloadPromises = new Map()
let nextSessionEpoch = 0

function planKey(planId) {
  return planId === null || planId === undefined ? '' : String(planId)
}

function taskKey(taskId) {
  return taskId === null || taskId === undefined ? '' : String(taskId)
}

function sameId(left, right) {
  return String(left) === String(right)
}

function normalizeTaskList(tasks) {
  return Array.isArray(tasks)
    ? tasks.filter(Boolean).map((task) => ({
      ...task,
      record: {
        ...(task.record || {}),
      },
    }))
    : []
}

function canAutoGenerate(status) {
  return status === 'ready' || status === 'in-progress'
}

function submissionKey(userId, planId, taskId) {
  return `${taskKey(userId)}:${planKey(planId)}:${taskKey(taskId)}`
}

function emptySubmissionState() {
  return {
    isStarting: false,
    isSaving: false,
    isCompleting: false,
    error: null,
  }
}

function emptyImageState(generation = 0) {
  return {
    displayPath: '',
    sourceImageUrl: '',
    loading: false,
    isUploading: false,
    error: null,
    generation,
    cleanup: null,
  }
}

export const useTaskStore = defineStore('task', {
  state: () => ({
    tasksByPlanId: {},
    taskImageCache: {},
    currentTaskId: null,
    isLoading: false,
    isGenerating: false,
    error: null,
    loadedPlanIds: [],
    submissionStates: {},
    sessionOwnerUserId: null,
    sessionEpoch: nextSessionEpoch,
  }),
  getters: {
    currentPlanId() {
      const planStore = usePlanStore()
      return planStore.currentPlan?.id ?? null
    },
    currentPlanRemoteTasks() {
      const key = planKey(this.currentPlanId)
      return key ? normalizeTaskList(this.tasksByPlanId[key]) : []
    },
    currentPlanTasks() {
      const key = planKey(this.currentPlanId)
      return key ? this.displayTasksForPlan(key) : []
    },
    tasks() {
      return Object.keys(this.tasksByPlanId).flatMap((planId) => this.displayTasksForPlan(planId))
    },
    currentTask() {
      return this.currentTaskId ? this.getTaskById(this.currentTaskId) : null
    },
    completedCount() {
      return this.currentPlanRemoteTasks.filter((task) => task.status === 'completed').length
    },
    progress() {
      if (!this.currentPlanRemoteTasks.length) {
        return 0
      }
      return Math.round((this.completedCount / this.currentPlanRemoteTasks.length) * 100)
    },
  },
  actions: {
    displayTasksForPlan(planId) {
      const key = planKey(planId)
      const remoteTasks = normalizeTaskList(this.tasksByPlanId[key])
      return remoteTasks
        .map((remoteTask) => {
          const remoteRecord = remoteTask.record || {}
          const imageState = this.imageStateForTask(remoteTask.id, remoteTask.planId)
          return {
            ...remoteTask,
            status: remoteTask.status,
            completedAt: remoteTask.completedAt,
            record: {
              ...remoteRecord,
              note: remoteRecord.note || '',
              imageUrl: remoteRecord.imageUrl || null,
              displayImagePath: remoteRecord.imageUrl ? imageState.displayPath || '' : '',
            },
          }
        })
        .sort((left, right) => (left.order || 0) - (right.order || 0))
    },
    setTasksForPlan(planId, tasks, taskCount = normalizeTaskList(tasks).length) {
      const key = planKey(planId)
      if (!key) {
        return []
      }

      const remoteTasks = normalizeTaskList(tasks)
      this.tasksByPlanId[key] = remoteTasks
      if (!this.loadedPlanIds.some((item) => sameId(item, key))) {
        this.loadedPlanIds = [...this.loadedPlanIds, key]
      }
      this.error = null

      const planStore = usePlanStore()
      planStore.syncTaskCount(planId, Number(taskCount) || remoteTasks.length)

      if (this.currentTaskId && !this.getTaskById(this.currentTaskId)) {
        this.currentTaskId = null
      }

      return this.displayTasksForPlan(key)
    },
    upsertRemoteTask(task, context = null) {
      const planId = task?.planId ?? context?.planId
      const key = planKey(planId)
      if (!key || !task || (context && !this.isSubmissionContextActive(context))) {
        return null
      }

      const remoteTask = {
        ...task,
        planId,
        record: {
          ...(task.record || {}),
        },
      }
      const current = normalizeTaskList(this.tasksByPlanId[key])
      const index = current.findIndex((item) => sameId(item.id, remoteTask.id))
      const next = [...current]
      if (index >= 0) {
        next.splice(index, 1, remoteTask)
      } else {
        next.push(remoteTask)
      }
      this.setTasksForPlan(planId, next, next.length)
      return this.getTaskById(remoteTask.id)
    },
    async ensureTasks(planId = this.currentPlanId, planStatus) {
      const key = planKey(planId)
      if (!key) {
        return []
      }

      if (ensurePromises.has(key)) {
        return ensurePromises.get(key)
      }

      const promise = this.loadTasksForPlan(planId, planStatus).finally(() => {
        ensurePromises.delete(key)
      })
      ensurePromises.set(key, promise)
      return promise
    },
    async loadTasksForPlan(planId, planStatus) {
      this.isLoading = true
      this.error = null

      try {
        let data = await tasksApi.getTasks(planId)
        let tasks = normalizeTaskList(data.tasks)
        let taskCount = Number(data.taskCount) || tasks.length
        const status = planStatus || usePlanStore().currentPlan?.status

        if (!tasks.length) {
          if (status === 'draft' || status === 'completed' || !canAutoGenerate(status)) {
            return this.setTasksForPlan(planId, tasks, taskCount)
          }

          this.isGenerating = true
          data = await tasksApi.generateTasks(planId)
          tasks = normalizeTaskList(data.tasks)
          taskCount = Number(data.taskCount) || tasks.length
        }

        return this.setTasksForPlan(planId, tasks, taskCount)
      } catch (error) {
        this.error = error
        throw error
      } finally {
        this.isLoading = false
        this.isGenerating = false
      }
    },
    async fetchTaskDetail(planId = this.currentPlanId, taskId = this.currentTaskId) {
      const key = planKey(planId)
      const id = taskKey(taskId)
      if (!key || !id) {
        return null
      }

      const data = await tasksApi.getTask(planId, taskId)
      const task = this.upsertRemoteTask(data.task)
      if (task) {
        this.currentTaskId = task.id
      }
      return task
    },
    getTaskById(taskId) {
      const currentPlanKey = planKey(this.currentPlanId)
      return this.currentPlanTasks.find((item) => sameId(item.id, taskId) && planKey(item.planId) === currentPlanKey) || null
    },
    setCurrentTask(taskId) {
      const task = this.getTaskById(taskId)
      if (task) {
        this.currentTaskId = task.id
      }
      return task || null
    },
    async ensureCurrentTask(taskId, { fetchDetail = false } = {}) {
      if (taskId) {
        const task = this.setCurrentTask(taskId)
        if (task) {
          return task
        }
      }

      if (fetchDetail && taskId && this.currentPlanId) {
        const task = await this.fetchTaskDetail(this.currentPlanId, taskId)
        if (task) {
          return task
        }
      }

      if (this.currentTaskId) {
        const task = this.setCurrentTask(this.currentTaskId)
        if (task) {
          return task
        }
      }

      const fallback = this.currentPlanTasks[0] || null
      this.currentTaskId = fallback?.id ?? null
      return fallback
    },
    ensureSubmissionSessionOwner(userId) {
      const normalizedUserId = taskKey(userId)
      if (!normalizedUserId) {
        throw { code: 'AUTH_REQUIRED', message: '请先登录后再记录任务' }
      }
      if (this.sessionOwnerUserId && !sameId(this.sessionOwnerUserId, normalizedUserId)) {
        this.resetSessionState()
      }
      this.sessionOwnerUserId = normalizedUserId
      return normalizedUserId
    },
    createSubmissionContext(taskId) {
      const userStore = useUserStore()
      const task = this.getTaskById(taskId)
      if (!userStore.isLoggedIn || !userStore.userInfo?.id) {
        throw { code: 'AUTH_REQUIRED', message: '请先登录后再记录任务' }
      }
      if (!task || !this.currentPlanId) {
        throw { code: 'TASK_NOT_FOUND', message: '没有找到这个任务，请返回任务列表重试' }
      }
      const userId = this.ensureSubmissionSessionOwner(userStore.userInfo.id)
      return {
        userId,
        planId: task.planId,
        taskId: task.id,
        sessionEpoch: this.sessionEpoch,
      }
    },
    isSubmissionContextActive(context) {
      const userStore = useUserStore()
      return Boolean(
        context &&
          userStore.isLoggedIn &&
          userStore.userInfo?.id &&
          sameId(userStore.userInfo.id, context.userId) &&
          sameId(this.sessionOwnerUserId, context.userId) &&
          this.sessionEpoch === context.sessionEpoch,
      )
    },
    submissionStateForTask(taskId, planId = this.currentPlanId) {
      const userId = useUserStore().userInfo?.id
      const key = submissionKey(userId, planId, taskId)
      return this.submissionStates[key] || emptySubmissionState()
    },
    setSubmissionState(context, patch) {
      if (!this.isSubmissionContextActive(context)) {
        return
      }
      const key = submissionKey(context.userId, context.planId, context.taskId)
      this.submissionStates[key] = {
        ...emptySubmissionState(),
        ...(this.submissionStates[key] || {}),
        ...patch,
      }
    },
    queueSubmission(context, stateKey, requestTask) {
      const key = submissionKey(context.userId, context.planId, context.taskId)
      const previous = submissionQueues.get(key) || Promise.resolve()
      const queued = previous
        .catch(() => null)
        .then(async () => {
          if (!this.isSubmissionContextActive(context)) {
            return null
          }
          this.setSubmissionState(context, { [stateKey]: true, error: null })
          try {
            const data = await requestTask()
            if (!this.isSubmissionContextActive(context)) {
              return null
            }
            const task = this.upsertRemoteTask(data.task, context)
            this.error = null
            return task
          } catch (error) {
            if (this.isSubmissionContextActive(context)) {
              this.setSubmissionState(context, { error })
              this.error = error
            }
            throw error
          } finally {
            this.setSubmissionState(context, { [stateKey]: false })
          }
        })
      const tail = queued.catch(() => null)
      submissionQueues.set(key, tail)
      return queued.finally(() => {
        if (submissionQueues.get(key) === tail) {
          submissionQueues.delete(key)
        }
      })
    },
    startTaskSubmission(taskId) {
      const task = this.getTaskById(taskId)
      if (task?.status === 'completed') {
        throw { code: 'TASK_ALREADY_COMPLETED', message: '这个任务已经完成了' }
      }
      const context = this.createSubmissionContext(taskId)
      return this.queueSubmission(context, 'isStarting', () => tasksApi.startTaskSubmission(context.planId, context.taskId))
    },
    saveTaskNote(taskId, note) {
      const context = this.createSubmissionContext(taskId)
      return this.queueSubmission(context, 'isSaving', () =>
        tasksApi.updateTaskSubmission(context.planId, context.taskId, { note: typeof note === 'string' ? note : '' }),
      )
    },
    completeTaskSubmission(taskId, note) {
      const context = this.createSubmissionContext(taskId)
      return this.queueSubmission(context, 'isCompleting', () =>
        tasksApi.completeTaskSubmission(context.planId, context.taskId, { note: typeof note === 'string' ? note : '' }),
      )
    },
    createTaskImageContext(taskId) {
      const userStore = useUserStore()
      const task = this.getTaskById(taskId)
      if (!userStore.isLoggedIn || !userStore.userInfo?.id) {
        throw { code: 'AUTH_REQUIRED', message: '请先登录后再查看任务图片' }
      }
      if (!task || !this.currentPlanId) {
        throw { code: 'TASK_NOT_FOUND', message: '没有找到这个任务，请返回任务列表重试' }
      }
      const userId = this.ensureSubmissionSessionOwner(userStore.userInfo.id)
      return {
        userId,
        planId: task.planId,
        taskId: task.id,
        sessionEpoch: this.sessionEpoch,
      }
    },
    imageCacheKeyForContext(context) {
      return submissionKey(context.userId, context.planId, context.taskId)
    },
    imageStateForTask(taskId, planId = this.currentPlanId) {
      const userId = useUserStore().userInfo?.id
      const key = submissionKey(userId, planId, taskId)
      return this.taskImageCache[key] || emptyImageState()
    },
    ensureImageState(context) {
      const key = this.imageCacheKeyForContext(context)
      if (!this.taskImageCache[key]) {
        this.taskImageCache[key] = emptyImageState()
      }
      return this.taskImageCache[key]
    },
    cleanupImageState(imageState) {
      if (!imageState?.displayPath) {
        return
      }
      if (typeof imageState.cleanup === 'function') {
        imageState.cleanup()
      } else if (imageState.displayPath.startsWith('blob:') && typeof URL !== 'undefined') {
        URL.revokeObjectURL(imageState.displayPath)
      }
      imageState.cleanup = null
      imageState.displayPath = ''
    },
    invalidateTaskImage(context) {
      const key = this.imageCacheKeyForContext(context)
      const imageState = this.ensureImageState(context)
      this.cleanupImageState(imageState)
      imageState.sourceImageUrl = ''
      imageState.loading = false
      imageState.error = null
      imageState.generation += 1
      imageDownloadPromises.delete(key)
      return imageState
    },
    isTaskImageContextActive(context, generation, sourceImageUrl) {
      if (!this.isSubmissionContextActive(context)) {
        return false
      }
      const imageState = this.taskImageCache[this.imageCacheKeyForContext(context)]
      return Boolean(
        imageState &&
          imageState.generation === generation &&
          imageState.sourceImageUrl === sourceImageUrl,
      )
    },
    handleTaskImageError(context, error) {
      if (!this.isSubmissionContextActive(context)) {
        return
      }
      if (['UNAUTHORIZED', 'INVALID_TOKEN', 'TOKEN_EXPIRED'].includes(error?.code) || error?.statusCode === 401) {
        endUserSession()
      }
    },
    ensureTaskImageDisplay(taskId, { force = false } = {}) {
      const context = this.createTaskImageContext(taskId)
      const task = this.getTaskById(context.taskId)
      const sourceImageUrl = task?.record?.imageUrl || ''
      const key = this.imageCacheKeyForContext(context)
      const imageState = this.ensureImageState(context)

      if (!sourceImageUrl) {
        this.invalidateTaskImage(context)
        return Promise.resolve(null)
      }
      if (!force && imageState.displayPath && imageState.sourceImageUrl === sourceImageUrl) {
        return Promise.resolve(imageState)
      }
      if (!force && imageState.loading && imageState.sourceImageUrl === sourceImageUrl && imageDownloadPromises.has(key)) {
        return imageDownloadPromises.get(key)
      }

      this.cleanupImageState(imageState)
      imageState.sourceImageUrl = sourceImageUrl
      imageState.loading = true
      imageState.error = null
      imageState.generation += 1
      const generation = imageState.generation

      const promise = tasksApi.downloadTaskImage(context.planId, context.taskId, sourceImageUrl)
        .then((result) => {
          if (!this.isTaskImageContextActive(context, generation, sourceImageUrl)) {
            result?.cleanup?.()
            return null
          }
          const currentState = this.taskImageCache[key]
          this.cleanupImageState(currentState)
          currentState.displayPath = result.displayPath || ''
          currentState.cleanup = result.cleanup || null
          currentState.loading = false
          currentState.error = null
          return currentState
        })
        .catch((error) => {
          if (this.isTaskImageContextActive(context, generation, sourceImageUrl)) {
            const currentState = this.taskImageCache[key]
            currentState.loading = false
            currentState.error = error
            this.handleTaskImageError(context, error)
          }
          throw error
        })
        .finally(() => {
          if (imageDownloadPromises.get(key) === promise) {
            imageDownloadPromises.delete(key)
          }
        })
      imageDownloadPromises.set(key, promise)
      return promise
    },
    uploadTaskImage(taskId, filePath) {
      const context = this.createTaskImageContext(taskId)
      const key = this.imageCacheKeyForContext(context)
      if (imageUploadPromises.has(key)) {
        return imageUploadPromises.get(key)
      }
      const imageState = this.ensureImageState(context)
      imageState.isUploading = true
      imageState.error = null
      const promise = tasksApi.uploadTaskImage(context.planId, context.taskId, filePath)
        .then(async (data) => {
          if (!this.isSubmissionContextActive(context)) {
            return null
          }
          const task = this.upsertRemoteTask(data.task, context)
          if (!task) {
            return null
          }
          this.invalidateTaskImage(context)
          await this.ensureTaskImageDisplay(context.taskId, { force: true })
          return this.getTaskById(context.taskId)
        })
        .catch((error) => {
          if (this.isSubmissionContextActive(context)) {
            this.ensureImageState(context).error = error
            this.handleTaskImageError(context, error)
          }
          throw error
        })
        .finally(() => {
          if (this.isSubmissionContextActive(context)) {
            this.ensureImageState(context).isUploading = false
          }
          if (imageUploadPromises.get(key) === promise) {
            imageUploadPromises.delete(key)
          }
        })
      imageUploadPromises.set(key, promise)
      return promise
    },
    resetSessionState() {
      nextSessionEpoch += 1
      Object.values(this.taskImageCache).forEach((imageState) => this.cleanupImageState(imageState))
      this.tasksByPlanId = {}
      this.taskImageCache = {}
      this.currentTaskId = null
      this.isLoading = false
      this.isGenerating = false
      this.error = null
      this.loadedPlanIds = []
      this.submissionStates = {}
      this.sessionOwnerUserId = null
      this.sessionEpoch = nextSessionEpoch
      ensurePromises.clear()
      submissionQueues.clear()
      imageUploadPromises.clear()
      imageDownloadPromises.clear()
    },
  },
})
